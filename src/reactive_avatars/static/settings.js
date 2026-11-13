(() => {
  const $ = (id) => document.getElementById(id);
  const deviceEl = $("device");
  const gainEl = $("gain");
  const gateEl = $("gate");
  const gainValEl = $("gainVal");
  const gateValEl = $("gateVal");
  const rawFillEl = $("rawFill");
  const outFillEl = $("outFill");
  const gateMarkEl = $("gateMark");
  const statusDotEl = $("statusDot");
  const statusTextEl = $("statusText");
  const saveStatusEl = $("saveStatus");
  const motionEl = $("motion");
  const motionValEl = $("motionVal");
  const glowEl = $("glow");
  const glowColorEl = $("glowColor");

  // the meter shows raw RMS over this range, which is also the gate slider's range
  const METER_MAX = 0.3;

  $("overlayUrl").textContent = `${location.origin}/`;

  function paintGateMark() {
    gateMarkEl.style.left = `${(Number(gateEl.value) / METER_MAX) * 100}%`;
  }

  function showStatus(cfg) {
    if (cfg.error) {
      statusDotEl.classList.add("bad");
      statusTextEl.textContent = `mic error: ${cfg.error}`;
    } else {
      statusDotEl.classList.remove("bad");
      statusTextEl.textContent = `capturing from: ${cfg.active_device_name ?? "unknown"}`;
    }
  }

  async function load() {
    const [devices, cfg] = await Promise.all([
      fetch("/api/devices").then((r) => r.json()),
      fetch("/api/config").then((r) => r.json()),
    ]);

    const auto = document.createElement("option");
    auto.value = "";
    auto.textContent = "Automatic (system sound server)";
    deviceEl.replaceChildren(auto);
    for (const d of devices) {
      const opt = document.createElement("option");
      opt.value = d.index;
      opt.textContent = d.name;
      deviceEl.appendChild(opt);
    }

    deviceEl.value = cfg.device === null ? "" : String(cfg.device);
    gainEl.value = cfg.gain;
    gateEl.value = cfg.gate;
    gainValEl.textContent = `${Number(cfg.gain).toFixed(1)}x`;
    gateValEl.textContent = Number(cfg.gate).toFixed(3);
    motionEl.value = cfg.motion;
    motionValEl.textContent = `${Number(cfg.motion).toFixed(1)}x`;
    glowEl.checked = cfg.glow;
    glowColorEl.value = cfg.glow_color;
    paintGateMark();
    showStatus(cfg);
    paintImages(cfg);
  }

  function paintImages(cfg) {
    $("idlePreview").src = cfg.idle_image;
    const talking = $("talkingPreview");
    talking.hidden = !cfg.talking_image;
    if (cfg.talking_image) talking.src = cfg.talking_image;
  }

  async function upload(slot, file) {
    if (!file) return;
    saveStatusEl.textContent = "Uploading…";
    const res = await fetch(`/api/avatar/${slot}`, {
      method: "PUT",
      headers: { "Content-Type": file.type },
      body: file,
    });
    if (!res.ok) {
      saveStatusEl.textContent = (await res.json()).detail ?? "Upload failed.";
      return;
    }
    paintImages(await res.json());
    saveStatusEl.textContent = "Avatar updated.";
  }

  async function reset(slot) {
    paintImages(await fetch(`/api/avatar/${slot}`, { method: "DELETE" }).then((r) => r.json()));
  }

  for (const slot of ["idle", "talking"]) {
    $(`${slot}File`).addEventListener("change", (e) => upload(slot, e.target.files[0]));
    $(`${slot}Reset`).addEventListener("click", () => reset(slot));
  }

  motionEl.addEventListener("input", () => {
    motionValEl.textContent = `${Number(motionEl.value).toFixed(1)}x`;
  });

  gainEl.addEventListener("input", () => {
    gainValEl.textContent = `${Number(gainEl.value).toFixed(1)}x`;
  });

  gateEl.addEventListener("input", () => {
    gateValEl.textContent = Number(gateEl.value).toFixed(3);
    paintGateMark();
  });

  $("save").addEventListener("click", async () => {
    saveStatusEl.textContent = "Applying…";
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        device: deviceEl.value === "" ? null : Number(deviceEl.value),
        gain: Number(gainEl.value),
        gate: Number(gateEl.value),
        motion: Number(motionEl.value),
        glow: glowEl.checked,
        glow_color: glowColorEl.value,
      }),
    });
    const cfg = await res.json();
    showStatus(cfg);
    saveStatusEl.textContent = cfg.error ? "Could not open that microphone." : "Saved.";
  });

  let quitting = false;
  $("quit").addEventListener("click", async () => {
    quitting = true;
    await fetch("/api/quit", { method: "POST" }).catch(() => {});
    document.body.innerHTML =
      '<p style="font:16px system-ui;padding:40px;color:#e8f6f0">reactive-avatars has stopped. You can close this tab.</p>';
  });

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/audio?role=settings`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.config) return;
      rawFillEl.style.width = `${Math.min(100, (data.raw / METER_MAX) * 100)}%`;
      outFillEl.style.width = `${Math.round(data.volume * 100)}%`;
    };
    ws.onclose = () => {
      if (!quitting) setTimeout(connect, 1000);
    };
    ws.onerror = () => ws.close();
  }

  load();
  connect();
})();
