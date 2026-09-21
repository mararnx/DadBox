# Box software

A Python service on a Raspberry Pi Zero 2 W (Raspberry Pi OS Lite 64-bit),
under `systemd`, reachable over Tailscale ([ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md)).
Read [docs/DEV-PROCESS.md](../docs/DEV-PROCESS.md) for how it is built and
debugged, [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for the state
machine and [docs/PROTOCOL.md](../docs/PROTOCOL.md) for the wire contract.

## Shape of it

| Module | Job | Exists |
| --- | --- | --- |
| `ctl` | **Build this first.** `dadboxctl` over a Unix socket: `state`, `record start/stop`, `play`, `inbox`, `outbox`, `checkin`, `modem on/off`, `led test`, `lock on/off`, `sim …` | stub |
| `ui` | Record and Play buttons (GPIO, internal pull-ups, ≥ 0.5 s press), their RGB lights (GPIO software PWM), travel lock, status LEDs, chimes, quiet hours, mute | no |
| `audio` | ALSA capture straight to `/data` while recording — the mic's supply is the record button's red-LED pin; trim and `ffmpeg` → Opus on stop; playback via the amp (SD pin gated) | no |
| `queue` | `/data/outbox`, `/data/inbox`; container + CRC; fsync-then-rename; resume from `upload-state` | no |
| `link` | Modem (SIM7670G HAT, USB Ethernet) power key; wait for the interface; check-in on the `state.poll_plan` cadence (ADR 0015), chunked upload, download; backoff forever | no |
| `power` | INA219 gauge (UPS Module 3S) over I²C; mains present (sign of the battery current); low-battery behaviour; cores/clock tuning | no |
| `state` | The lights/link/power/fault state machines — pure Python, unit-tested on the Mac | yes |

## Layout rule

Everything that isn't a driver is plain Python with no `RPi`/ALSA import, so
it runs and tests on the Mac. Drivers are thin and swappable (a fake GPIO
and a fake ALSA for `tools/fakebox`).

## First target — M0

`dadboxctl`, then: `record start` (or the record button) → `arecord` to
`/data` → `record stop` → trim → `ffmpeg` → Opus → press play → hear it. No
network. Listen inside the cardboard box.

## Files

- `dadbox/` — the package. `python3 -m dadbox` runs the service.
- `systemd/dadbox.service` — the unit.
- `setup/` — `config.txt` lines, the overlay, the `/data` partition, Tailscale.
- `tests/` — `pytest`, on the Mac.
- `pyproject.toml` — deps: `gpiozero`, `sounddevice`, `smbus2`, `requests`.
  `ffmpeg` and `alsa-utils` from apt.
