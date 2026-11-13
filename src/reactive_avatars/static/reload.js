// Injected into every pack page: reloads it when you pick another avatar or edit this
// pack's layers in settings, so OBS never needs touching.
(() => {
  if (window.RA_PREVIEW) return; // previewing a pack: never follow the live avatar
  const proto = location.protocol === "https:" ? "wss" : "ws";
  function watch() {
    const ws = new WebSocket(`${proto}://${location.host}/ws/audio`);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.config && (msg.config.avatar !== window.RA_AVATAR || msg.config.rev !== window.RA_REV)) {
        location.reload();
      }
    };
    ws.onclose = () => setTimeout(watch, 1000);
    ws.onerror = () => ws.close();
  }
  watch();
})();
