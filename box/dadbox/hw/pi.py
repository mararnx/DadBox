"""The Pi Zero 2 W drivers: gpiozero for pins, arecord/ffmpeg/aplay for audio.

Pin numbers are BCM and are the proposal in `hal.py`; every one of them is
to be confirmed with the parts in hand and then fixed here. Nothing outside
this file knows a pin number.
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from typing import Callable, Optional, Tuple

from ..dsp import BLOCK_BYTES, BLOCK_MS, RATE, SPEECH_RMS, chime_pcm, rms
from ..gestures import Button
from ..hal import Hardware
from ..lights import Frame

log = logging.getLogger("dadbox.hw")

PIN_MIC_AND_RECORD_RED = 17      # one pin: the mic's VDD and the record button's red ring
PIN_RECORD_GREEN, PIN_RECORD_BLUE = 27, 22
PIN_PLAY_RED, PIN_PLAY_GREEN, PIN_PLAY_BLUE = 23, 24, 25
PIN_RECORD_SWITCH, PIN_PLAY_SWITCH = 5, 6
PIN_LINK_LED, PIN_POWER_LED = 12, 13
PIN_AMP_SD = 16                  # MAX98357A SD_MODE — owned by the kernel's voicehat driver, see PiAmpGate
PIN_MODEM_PWRKEY = 26            # SIM7670G HAT PWRKEY — wiring to confirm
ALSA_DEVICE = os.environ.get("DADBOX_ALSA", "default")
DEBOUNCE_S = 0.02


class PiButtons:
    def __init__(self):
        from gpiozero import Button as GZButton
        self.record = GZButton(PIN_RECORD_SWITCH, pull_up=True, bounce_time=DEBOUNCE_S)
        self.play = GZButton(PIN_PLAY_SWITCH, pull_up=True, bounce_time=DEBOUNCE_S)

    def watch(self, on_contact: Callable[[Button, bool], None]) -> None:
        self.record.when_pressed = lambda: on_contact(Button.RECORD, True)
        self.record.when_released = lambda: on_contact(Button.RECORD, False)
        self.play.when_pressed = lambda: on_contact(Button.PLAY, True)
        self.play.when_released = lambda: on_contact(Button.PLAY, False)


class PiMicGate:
    def __init__(self):
        from gpiozero import DigitalOutputDevice
        self.pin = DigitalOutputDevice(PIN_MIC_AND_RECORD_RED, initial_value=False)

    def set(self, on: bool) -> None:
        self.pin.value = 1 if on else 0

    def is_on(self) -> bool:
        return bool(self.pin.value)


class PiButtonLights:
    """Software PWM on five pins. The sixth — record red — is the mic gate's and is ignored here."""

    def __init__(self):
        from gpiozero import PWMLED
        self.rg, self.rb = PWMLED(PIN_RECORD_GREEN), PWMLED(PIN_RECORD_BLUE)
        self.pr, self.pg, self.pb = PWMLED(PIN_PLAY_RED), PWMLED(PIN_PLAY_GREEN), PWMLED(PIN_PLAY_BLUE)

    def write(self, frame: Frame) -> None:
        _, g, b = frame.record
        self.rg.value, self.rb.value = g, b
        self.pr.value, self.pg.value, self.pb.value = frame.play


class PiStatusLeds:
    def __init__(self):
        from gpiozero import LED
        self.link, self.power = LED(PIN_LINK_LED), LED(PIN_POWER_LED)

    def write(self, link_on: bool, power_on: bool) -> None:
        self.link.value, self.power.value = link_on, power_on


class PiAmpGate:
    """The amp's SD_MODE pin (GPIO 16) belongs to the kernel: the
    googlevoicehat-soundcard driver claims it as `sdmode` and raises it only
    while a playback stream is open, low otherwise. Claiming it from user
    space fails with "GPIO busy" (found on the bench, 2026-09-24). The amp is
    therefore gated by the driver; this records the intent for the logs."""

    def __init__(self):
        self.on = False

    def set(self, on: bool) -> None:
        self.on = on


