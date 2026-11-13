from __future__ import annotations

import threading

import numpy as np
import sounddevice as sd

BLOCK_SIZE = 1024


def resolve_device(configured: str | None) -> int | None:
    """Map a saved device name to PortAudio's current index (indices shift between
    runs, names don't). With no choice saved, PortAudio's default input is often a
    raw ALSA card that records silence on PipeWire/PulseAudio systems, so prefer
    the sound server's own device."""
    devices = sd.query_devices()
    if configured:
        for index, info in enumerate(devices):
            if info["name"] == configured and info.get("max_input_channels", 0) > 0:
                return index
    for preferred in ("pulse", "pipewire"):
        for index, info in enumerate(devices):
            if info["name"] == preferred and info.get("max_input_channels", 0) > 0:
                return index
    return None


def list_input_devices() -> list[dict]:
    devices = []
    try:
        default_input = sd.default.device[0]
    except (TypeError, IndexError):
        default_input = None
    for index, info in enumerate(sd.query_devices()):
        if info.get("max_input_channels", 0) > 0:
            devices.append(
                {
                    "name": info["name"],
                    "is_default": index == default_input,
                }
            )
    return devices


class AudioEngine:
    """Captures mic audio on a PortAudio callback thread and exposes a
    gain/gate-adjusted volume (0..1)."""

    def __init__(self, device: str | None, gain: float, gate: float) -> None:
        self.device = device
        self.gain = gain
        self.gate = gate
        self._lock = threading.Lock()
        self._volume = 0.0
        self._raw = 0.0
        self._stream: sd.InputStream | None = None
        self.error: str | None = None
        self.active_device_name: str | None = None

    def start(self) -> None:
        try:
            device = resolve_device(self.device)
            device_info = sd.query_devices(device, "input")
            samplerate = int(device_info["default_samplerate"])
            self.active_device_name = device_info["name"]
            self._stream = sd.InputStream(
                device=device,
                channels=1,
                samplerate=samplerate,
                blocksize=BLOCK_SIZE,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()
            self.error = None
        except Exception as exc:  # pragma: no cover - hardware dependent
            self.error = str(exc)
            self.active_device_name = None
            self._stream = None

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def restart(self, device: str | None, gain: float, gate: float) -> None:
        self.stop()
        self.device = device
        self.gain = gain
        self.gate = gate
        self.start()

    def get_levels(self) -> tuple[float, float]:
        """(gated volume driving the avatar, raw mic RMS for the tuning meter)"""
        with self._lock:
            return self._volume, self._raw

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        rms = float(np.sqrt(np.mean(np.square(indata[:, 0])) + 1e-12))
        # gate against the raw level so its meaning doesn't shift with gain
        volume = 0.0 if rms < self.gate else min(1.0, (rms - self.gate) * self.gain)
        with self._lock:
            self._volume = volume
            self._raw = rms
