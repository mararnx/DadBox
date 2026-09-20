# DadBox

A voice messaging device for a parent and child who live apart. The child has a
box with a lid and one button; the parent has an iPhone. Read
[docs/BRIEF.md](docs/BRIEF.md) and [docs/REVIEW.md](docs/REVIEW.md) before
making assumptions about the design.

## Streams

| Stream | Where | Blocked by |
| --- | --- | --- |
| Shopping | `hardware/SHOPPING-LIST.md` | phase 2: Sunrise 4G check in both bedrooms |
| Firmware | `firmware/` (ESP-IDF + esp_modem, LILYGO T-A7670G R2, classic ESP32) | phase 1 parts |
| Server | `server/` (Node + TS + Fastify) | nothing |
| iOS | `ios/` (SwiftUI, APNs) | server endpoints, Apple dev account |

## Working on the firmware

- Every firmware Bash command starts with `. ~/esp/esp-idf/export.sh`.
- Read the board with `tools/serial_capture.py` (returns), never `idf.py
  monitor` (doesn't). Drive it through the serial console (`state`, `lid
  open`, `play`, `at …`) before asking the user to touch anything.
- Logic goes in pure C so it compiles on the Mac; test it there first.
- Claude can't hear, see LEDs, or read a meter: ask the user for exactly that
  observation, nothing more. See `docs/DEV-PROCESS.md`.

## Conventions

- **The protocol is the contract.** `docs/PROTOCOL.md` changes first, then the
  three code streams. Never let firmware and app drift into private agreements.
- Hardware or architecture choices that were not obvious get an ADR in
  `docs/decisions/`. Revise the ADR rather than quietly doing something else.
- Every bench session gets an entry at the top of `docs/BUILD-LOG.md`.
- Parts live in `hardware/bom/bom.csv` with a phase number, not scattered in prose.
  Swiss sources and prices in `hardware/SOURCING.md`; the enclosure is a Hammond
  1590DD (aluminium — antenna outside, 32 mm inside, round holes only).
- Never commit secrets. Wi-Fi/API credentials go in `.env` or a gitignored
  `secrets.h`. APNs `.p8` keys never enter this repo.

## Design rules that are not negotiable

- **The ring has no error state.** It speaks only to the child: waiting,
  listening, playing, got-it. Link, battery and faults live on two small status
  LEDs — the adults' channel — and in the app. A child never interprets a fault.
- **Nothing a child recorded is ever lost.** The got-it pulse comes only after
  fsync; the outbox is never evicted; deletion only on the server's 2xx to
  `complete`, which follows a durable write and CRC check.
- **The mic is powered only while the lid is open**, through a switch, with the
  ring lit. The box lives in rooms with other people in them.
- **No real-time-constrained codec in the capture path.** ADPCM as it goes is
  fine; Opus happens after the lid closes, in the background.
- **Every consumer is power-gated.** Ring, amp, mic, modem. The target is a
  weekend unplugged and ungated LEDs alone would eat it.
- Quiet hours are enforced on the device, not by the sender's discipline.
- No transcription, no speech services, no third-party analytics, ever.
