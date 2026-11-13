# reactive-avatars

A mic-reactive avatar for OBS / Streamlabs Browser Sources. Bring your own character:

- **Build one from layers, no code.** Upload same-size transparent images (body, eyes open/closed,
  mouth closed/open, plus ears, a hat, anything) in the settings page. It blinks, talks, droops
  when you're quiet, perks ears, and glows with your voice.
- **Use a single picture** that bounces with your voice, or two for the classic PNGtuber swap.
- **Drop in a hand-animated rig** (any SVG/HTML page) as a private avatar pack.

It ships with **Blobby**, an example layered avatar. See
[docs/making-an-avatar.md](docs/making-an-avatar.md).

A small local server captures your microphone (via `sounddevice`) and streams the
volume to a browser page over WebSocket, so there's no in-browser mic permission
prompt, which is flaky inside OBS/Streamlabs' embedded Chromium.

## Requirements

The only system dependency is **PortAudio** (used to read your microphone). On Linux the
app uses your system's own audio libraries (ALSA, PortAudio) instead of bundling them, so
it works with whatever PipeWire/PulseAudio setup your distro has.

| OS | Setup |
| --- | --- |
| **Windows** 10/11 | Nothing to install, PortAudio is bundled. |
| **Arch / Manjaro** | `sudo pacman -S portaudio` |
| **Debian** | `sudo apt install libportaudio2` |
| **Ubuntu** | `sudo apt install libportaudio2` |

Running from source also needs [Python 3.12+](https://www.python.org/downloads/) and
[uv](https://docs.astral.sh/uv/) (`pip install uv`, or see the uv docs for other installers).
The prebuilt binaries below don't need Python or uv.

A browser is needed to open the settings page.

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

1. **Choose your avatar:** the example, **Build my own from layers**, or **A single picture**
   (PNG, JPG, GIF, WebP or SVG; transparent PNGs look best).
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

## Troubleshooting

**The avatar doesn't react to my voice**

1. Open the settings page and talk. The green bar is your raw mic level. At silence it
   sits as a thin sliver (room noise), so look for it to jump when you speak.
2. If it moves but never reaches the amber gate line, **lower the noise gate** (just above
   the silent level) and/or **raise Sensitivity**, then press Save.
3. If it never moves, the app is listening to the wrong input or your mic is muted or too
   quiet. Check the status line at the top for the device name, then pick another mic.

**My microphone isn't in the list (or the list is empty)**

- Leave the dropdown on **Automatic**, or pick `pulse` / `pipewire`. These go through your
  sound server and are the most reliable on Linux.
- Raw `hw:` entries talk to the hardware directly. They can be silent (for example a
  headset jack with nothing plugged in) or fail with "Device unavailable" because
  PipeWire/PulseAudio already holds the device. Avoid them unless you know you need one.
- Restart the app after plugging in a new mic; the device list is read at startup.
- **Linux, no `pulse`/`pipewire` entries:** install PortAudio (see Requirements) and use the
  latest release. Check what the system sees with `pactl list short sources` or `wpctl status`.
- **Windows:** check *Settings → Privacy & security → Microphone* allows desktop apps, and
  that the right mic is the default input in the Sound settings.

**"Mic error" in the status line**

Another app may have exclusive access to the device, or the device was unplugged. Close
the other app or pick a different mic, then press Save to retry.

**The mic selection changed after a reboot**

Mics are saved by name, so renaming or unplugging the saved device makes the app fall
back to Automatic. Pick it again and Save.

**Port 8347 is already in use**

Another copy is probably running. Use **Quit app** on its settings page, or
`kill $(lsof -t -i :8347)` on Linux, or start this one on another port with `--port 8350`
(then update the Browser Source URL).

**The avatar is missing in OBS / Streamlabs**

Keep the app running, make sure the Browser Source URL matches the port above, and turn
off "Shutdown source when not visible" so it keeps animating between scenes.

## Files

```
src/reactive_avatars/
  __init__.py   CLI entry point
  server.py     FastAPI app: overlay, settings, image upload, WebSocket
  audio.py      mic capture -> gated volume
  config.py     settings + paths
  packs.py      avatar packs: discovery, layer builder, safe file access
  static/       overlay + settings pages (plain HTML/JS/CSS, no build step)
    layers.*    the player for layered avatars
    packs/      built-in example avatars (Blobby)
docs/           making-an-avatar.md
tests/          pytest (make test)
```

Settings, uploaded images and your own avatar packs live in `~/.config/reactive-avatars/`.

## Custom avatars

Everything about making and sharing avatars (layer format, reactions, previewing, and
fully custom HTML rigs) is in [docs/making-an-avatar.md](docs/making-an-avatar.md). Packs
in `~/.config/reactive-avatars/packs/` stay on your machine, so private art never has to
be committed anywhere.

## License

MIT
