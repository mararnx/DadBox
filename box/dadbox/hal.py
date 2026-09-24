"""The hardware seam. Everything below this line has two implementations: the
Pi (`hw/pi.py`, gpiozero and ALSA) and the simulator (`sim/`). The core and
the workers only ever see these interfaces.

Proposed pin map (BCM numbers; verify with the parts in hand). Every wire, per part and per
header pin, is in hardware/schematics/WIRING.md — change it together with hw/pi.py:

    GPIO 17   Record button red LED **and** the mic's 3.3 V supply — the wiring fact
    GPIO 27   Record button green        GPIO 22   Record button blue
    GPIO 23   Play button red            GPIO 24   Play button green      GPIO 25   Play button blue
    GPIO 5    Record switch (to GND, internal pull-up)
    GPIO 6    Play switch   (to GND, internal pull-up)
    GPIO 12   LINK status LED            GPIO 13   POWER status LED
    GPIO 16   MAX98357A SD_MODE — driven by the kernel's voicehat driver, only while audio plays
    GPIO 26   Modem power key (SIM7670G HAT PWRKEY — wiring to confirm)
    GPIO 18/19/20/21  I2S (googlevoicehat-soundcard)   GPIO 2/3  I²C (INA219, later)   GPIO 14/15  UART console
"""
from __future__ import annotations

from typing import Callable, Optional, Protocol, Tuple

from .gestures import Button
from .lights import Frame


class Buttons(Protocol):
    def watch(self, on_contact: Callable[[Button, bool], None]) -> None:
        """Call `on_contact(button, is_down)` on every debounced contact change."""


class ButtonLights(Protocol):
    def write(self, frame: Frame) -> None:
        """Levels 0..1 for both RGB rings. The driver must ignore `frame.record[0]`:
        that pin belongs to `MicGate`, and the renderer keeps it 0 or 1 anyway."""


class StatusLeds(Protocol):
    def write(self, link_on: bool, power_on: bool) -> None: ...


class MicGate(Protocol):
    """The record button's red light and the microphone's supply: one pin."""
    def set(self, on: bool) -> None: ...
    def is_on(self) -> bool: ...


class AmpGate(Protocol):
    def set(self, on: bool) -> None: ...


class Modem(Protocol):
    def power(self, on: bool) -> None: ...
    def is_up(self) -> bool:
        """The USB Ethernet interface exists and has an address."""
    def rssi(self) -> Optional[int]: ...


class PowerGauge(Protocol):
    def read(self) -> Tuple[bool, Optional[int], bool]:
        """(mains present, battery %, charging). Battery None when none is fitted (ADR 0019)."""


class CaptureHandle(Protocol):
    def stop(self) -> None: ...


class AudioBackend(Protocol):
    """ALSA + ffmpeg on the Pi; synthesis in the simulator."""

    def start_capture(self, path: str, on_level: Callable[[float, float], None],
                      on_end: Callable[[bool, str], None]) -> CaptureHandle:
        """Stream 16 kHz s16le mono PCM to `path`, fsyncing at least every second.
        `on_level(elapsed_s, silence_s)` every ~100 ms; `on_end(ok, reason)` once."""

    def encode(self, pcm_path: str) -> Tuple[bytes, int]:
        """Trimmed PCM → (Ogg Opus bytes, duration_ms). Raises on failure."""

    def play(self, audio: bytes, codec: int, volume: int, on_end: Callable[[bool], None],
             duration_ms: int = 0) -> Callable[[], None]:
        """Decode and play; returns a stop function. `duration_ms` is the header's
        word on the length — the simulator paces itself by it."""

    def chime(self, volume: int) -> None: ...


class Hardware:
    """The bundle the service is handed."""

    def __init__(self, *, buttons: Buttons, lights: ButtonLights, status: StatusLeds, mic: MicGate,
                 amp: AmpGate, modem: Modem, power: PowerGauge, audio: AudioBackend):
        self.buttons, self.lights, self.status = buttons, lights, status
        self.mic, self.amp, self.modem, self.power, self.audio = mic, amp, modem, power, audio
