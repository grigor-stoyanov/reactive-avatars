from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, Literal

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config as cfg_mod
from .audio import AudioEngine, list_input_devices

STATIC_DIR = Path(__file__).parent / "static"
BROADCAST_HZ = 30
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

engine: AudioEngine | None = None
clients: set[WebSocket] = set()  # every connected page (overlay + settings)
settings_clients: set[WebSocket] = set()
settings_seen = False  # arms auto-quit the first time a settings page connects

# Auto-quit: once the settings page has been opened, the app exits when every
# page (settings and overlay) has been gone for QUIT_GRACE_S seconds. The grace
# period survives a page reload. Disable with --keep-alive.
auto_quit = True
QUIT_GRACE_S = 10
request_shutdown: Callable[[], None] = lambda: None  # set by main()


class ConfigUpdate(BaseModel):
    device: int | None = None
    gain: float = Field(4.0, ge=0.5, le=50)
    gate: float = Field(0.06, ge=0, le=1)
    motion: float = Field(1.0, ge=0, le=3)
    glow: bool = True
    glow_color: str = Field("#45f0a6", pattern=r"^#[0-9a-fA-F]{6}$")


def _image_path(cfg: dict, slot: str) -> Path | None:
    name = cfg.get(f"{slot}_image")
    if not name:
        return None
    path = cfg_mod.IMAGE_DIR / name
    return path if path.is_file() else None


def overlay_config() -> dict:
    """What the overlay page needs to render (sent over the WebSocket)."""
    cfg = cfg_mod.load_config()
    images = {}
    for slot in cfg_mod.SLOTS:
        path = _image_path(cfg, slot)
        images[slot] = f"/avatar/{slot}?v={path.stat().st_mtime_ns}" if path else None
    if images["idle"] is None:
        images["idle"] = "/static/default-avatar.svg"
    return {
        "motion": cfg["motion"],
        "glow": cfg["glow"],
        "glow_color": cfg["glow_color"],
        "idle_image": images["idle"],
        "talking_image": images["talking"],
    }


def settings_payload() -> dict:
    cfg = cfg_mod.load_config()
    return {
        **cfg,
        **overlay_config(),
        "error": engine.error if engine else None,
        "active_device_name": engine.active_device_name if engine else None,
    }


async def _send_all(payload: dict) -> None:
    dead = []
    for ws in list(clients):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


async def _broadcast_loop() -> None:
    while True:
        await asyncio.sleep(1 / BROADCAST_HZ)
        if clients and engine is not None:
            volume, raw = engine.get_levels()
            await _send_all({"volume": round(volume, 4), "raw": round(raw, 4)})


async def _quit_watchdog() -> None:
    empty_for = 0.0
    while True:
        await asyncio.sleep(1)
        if not (auto_quit and settings_seen) or clients:
            empty_for = 0.0
            continue
        empty_for += 1
        if empty_for >= QUIT_GRACE_S:
            request_shutdown()
            return


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    cfg = cfg_mod.load_config()
    engine = AudioEngine(cfg["device"], cfg["gain"], cfg["gate"])
    engine.start()
    tasks = [asyncio.create_task(_broadcast_loop()), asyncio.create_task(_quit_watchdog())]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        engine.stop()


app = FastAPI(lifespan=lifespan, title="reactive-avatars")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def overlay_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "overlay.html")


@app.get("/settings")
async def settings_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "settings.html")


@app.get("/api/devices")
async def api_devices() -> JSONResponse:
    return JSONResponse(list_input_devices())


@app.get("/api/config")
async def api_get_config() -> JSONResponse:
    return JSONResponse(settings_payload())


@app.post("/api/config")
async def api_set_config(update: ConfigUpdate) -> JSONResponse:
    assert engine is not None
    cfg_mod.save_config({**cfg_mod.load_config(), **update.model_dump()})
    engine.restart(update.device, update.gain, update.gate)
    await _send_all({"config": overlay_config()})
    return JSONResponse(settings_payload())


@app.post("/api/quit")
async def api_quit() -> JSONResponse:
    asyncio.get_running_loop().call_later(0.3, request_shutdown)  # let the response out first
    return JSONResponse({"ok": True})


@app.get("/avatar/{slot}")
async def get_avatar(slot: Literal["idle", "talking"]) -> FileResponse:
    path = _image_path(cfg_mod.load_config(), slot)
    if path is None:
        raise HTTPException(404)
    # sandbox: an uploaded SVG must never run script if opened directly
    return FileResponse(path, headers={"Content-Security-Policy": "sandbox"})


@app.put("/api/avatar/{slot}")
async def put_avatar(slot: Literal["idle", "talking"], request: Request) -> JSONResponse:
    """Raw image bytes as the request body (no multipart dependency needed)."""
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    ext = cfg_mod.IMAGE_TYPES.get(content_type)
    if ext is None:
        raise HTTPException(415, f"Unsupported type. Use one of: {', '.join(cfg_mod.IMAGE_TYPES)}")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Image too large (10 MB max)")
    if not body:
        raise HTTPException(400, "Empty upload")

    cfg = cfg_mod.load_config()
    _delete_image(cfg, slot)
    cfg_mod.IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{slot}{ext}"
    (cfg_mod.IMAGE_DIR / name).write_bytes(bytes(body))
    cfg[f"{slot}_image"] = name
    cfg_mod.save_config(cfg)
    await _send_all({"config": overlay_config()})
    return JSONResponse(settings_payload())


@app.delete("/api/avatar/{slot}")
async def delete_avatar(slot: Literal["idle", "talking"]) -> JSONResponse:
    cfg = cfg_mod.load_config()
    _delete_image(cfg, slot)
    cfg[f"{slot}_image"] = None
    cfg_mod.save_config(cfg)
    await _send_all({"config": overlay_config()})
    return JSONResponse(settings_payload())


def _delete_image(cfg: dict, slot: str) -> None:
    path = _image_path(cfg, slot)
    if path is not None:
        path.unlink(missing_ok=True)


@app.websocket("/ws/audio")
async def ws_audio(websocket: WebSocket) -> None:
    global settings_seen
    await websocket.accept()
    clients.add(websocket)
    if websocket.query_params.get("role") == "settings":
        settings_clients.add(websocket)
        settings_seen = True
    try:
        await websocket.send_json({"config": overlay_config()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(websocket)
        settings_clients.discard(websocket)
