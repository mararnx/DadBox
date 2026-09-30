# DadBox

A voice messaging device for a parent and child who live apart. The child has
an aluminium box with two lit buttons — record and play
([ADR 0016](docs/decisions/0016-two-buttons-no-lid.md)); the parent has an
iPhone. Read [docs/BRIEF.md](docs/BRIEF.md) and [docs/REVIEW.md](docs/REVIEW.md)
before making assumptions about the design.

## Streams

| Stream | Where | Blocked by |
| --- | --- | --- |
| Shopping | `hardware/SHOPPING-LIST.md` | bench parts ordered 2026-09-21; antenna waits for the modem HAT, battery parts for a current measurement |
| Box | `box/` (Python service on a Pi Zero 2 W, Raspberry Pi OS Lite); `box/DESIGN.md`; the whole service runs on the Mac as `python3 -m dadbox.sim` | parts arriving; drivers in `box/dadbox/hw/pi.py` untested |
| Server | `server/` — live on Supabase Pro, Zurich (Edge Function, Postgres, Storage, `pg_cron`); `docs/SERVER-CONCEPT.md`, ADR 0017/0018. Drive it with `tools/fakebox` | APNs key for push |
| iOS | `ios/` (SwiftUI, APNs) | server endpoints, Apple dev account |

## Working on the box

- The box is a Linux machine reachable as `ssh dadbox` over Tailscale (bench:
  UART on GPIO 14/15 via `tools/serial_capture.py`, or home Wi-Fi). Deploy is
  `rsync` + `systemctl restart dadbox`; logs are `journalctl -u dadbox`.
- Drive it with `dadboxctl` (`state`, `record start`, `play`, `checkin`, `led
  test`, `sim link down`) before asking the user to touch anything.
- The root filesystem is a read-only overlay. Only `/data` is writable. Every
  message write is fsync-then-rename. Never disable the overlay in the field.
- Same Python runs on the Mac: unit-test the logic here first.
- Claude can't hear, see LEDs, or read a meter: ask the user for exactly that
  observation, nothing more. See `docs/DEV-PROCESS.md`.

## Conventions

- **The protocol is the contract.** `docs/PROTOCOL.md` changes first, then the
  three code streams. Never let firmware and app drift into private agreements.
- Hardware or architecture choices that were not obvious get an ADR in
  `docs/decisions/`. Revise the ADR rather than quietly doing something else.
- Every bench session gets an entry at the top of `docs/BUILD-LOG.md`.
- Parts live in `hardware/bom/bom.csv` with a phase number, not scattered in prose.
  Swiss sources in `hardware/SOURCING.md`; how the parts were chosen in
  `hardware/EVALUATION.md`.
- The hardware in one breath (ADR 0014 as revised, ADR 0016): a 1590DD-size
  die-cast aluminium box (antenna outside, ~33 mm inside — measure the clone,
  round holes only); Pi Zero 2 W; Waveshare SIM7670G LTE Cat-1 HAT on USB;
  I2S mic + MAX98357A amp; two 16 mm RGB-lit buttons; 5 V micro-USB power. The
  first box is **mains only** — the battery (Waveshare UPS Module 3S) is
  deferred (ADR 0019), so pulling the plug is how it turns off. **Off-the-shelf parts only** — no 3D
  printing, no custom PCB.
- Several Claude sessions work in this folder. Stay in your stream's files,
  and commit your own changes separately.
- Never commit secrets. Wi-Fi/API credentials go in `.env` or a gitignored
  `secrets.h`. APNs `.p8` keys never enter this repo.

## Design rules that are not negotiable

- **The buttons' lights are the box's only lights, and they have one "not
  ready" state** ([ADR 0024](docs/decisions/0024-no-status-leds-record-says-ready.md)).
  They say waiting, recording, playing, got-it and, on Record, ready (steady
  dim blue) or not ready (slow blue blink). There are no status LEDs. Why the box is not
  ready (link, server, fault) is the app's to explain. A child never
  interprets a fault.
- **Nothing a child recorded is ever lost.** The got-it pulse comes only after
  fsync; the outbox is never evicted; deletion only on the server's 2xx to
  `complete`, which follows a durable write and CRC check.
- **The mic is powered only while recording, from the same pin that lights the
  record button red.** No red light, no mic power — by wiring, not by
  firmware. The box lives in rooms with other people in them.
- **The capture is on disk while the child is still talking.** Opus is made
  after recording stops; nothing is ever only in RAM.
- **Every consumer is power-gated.** Button LEDs, amp, mic — and, on battery, the
  modem between check-ins (ADR 0015). A Pi can't sleep, so gating is the whole budget.
- **The box travels in a bag.** Presses under 0.5 s are ignored and the travel
  lock (both buttons, 3 s) must keep working (ADR 0016).
- Quiet hours are enforced on the device, not by the sender's discipline.
- No transcription, no speech services, no third-party analytics, ever.
