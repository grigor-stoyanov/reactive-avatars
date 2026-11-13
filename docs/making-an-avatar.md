# Making an avatar

An **avatar pack** is a folder with an `avatar.json`. There are two kinds. Most people
want the first.

Packs live in `~/.config/reactive-avatars/packs/<name>/` (on Windows:
`C:\Users\<you>\.config\reactive-avatars\packs\<name>\`). Drop a folder in, reload the
settings page, and pick it from the **Avatar** menu. Packs there are private to your
machine and override a built-in pack with the same name.

## 1. Layered avatar (no code)

You draw (or export) several **transparent images that are all the same size**, in any art
program. They are stacked on top of each other, so nothing needs positioning. The app
animates them: it swaps the mouth with your loudness, blinks, droops the eyes when you're
quiet, perks ears, lifts hats, breathes, and glows.

### The easy way: the settings page

Choose **Build my own from layers** in the Avatar menu and upload one image per slot.
Only the body is required. Changes show up in OBS instantly.

### The file way

```
my-pack/
  avatar.json
  body.png  eyes_open.png  eyes_closed.png
  mouth_closed.png  mouth_open.png  ears.png  hat.png
```

```json
{
  "name": "My Avatar",
  "type": "layers",
  "layers": [
    { "image": "ears.png",         "react": "perk_left" },
    { "image": "body.png",         "role": "body" },
    { "image": "eyes_open.png",    "role": "eyes_open" },
    { "image": "eyes_closed.png",  "role": "eyes_closed" },
    { "image": "mouth_closed.png", "role": "mouth_closed" },
    { "image": "mouth_open.png",   "role": "mouth_open" },
    { "image": "hat.png",          "react": "lift" }
  ]
}
```

`layers` is drawn **back to front**. Images can be PNG, WebP, GIF, JPG or SVG, and must
share one canvas size (for example 512×512) so they line up.

**Roles** (which frame is shown):

| role | shown when |
| --- | --- |
| `body` | always |
| `eyes_open` | normally |
| `eyes_half` | quiet for a few seconds (sleepy). Optional |
| `eyes_closed` | blinking |
| `mouth_closed` | silent |
| `mouth_half` | talking softly. Optional; skipped if missing |
| `mouth_open` | talking loudly |

Only the roles you provide are used. A pack with just a body works too.

**Reactions** (`"react"`) make a layer move with your voice. Use a preset name:
`sway`, `bounce`, `lift`, `perk_left`, `perk_right`, `pulse`, or write your own:

```json
{ "image": "tail.png", "react": { "rotate": 10, "sway": 3, "origin": [0.2, 0.8] } }
```

| key | meaning |
| --- | --- |
| `y` | vertical move, in % of height, at full volume (negative = up) |
| `rotate` | degrees at full volume |
| `scale` | extra scale at full volume (`0.06` = 6% bigger) |
| `sway` | idle rocking in degrees |
| `origin` | pivot point `[x, y]` as fractions of the canvas (default centre) |

### Previewing

`http://127.0.0.1:8347/?avatar=my-pack&volume=0.9` shows a pack at a fixed loudness
without switching your live avatar. Try `volume=0` (idle), `0.12` and `0.9`.

## 2. HTML avatar (full control)

For a hand-animated rig (an SVG character, canvas, WebGL, anything):

```json
{ "name": "My Rig", "type": "html", "entry": "index.html" }
```

`entry` is served as the overlay, and relative URLs resolve inside your pack folder. Your
page opens `ws://<host>/ws/audio` and receives about 30 messages a second:

```json
{ "volume": 0.42, "raw": 0.07 }
```

`volume` is the mic level after the noise gate and sensitivity (0..1, drive your animation
with this); `raw` is the ungated mic level. You also get a one-off
`{ "config": { ... } }` message, which you can ignore. The app reloads your page
automatically when you switch avatars.

Keep the page background transparent so only your character shows over the scene.
