"""Avatar packs: a folder with an ``avatar.json`` manifest.

Two kinds (see docs/making-an-avatar.md):
  * ``layers``: same-size transparent images the built-in player animates.
  * ``html``: your own page/rig, served as the overlay.

Built-in packs ship in static/packs/. User packs live in ~/.config/reactive-avatars/packs/
and win on id clashes, so a private rig never needs to be in the repo.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import config as cfg_mod

BUILTIN_DIR = Path(__file__).parent / "static" / "packs"
DEFAULT_PACK = "blobby"
CUSTOM_ID = "custom"  # the pack the settings-page layer builder writes
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Layer-builder slots, in draw order (back to front). Only "body" is required.
SLOTS: list[dict[str, Any]] = [
    {"role": "back1", "label": "Behind body 1 (e.g. ears, tail)", "react": True},
    {"role": "back2", "label": "Behind body 2", "react": True},
    {"role": "body", "label": "Body / head", "required": True},
    {"role": "eyes_open", "label": "Eyes open"},
    {"role": "eyes_half", "label": "Eyes half closed (sleepy, optional)"},
    {"role": "eyes_closed", "label": "Eyes closed (blink)"},
    {"role": "mouth_closed", "label": "Mouth closed"},
    {"role": "mouth_half", "label": "Mouth half open (optional)"},
    {"role": "mouth_open", "label": "Mouth open"},
    {"role": "front1", "label": "In front 1 (e.g. hat, glasses)", "react": True},
    {"role": "front2", "label": "In front 2", "react": True},
    {"role": "front3", "label": "In front 3", "react": True},
]
ANIMATED_ROLES = {
    "body", "eyes_open", "eyes_half", "eyes_closed", "mouth_closed", "mouth_half", "mouth_open"
}
REACTIONS = ["none", "sway", "bounce", "lift", "perk_left", "perk_right", "pulse"]


def _read_manifest(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads((path / "avatar.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def pack_dir(pack_id: str) -> Path | None:
    if not ID_RE.match(pack_id):
        return None
    for root in (cfg_mod.PACKS_DIR, BUILTIN_DIR):  # user packs first
        candidate = root / pack_id
        if (candidate / "avatar.json").is_file():
            return candidate
    return None


def list_packs() -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for root, builtin in ((BUILTIN_DIR, True), (cfg_mod.PACKS_DIR, False)):
        if not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            manifest = _read_manifest(path) if path.is_dir() and ID_RE.match(path.name) else None
            if manifest is None:
                continue
            found[path.name] = {
                "id": path.name,
                "name": str(manifest.get("name", path.name)),
                "type": manifest.get("type", "layers"),
                "builtin": builtin,
            }
    return list(found.values())


def resolve_file(pack_id: str, relative: str) -> Path | None:
    """A file inside a pack, or None. Never escapes the pack folder."""
    base = pack_dir(pack_id)
    if base is None:
        return None
    target = (base / relative).resolve()
    if not target.is_relative_to(base.resolve()) or not target.is_file():
        return None
    return target


def manifest_rev(pack_id: str) -> int:
    base = pack_dir(pack_id)
    return (base / "avatar.json").stat().st_mtime_ns if base else 0


# ---- the settings-page layer builder (writes the "custom" user pack) -------------------

def _custom_dir() -> Path:
    return cfg_mod.PACKS_DIR / CUSTOM_ID


def _custom_state() -> dict[str, Any]:
    try:
        return json.loads((_custom_dir() / "state.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {"files": {}, "react": {}}


def _write_custom(state: dict[str, Any]) -> None:
    root = _custom_dir()
    root.mkdir(parents=True, exist_ok=True)
    (root / "state.json").write_text(json.dumps(state, indent=2))
    layers = []
    for slot in SLOTS:
        role = slot["role"]
        name = state["files"].get(role)
        if not name:
            continue
        layer: dict[str, Any] = {"image": name}
        if role in ANIMATED_ROLES:
            layer["role"] = role
        reaction = state["react"].get(role, "none")
        if reaction != "none":
            layer["react"] = reaction
        layers.append(layer)
    (root / "avatar.json").write_text(
        json.dumps({"name": "My layered avatar", "type": "layers", "layers": layers}, indent=2)
    )


def custom_slots() -> list[dict[str, Any]]:
    state = _custom_state()
    out = []
    for slot in SLOTS:
        role = slot["role"]
        name = state["files"].get(role)
        out.append(
            {
                **slot,
                "url": f"/a/{CUSTOM_ID}/{name}?v={(_custom_dir() / name).stat().st_mtime_ns}"
                if name and (_custom_dir() / name).is_file()
                else None,
                "reaction": state["react"].get(role, "none") if slot.get("react") else None,
            }
        )
    return out


def set_custom_layer(role: str, ext: str, data: bytes) -> None:
    if role not in {s["role"] for s in SLOTS}:
        raise KeyError(role)
    state = _custom_state()
    clear_custom_layer(role, state, write=False)
    root = _custom_dir()
    root.mkdir(parents=True, exist_ok=True)
    name = f"{role}{ext}"
    (root / name).write_bytes(data)
    state["files"][role] = name
    _write_custom(state)


def clear_custom_layer(role: str, state: dict[str, Any] | None = None, write: bool = True) -> None:
    state = state if state is not None else _custom_state()
    old = state["files"].pop(role, None)
    if old:
        (_custom_dir() / old).unlink(missing_ok=True)
    if write:
        _write_custom(state)


def set_custom_reaction(role: str, reaction: str) -> None:
    if reaction not in REACTIONS or role not in {s["role"] for s in SLOTS if s.get("react")}:
        raise KeyError(role)
    state = _custom_state()
    state["react"][role] = reaction
    _write_custom(state)
