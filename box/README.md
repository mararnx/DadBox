# Box software

A Python service on a Raspberry Pi Zero 2 W (Raspberry Pi OS Lite 64-bit),
under `systemd`, reachable over Tailscale ([ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md)).
Read [docs/DEV-PROCESS.md](../docs/DEV-PROCESS.md) for how it is built and
debugged, [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for the state
machine and [docs/PROTOCOL.md](../docs/PROTOCOL.md) for the wire contract.

## Shape of it

| Module | Job | Exists |
| --- | --- | --- |
| `ctl` | **Build this first.** `dadboxctl` over a Unix socket: `state`, `lid open/close`, `play`, `checkin`, `modem on/off`, `ring test`, `sim …` | no |
| `ui` | Lid (reed on GPIO, interrupt), play button, ring (WS2812 over SPI, gated), status LEDs, chimes, quiet hours, mute | no |
| `audio` | ALSA capture straight to `/data` while the lid is open; `ffmpeg` → Opus on close; playback via the amp (SD pin gated) | no |
| `queue` | `/data/outbox`, `/data/inbox`; container + CRC; fsync-then-rename; resume from `upload-state` | no |
| `link` | Modem PWRKEY; wait for the interface; check-in on the `state.poll_plan` cadence (ADR 0015), chunked upload, download; backoff forever | no |
| `power` | INA219 gauge (UPS HAT) over I²C; mains present; low-battery behaviour; cores/clock tuning | no |
| `state` | The ring/link/power/fault state machines — pure Python, unit-tested on the Mac | no |

## Layout rule

Everything that isn't a driver is plain Python with no `RPi`/ALSA import, so
it runs and tests on the Mac. Drivers are thin and swappable (a fake GPIO
and a fake ALSA for `tools/fakebox`).

## First target — M0

`dadboxctl`, then: lid open (a toggle switch on the bench) → `arecord` to
`/data` → lid close → trim → `ffmpeg` → Opus → press play → hear it. No
network. Listen inside the cardboard box.

## Files

- `dadbox/` — the package. `python3 -m dadbox` runs the service.
- `systemd/dadbox.service` — the unit.
- `setup/` — `config.txt` lines, the overlay, the `/data` partition, Tailscale.
- `pyproject.toml` — deps: `gpiozero`, `pyalsaaudio` or `sounddevice`,
  `rpi_ws281x`, `smbus2`, `requests`. `ffmpeg` and `alsa-utils` from apt.
