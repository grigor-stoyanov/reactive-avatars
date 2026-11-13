# reactive-avatars

Turn any image into a mic-reactive avatar for OBS / Streamlabs Browser Sources.

Upload a picture and it bounces and glows with your voice. Add a second "talking"
image and it swaps to that while you speak (the classic PNGtuber setup).

A small local server captures your microphone (via `sounddevice`) and streams the
volume to a browser page over WebSocket, so there's no in-browser mic permission
prompt, which is flaky inside OBS/Streamlabs' embedded Chromium.

## Quick start

```bash
uv run reactive-avatars        # or: pip install . && reactive-avatars
```

Requires Python 3.12+. This opens the settings page, where you can:

1. **Upload your avatar** (PNG, JPG, GIF, WebP or SVG; transparent PNGs look best),
   and optionally a second image to show while talking.
2. **Pick your microphone** and tune the noise gate and sensitivity with the live meter.
3. Adjust motion strength and glow color.

Then add `http://127.0.0.1:8347/` as a **Browser Source** (e.g. 400×400) in OBS or
Streamlabs. Changes apply live. Keep the terminal open while streaming.

| URL | What |
| --- | --- |
| `http://127.0.0.1:8347/` | Overlay (the Browser Source) |
| `http://127.0.0.1:8347/settings` | Settings page |
| `http://127.0.0.1:8347/?debug=1` | Overlay with a small volume readout |

Options: `--port 9000`, `--host 0.0.0.0`, `--no-browser`.

## Tuning the mic

The meter shows your raw mic level (green), the noise gate (amber) and what reaches
the avatar (violet). Put the gate just above where green idles when you're silent.
The overlay also auto-adjusts to your speaking level.

If nothing reacts, check the status line on the settings page: it names the device
being captured. "Automatic" prefers `pulse`/`pipewire` on Linux, because PortAudio's
default is often a raw ALSA card that records silence.

## Files

```
src/reactive_avatars/
  __init__.py   CLI entry point
  server.py     FastAPI app: overlay, settings, image upload, WebSocket
  audio.py      mic capture -> gated volume
  config.py     settings + paths
  static/       overlay and settings pages (plain HTML/JS/CSS, no build step)
examples/neon-cat/   a hand-animated SVG avatar, as a template for custom rigs
```

Settings and uploaded images live in `~/.config/reactive-avatars/`.

## Custom animation

For a fully custom avatar, copy `examples/neon-cat/` and edit it. It connects to the
same `/ws/audio` WebSocket, which sends `{"volume": 0..1, "raw": rms}` ~30 times a
second (plus a one-off `{"config": ...}` message you can ignore).

## License

MIT
