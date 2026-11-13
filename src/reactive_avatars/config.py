from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "reactive-avatars"
CONFIG_PATH = CONFIG_DIR / "config.json"
IMAGE_DIR = CONFIG_DIR / "avatars"  # single-image uploads
PACKS_DIR = CONFIG_DIR / "packs"  # user avatar packs (private rigs, downloaded packs, the layer builder)

# Upload slots: "idle" is the main avatar, "talking" is an optional swap-in image.
SLOTS = ("idle", "talking")

# content-type -> file extension. Only formats every browser source can render.
IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

DEFAULTS: dict[str, Any] = {
    "avatar": "blobby",  # a pack id, or "image" for the single-picture mode
    "device": None,  # input device name, None = automatic (sound server default)
    "gate": 0.06,  # raw mic RMS below this counts as silence
    "gain": 4.0,  # multiplies the gated level to reach full reaction
    "motion": 1.0,  # strength of the bounce/scale reaction (0 = none)
    "glow": True,  # glow behind the avatar that brightens with your voice
    "glow_color": "#45f0a6",
    "idle_image": None,  # filename inside IMAGE_DIR, None = bundled default
    "talking_image": None,
}


def load_config() -> dict[str, Any]:
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}
    if not isinstance(data.get("device"), str):
        data.pop("device", None)  # older versions saved a numeric index, which isn't stable
    return {**DEFAULTS, **data}


def save_config(config: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    merged = {**DEFAULTS, **config}
    CONFIG_PATH.write_text(json.dumps(merged, indent=2))