class PiModem:
    """USB Ethernet interface from the SIM7670G HAT; power key on a GPIO (to confirm)."""

    def __init__(self):
        try:
            from gpiozero import DigitalOutputDevice
            self.pwrkey = DigitalOutputDevice(PIN_MODEM_PWRKEY, initial_value=False)
        except Exception:                                  # noqa: BLE001 — no pin yet: modem is always on
            self.pwrkey = None
        self._want_on = True

    def power(self, on: bool) -> None:
        if self._want_on == on or self.pwrkey is None:
            return
        self._want_on = on
        self.pwrkey.on(); time.sleep(1.5); self.pwrkey.off()   # SIMCom-style pulse; confirm from the wiki

    def is_up(self) -> bool:
        """A route out exists — through the modem's USB Ethernet in the field, or
        Wi-Fi on the bench. The server round then says whether it really works."""
        try:
            out = subprocess.run(["ip", "-4", "route", "show", "default"], capture_output=True, text=True, timeout=5).stdout
        except Exception:                                  # noqa: BLE001
            return False
        return has_default_route(out)

    def rssi(self) -> Optional[int]:
        return None                                        # AT+CSQ on the AT port, later


def has_default_route(ip_route_output: str) -> bool:
    """`ip -4 route show default` prints one line per default route, e.g.
    `default via 192.168.225.1 dev usb0 proto dhcp metric 100`."""
    return any(line.split()[:1] == ["default"] and " dev " in line for line in ip_route_output.splitlines())


class PiPower:
    """No battery yet (ADR 0019). With the UPS Module 3S: INA219 over I²C here."""

    def read(self) -> Tuple[bool, Optional[int], bool]:
        return True, None, False


class _Capture:
    def __init__(self, path: str, on_level, on_end):
        self.proc = subprocess.Popen(
            ["arecord", "-q", "-D", ALSA_DEVICE, "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._pump, args=(path, on_level, on_end), daemon=True)
        self.thread.start()

    def _pump(self, path, on_level, on_end):
        ok, reason = True, ""
        try:
            with open(path, "wb") as f:
                start = time.monotonic()
                last_sync = start
                silence_s = 0.0
                settled = False
                while not self._stop.is_set():
                    block = self.proc.stdout.read(BLOCK_BYTES)
                    if not block:
                        ok, reason = False, "arecord ended"
                        break
                    if not settled:                       # drop the mic's power-up click
                        settled = True
                        continue
                    f.write(block)
                    now = time.monotonic()
                    if now - last_sync >= 1.0:
                        f.flush(); os.fsync(f.fileno()); last_sync = now
                    silence_s = silence_s + BLOCK_MS / 1000 if rms(block) < SPEECH_RMS else 0.0
                    on_level(now - start, silence_s)
                f.flush(); os.fsync(f.fileno())
        except Exception as e:                             # noqa: BLE001
            ok, reason = False, str(e)
        finally:
            if self.proc.poll() is None:
                self.proc.terminate()
            on_end(ok, reason)

    def stop(self) -> None:
        self._stop.set()
        if self.proc.poll() is None:
            self.proc.terminate()


class PiAudio:
    def start_capture(self, path, on_level, on_end):
        return _Capture(path, on_level, on_end)

    def encode(self, pcm_path: str) -> Tuple[bytes, int]:
        size = os.path.getsize(pcm_path)
        duration_ms = int(size / 2 / RATE * 1000)
        out = subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", pcm_path,
             "-c:a", "libopus", "-b:a", "16k", "-application", "voip", "-f", "ogg", "-"],
            capture_output=True, check=True)
        return out.stdout, duration_ms

    def play(self, audio: bytes, codec: int, volume: int, on_end: Callable[[bool], None],
             duration_ms: int = 0) -> Callable[[], None]:
        gain = max(0, min(100, volume)) / 100.0
        dec = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-i", "pipe:0", "-af", f"volume={gain}", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        out = subprocess.Popen(["aplay", "-q", "-D", ALSA_DEVICE, "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"],
                               stdin=dec.stdout)

        def feed():
            try:
                dec.stdin.write(audio); dec.stdin.close()
            except BrokenPipeError:
                pass
            rc = out.wait()
            on_end(rc == 0)
        threading.Thread(target=feed, daemon=True).start()

        def stop():
            for p in (dec, out):
                if p.poll() is None:
                    p.terminate()
        return stop

    def chime(self, volume: int) -> None:
        gain = max(0, min(100, volume)) / 100.0
        pcm = chime_pcm()
        if gain < 1.0:
            import array
            a = array.array("h"); a.frombytes(pcm)
            pcm = array.array("h", (int(s * gain) for s in a)).tobytes()
        subprocess.run(["aplay", "-q", "-D", ALSA_DEVICE, "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"],
                       input=pcm, check=False)


def make_hardware() -> Hardware:
    return Hardware(buttons=PiButtons(), lights=PiButtonLights(), status=PiStatusLeds(), mic=PiMicGate(),
                    amp=PiAmpGate(), modem=PiModem(), power=PiPower(), audio=PiAudio())
