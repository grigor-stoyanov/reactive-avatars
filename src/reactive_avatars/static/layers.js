// Plays a "layers" avatar pack: same-size transparent images stacked on one canvas.
// Roles (body, eyes_*, mouth_*) are swapped by the voice; other layers can carry a
// "react" so ears perk, a hat lifts, etc. Format: docs/making-an-avatar.md
(() => {
  const avatarEl = document.getElementById("avatar");
  const debugEl = document.getElementById("debug");
  const debugMode = new URLSearchParams(location.search).has("debug");
  if (debugMode) debugEl.hidden = false;

  const TALK_THRESHOLD = 0.06;
  const TALK_HOLD_MS = 700;
  const SLEEPY_AFTER_MS = 2600;
  const BLINK_MS = 130;

  // react: y = % of height at full volume, rotate = degrees at full volume,
  // scale = extra scale at full volume, sway = idle rocking in degrees,
  // origin = pivot as fractions of the canvas.
  const PRESETS = {
    none: {},
    sway: { sway: 2.5 },
    bounce: { y: -4 },
    lift: { y: -4, sway: 1.5 },
    perk_left: { rotate: -7, origin: [0.3, 0.45] },
    perk_right: { rotate: 7, origin: [0.7, 0.45] },
    pulse: { scale: 0.06 },
  };

  const layers = []; // { el, role, react }
  let settings = { motion: 1, glow: true, glow_color: "#45f0a6" };
  const fixedVolume = new URLSearchParams(location.search).get("volume"); // design preview
  let rawVolume = fixedVolume === null ? 0 : Number(fixedVolume);
  let level = 0;
  let peakRef = 0.3;
  let lastLoudAt = -Infinity;
  let blinkStart = -Infinity;

  const lerp = (a, b, t) => a + (b - a) * t;
  const clamp01 = (v) => Math.min(1, Math.max(0, v));
  const byRole = (role) => layers.find((l) => l.role === role);

  async function load() {
    const base = `/a/${window.RA_AVATAR}/`;
    const manifest = await fetch(`${base}avatar.json`).then((r) => r.json());
    for (const spec of manifest.layers ?? []) {
      const el = document.createElement("img");
      el.alt = "";
      el.src = base + spec.image;
      avatarEl.appendChild(el);
      const react = typeof spec.react === "string" ? PRESETS[spec.react] ?? {} : spec.react ?? {};
      const [ox, oy] = react.origin ?? spec.origin ?? [0.5, 0.5];
      el.style.transformOrigin = `${ox * 100}% ${oy * 100}%`;
      layers.push({ el, role: spec.role ?? null, react });
    }
    requestAnimationFrame(frame);
  }

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/audio`);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.config) settings = msg.config;
      else if (fixedVolume === null) rawVolume = msg.volume;
    };
    ws.onclose = () => setTimeout(connect, 1000);
    ws.onerror = () => ws.close();
  }

  function scheduleBlink() {
    setTimeout(() => {
      blinkStart = performance.now();
      scheduleBlink();
    }, 2400 + Math.random() * 3600);
  }

  function show(role, visible) {
    const layer = byRole(role);
    if (layer) layer.el.hidden = !visible;
  }

  function frame(now) {
    // auto-gain against a decaying peak, fast attack / slower release
    peakRef = Math.max(rawVolume, peakRef * 0.995, 0.25);
    const shaped = Math.pow(clamp01(rawVolume / peakRef), 0.6);
    level = lerp(level, shaped, shaped > level ? 0.55 : 0.14);

    if (rawVolume > TALK_THRESHOLD) lastLoudAt = now;
    const talking = now - lastLoudAt < TALK_HOLD_MS;
    const quietFor = now - lastLoudAt;

    // mouth: pick the frame that fits the loudness (falls back to what the pack has)
    const hasHalf = Boolean(byRole("mouth_half"));
    const mouth = level > 0.5 ? "open" : level > 0.15 ? (hasHalf ? "half" : "open") : "closed";
    for (const name of ["closed", "half", "open"]) show(`mouth_${name}`, name === mouth);
    if (!byRole(`mouth_${mouth}`)) for (const name of ["closed", "half", "open"]) show(`mouth_${name}`, name === "closed");

    // eyes: blink -> closed, quiet for a while -> half (or closed), otherwise open
    const blinking = now - blinkStart < BLINK_MS;
    const sleepy = !talking && quietFor > SLEEPY_AFTER_MS;
    let eyes = "open";
    if (blinking) eyes = "closed";
    else if (sleepy) eyes = byRole("eyes_half") ? "half" : "open";
    if (!byRole(`eyes_${eyes}`)) eyes = "open";
    for (const name of ["open", "half", "closed"]) show(`eyes_${name}`, name === eyes);

    // per-layer reactions
    const m = settings.motion;
    for (const layer of layers) {
      const r = layer.react;
      if (!r.y && !r.rotate && !r.scale && !r.sway) continue;
      const y = (r.y ?? 0) * level * m;
      const rot = (r.rotate ?? 0) * level * m + (r.sway ?? 0) * m * Math.sin(now / 900);
      const sc = 1 + (r.scale ?? 0) * level * m;
      layer.el.style.transform = `translateY(${y.toFixed(2)}%) rotate(${rot.toFixed(2)}deg) scale(${sc.toFixed(4)})`;
    }

    // whole-avatar bounce, breathing while idle, glow
    const breathe = talking ? 0 : Math.sin(now / 1400) * 0.8 * m;
    const lift = -level * 2 * m + breathe;
    avatarEl.style.transform = `translateY(${lift.toFixed(2)}%) scale(${(1 + level * 0.03 * m).toFixed(4)})`;
    avatarEl.style.filter = settings.glow
      ? `drop-shadow(0 0 ${(4 + level * 22).toFixed(1)}px ${settings.glow_color}${Math.round(40 + level * 215)
          .toString(16)
          .padStart(2, "0")})`
      : "none";

    if (debugMode) debugEl.textContent = `volume ${rawVolume.toFixed(3)} level ${level.toFixed(2)} mouth ${mouth} eyes ${eyes}`;
    requestAnimationFrame(frame);
  }

  load();
  connect();
  scheduleBlink();
})();
