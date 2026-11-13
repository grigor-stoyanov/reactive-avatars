# reactive-avatars

Turn any image into a mic-reactive avatar for OBS / Streamlabs Browser Sources.

Upload a picture and it bounces and glows with your voice. Add a second "talking"
image and it swaps to that while you speak (the classic PNGtuber setup).

A small local server captures your microphone (via `sounddevice`) and streams the
volume to a browser page over WebSocket, so there's no in-browser mic permission
prompt, which is flaky inside OBS/Streamlabs' embedded Chromium.

## Requirements

The only system dependency is **PortAudio** (used to read your microphone).

| OS | Setup |
| --- | --- |
| **Windows** 10/11 | Nothing to install, PortAudio is bundled. |
| **Arch / Manjaro** | `sudo pacman -S portaudio` |
| **Debian** | `sudo apt install libportaudio2` |
| **Ubuntu** | `sudo apt install libportaudio2` |

Running from source also needs [Python 3.12+](https://www.python.org/downloads/) and
[uv](https://docs.astral.sh/uv/) (`pip install uv`, or see the uv docs for other installers).
The prebuilt binaries below don't need Python or uv.

Linux audio works best with PulseAudio or PipeWire (the default on current Arch,
Debian and Ubuntu). A browser is needed to open the settings page.

## Download (no install)

Grab `reactive-avatars-windows.exe` or `reactive-avatars-linux` from the
[Releases](../../releases) page and double-click it (on Linux, `chmod +x` it first,
and run it in a terminal if your file manager asks).

- **Windows:** the binary is unsigned, so SmartScreen may warn. Click
  *More info → Run anyway*.
- **Linux:** install PortAudio first (see above).

To build it yourself: `make build` (produces a binary for your current OS).

## Quick start (from source)

```bash
uv run reactive-avatars        # or: pip install . && reactive-avatars
```

This opens the settings page, where you can:

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

Options: `--port 9000`, `--host 0.0.0.0`, `--no-browser`, `--keep-alive`.

**Stopping the app:** click **Quit app** on the settings page. The app also quits by
itself about 10 seconds after you close the settings tab, as long as no overlay (OBS /
Streamlabs) is still connected, so closing the browser won't kill your stream overlay.
Pass `--keep-alive` to disable the auto-quit. `Ctrl+C` in the terminal always works.

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
