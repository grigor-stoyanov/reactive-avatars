(() => {
  const $ = (id) => document.getElementById(id);
  const avatarEl = $("avatar");
  const idleEl = $("idle");
  const talkingEl = $("talking");
  const debugEl = $("debug");

  const TALK_THRESHOLD = 0.06;
  const TALK_HOLD_MS = 600;

  const debugMode = new URLSearchParams(location.search).has("debug");
  if (debugMode) debugEl.hidden = false;

  let settings = { motion: 1, glow: true, glow_color: "#45f0a6" };
  let rawVolume = 0;
  let level = 0; // smoothed, normalised 0..1
  let peakRef = 0.3; // auto-gain reference, decays toward the floor
  let lastLoudAt = -Infinity;

  const lerp = (a, b, t) => a + (b - a) * t;
  const clamp01 = (v) => Math.min(1, Math.max(0, v));

  function applyConfig(cfg) {
    settings = cfg;
    if (idleEl.getAttribute("src") !== cfg.idle_image) idleEl.src = cfg.idle_image;
    if (cfg.talking_image) {
      if (talkingEl.getAttribute("src") !== cfg.talking_image) talkingEl.src = cfg.talking_image;
    } else {
      talkingEl.removeAttribute("src");
    }
  }

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/audio`);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.config) applyConfig(msg.config);
      else rawVolume = msg.volume;
    };
    ws.onclose = () => setTimeout(connect, 1000);
    ws.onerror = () => ws.close();
  }

  function frame(now) {
    // Auto-gain: normalise against a decaying peak so a quiet mic still gets a
    // full reaction without pushing a loud one past full scale.
    peakRef = Math.max(rawVolume, peakRef * 0.995, 0.25);
    const shaped = Math.pow(clamp01(rawVolume / peakRef), 0.6);
    // fast attack, slower release
    level = lerp(level, shaped, shaped > level ? 0.55 : 0.14);

    if (rawVolume > TALK_THRESHOLD) lastLoudAt = now;
    const talking = now - lastLoudAt < TALK_HOLD_MS;

    // Two images: swap while talking. One image: just the motion + glow below.
    const swap = Boolean(settings.talking_image);
    talkingEl.hidden = !(swap && talking);
    idleEl.hidden = swap && talking;

    const m = settings.motion;
    const breathe = talking ? 0 : Math.sin(now / 1400) * 0.8 * m;
    const lift = -level * 4 * m + breathe; // percent of avatar height
    const scale = 1 + level * 0.06 * m;
    avatarEl.style.transform = `translateY(${lift.toFixed(2)}%) scale(${scale.toFixed(4)})`;

    const glow = settings.glow
      ? `drop-shadow(0 0 ${(4 + level * 22).toFixed(1)}px ${settings.glow_color}${Math.round(40 + level * 215)
          .toString(16)
          .padStart(2, "0")})`
      : "none";
    idleEl.style.filter = talkingEl.style.filter = glow;

    if (debugMode) {
      debugEl.textContent = `volume ${rawVolume.toFixed(3)}  level ${level.toFixed(2)}  ${talking ? "talking" : "idle"}`;
    }
    requestAnimationFrame(frame);
  }

  connect();
  requestAnimationFrame(frame);
})();
