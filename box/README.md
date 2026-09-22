# Box software

A Python service on a Raspberry Pi Zero 2 W (Raspberry Pi OS Lite 64-bit),
under `systemd`, reachable over Tailscale ([ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md)).
Read [DESIGN.md](DESIGN.md) for how it is built, [docs/DEV-PROCESS.md](../docs/DEV-PROCESS.md)
for how it is debugged, [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for
the state machine and [docs/PROTOCOL.md](../docs/PROTOCOL.md) for the wire
contract.

## Shape of it

A pure core (`core.py`: events in, actions out, no I/O) and an effectful
shell around it. The same core, workers, store and link run on the Pi and on
the Mac; only the hardware interfaces in `hal.py` have two implementations —
`hw/pi.py` and `sim/`.

| Module | Job | Exists |
| --- | --- | --- |
| `core` | the state machine: modes, presses, lock, replay, quiet hours, cadence, light plans, telemetry | yes, tested |
| `gestures` | contacts → presses (≥ 0.5 s), both held 3 s = travel lock | yes, tested |
| `lights` | plans → pin levels; **record red is 0 or 1, asserted** | yes, tested |
| `settings`, `dsp`, `state`, `container` | settings + quiet hours, RMS/trim/chime, the rules, DBX1 + AES-GCM | yes, tested |
| `store` | `/data`: outbox, inbox, capture, seq, lock, keys — fsync-then-rename | yes, tested |
| `link` | `Client` (PROTOCOL.md) + `LinkWorker` (upload, played, check-in, download, backoff forever, modem gating) | yes, tested |
| `audio` | capture → trim → Opus → seal → fsync → *got it*; inbox → open → play; amp gate | yes, tested |
| `service`, `ctl` | the loop, the lights driver, `dadboxctl` over a Unix socket | yes, tested |
| `hw/pi` | gpiozero + `arecord`/`ffmpeg`/`aplay` + `ip addr` for the modem | written, **untested on a Pi** |
| `sim/` | fake drivers, synthetic audio, in-process server, web UI | yes |

## Run it

```bash
python3 -m venv ~/.venvs/dadbox && ~/.venvs/dadbox/bin/pip install cryptography requests pytest
cd box
~/.venvs/dadbox/bin/python -m pytest -q                 # 70 tests, ~7 s, no hardware
~/.venvs/dadbox/bin/python -m dadbox.sim                # the virtual box: http://127.0.0.1:8765
~/.venvs/dadbox/bin/python -m dadbox.sim --speed 20 --real-server   # against the live Supabase server
DADBOX_CTL=~/.dadbox-sim/ctl.sock ~/.venvs/dadbox/bin/python -m dadbox.ctl state
```

On the Pi: `python3 -m dadbox` (see `systemd/dadbox.service`), `dadboxctl`.

## Layout rule

Everything that isn't a driver is plain Python with no `RPi`/ALSA import, so
it runs and tests on the Mac. Drivers are thin and swappable.

## Files

- `dadbox/` — the package. `python3 -m dadbox` runs the service; `python3 -m dadbox.sim` the simulator.
- `DESIGN.md` — how it is built, what was decided, what to check in the simulator.
- `systemd/dadbox.service` — the unit.
- `setup/` — `config.txt` lines, the overlay, the `/data` partition, Tailscale.
- `tests/` — `pytest`, on the Mac.
- `pyproject.toml` — deps: `requests`, `cryptography`; on the Pi also `gpiozero`, `smbus2`, `systemd-python`.
  `ffmpeg` and `alsa-utils` from apt.
