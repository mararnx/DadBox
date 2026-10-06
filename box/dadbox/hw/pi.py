"""The Pi Zero 2 W drivers: gpiozero for pins, arecord/ffmpeg/aplay for audio.

Pin numbers are BCM and are the proposal in `hal.py` and hardware/schematics/WIRING.md; every one of them is
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

from ..dsp import BLOCK_BYTES, BLOCK_MS, RATE, SPEECH_LEVEL, chime_pcm, level
from ..gestures import Button
from ..hal import Hardware
from ..lights import Frame

log = logging.getLogger("dadbox.hw")

PIN_MIC_AND_RECORD_RED = 17      # one pin: the mic's VDD and the record button's red ring
PIN_RECORD_GREEN, PIN_RECORD_BLUE = 27, 22
PIN_PLAY_RED, PIN_PLAY_GREEN, PIN_PLAY_BLUE = 23, 24, 25
PIN_RECORD_SWITCH, PIN_PLAY_SWITCH = 5, 6
PIN_AMP_SD = 16                  # MAX98357A SD_MODE — owned by the kernel's voicehat driver, see PiAmpGate
PIN_MODEM_PWRKEY = 4             # pin 7, joined to the HAT's pin 7 (P4 = PWR) by one pin from below (ADR 0026); DIP 3 on; high = key pressed
MODEM_AT_PORT = os.environ.get("DADBOX_MODEM_AT", "/dev/ttyACM0")   # the HAT enumerates as 05c6:9330, AT on ACM0
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


BOOTLIGHT_STOP = "/run/dadbox/bootlight-stop"


def _end_bootlight() -> None:
    """dadbox-bootlight.service cycles Play's colours from early boot (ADR 0024 §7).
    It stops itself when this file appears; wait out its last step (0.4 s) so it
    lets go of the pins before the PWM takes them, and the rainbow carries on."""
    try:
        open(BOOTLIGHT_STOP, "w").close()
    except OSError:
        return                                   # not under systemd (the Mac, a test)
    time.sleep(0.5)


class PiButtonLights:
    """Software PWM on five pins. The sixth — record red — is the mic gate's and is ignored here."""

    def __init__(self):
        from gpiozero import PWMLED
        _end_bootlight()
        self.rg, self.rb = PWMLED(PIN_RECORD_GREEN), PWMLED(PIN_RECORD_BLUE)
        self.pr, self.pg, self.pb = PWMLED(PIN_PLAY_RED), PWMLED(PIN_PLAY_GREEN), PWMLED(PIN_PLAY_BLUE)

    def write(self, frame: Frame) -> None:
        _, g, b = frame.record
        self.rg.value, self.rb.value = g, b
        self.pr.value, self.pg.value, self.pb.value = frame.play


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
    """RNDIS `usb0` from the SIM7670G HAT, AT commands on `ttyACM0`, power key on GPIO 4.
    GPIO 4 has a pull-up at boot; `gpio=4=op,dl` in config.txt holds it low until this claims it,
    or the key would be held through boot (≥ 2.5 s turns the modem off).
    The power key is not yet proven on the bench: the first box is mains only and never
    switches the modem off (ADR 0019), so `power` only matters once the battery is fitted."""

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
        self.pwrkey.on(); time.sleep(0.5 if on else 3.0); self.pwrkey.off()   # SIM767x: on ≥ 50 ms, off ≥ 2.5 s

    def is_up(self) -> bool:
        """A route out exists — through the modem's USB Ethernet in the field, or
        Wi-Fi on the bench. The server round then says whether it really works."""
        try:
            out = subprocess.run(["ip", "-4", "route", "show", "default"], capture_output=True, text=True, timeout=5).stdout
        except Exception:                                  # noqa: BLE001
            return False
        return has_default_route(out)

    def rssi(self) -> Optional[int]:
        """Received signal strength in dBm from `AT+CSQ`, or None when the modem does not answer."""
        try:
            return csq_to_dbm(at_command(MODEM_AT_PORT, "AT+CSQ"))
        except Exception as e:                             # noqa: BLE001 — no modem, busy port: no reading
            log.debug("rssi: %s", e)
            return None


def at_command(port: str, line: str, timeout_s: float = 2.0) -> str:
    """One AT command on a raw tty; returns what came back up to OK or ERROR."""
    import select
    import termios
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        attrs = termios.tcgetattr(fd)
        attrs[0] = attrs[1] = attrs[3] = 0                 # raw: no input/output processing, no echo
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        termios.tcflush(fd, termios.TCIOFLUSH)
        os.write(fd, (line + "\r").encode())
        buf, end = b"", time.monotonic() + timeout_s
        while time.monotonic() < end and not buf.rstrip().endswith((b"OK", b"ERROR")):
            if select.select([fd], [], [], 0.1)[0]:
                buf += os.read(fd, 1024)
        return buf.decode(errors="replace")
    finally:
        os.close(fd)


def csq_to_dbm(reply: str) -> Optional[int]:
    """`+CSQ: 20,0` → -73 dBm (3GPP 27.007: 0 is ≤ -113, 31 is ≥ -51, 99 unknown)."""
    for line in reply.splitlines():
        if line.startswith("+CSQ:"):
            n = int(line.split(":")[1].split(",")[0])
            return None if n == 99 else -113 + 2 * min(n, 31)
    return None


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
                    if not block:                         # stop() terminated arecord mid-read: a normal end
                        if not self._stop.is_set():
                            ok, reason = False, "arecord ended"
                        break
                    if not settled:                       # drop the mic's power-up click
                        settled = True
                        continue
                    f.write(block)
                    now = time.monotonic()
                    if now - last_sync >= 1.0:
                        f.flush(); os.fsync(f.fileno()); last_sync = now
                    silence_s = silence_s + BLOCK_MS / 1000 if level(block) < SPEECH_LEVEL else 0.0
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
    return Hardware(buttons=PiButtons(), lights=PiButtonLights(), mic=PiMicGate(),
                    amp=PiAmpGate(), modem=PiModem(), power=PiPower(), audio=PiAudio())
