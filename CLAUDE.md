# DadBox

A voice messaging device for a parent and child who live apart. The child has a
box with two buttons; the parent has an iPhone. Read [docs/BRIEF.md](docs/BRIEF.md)
before making assumptions about the design.

## Streams

| Stream | Where | Blocked by |
| --- | --- | --- |
| Shopping | `hardware/SHOPPING-LIST.md` | cellular coverage check |
| Firmware | `firmware/` (ESP-IDF, ESP32-S3) | phase 1 parts |
| Server | `server/` (Node + TS + Fastify) | nothing |
| iOS | `ios/` (SwiftUI, APNs) | server endpoints, Apple dev account |

## Conventions

- **The protocol is the contract.** `docs/PROTOCOL.md` changes first, then the
  three code streams. Never let firmware and app drift into private agreements.
- Hardware or architecture choices that were not obvious get an ADR in
  `docs/decisions/`. Revise the ADR rather than quietly doing something else.
- Every bench session gets an entry at the top of `docs/BUILD-LOG.md`.
- Parts live in `hardware/bom/bom.csv` with a phase number, not scattered in prose.
- Never commit secrets. Wi-Fi/API credentials go in `.env` or a gitignored
  `secrets.h`. APNs `.p8` keys never enter this repo.

## Design rules that are not negotiable

- **The box has no error state.** Network trouble queues silently and retries.
  Every failure surfaces in the parent's app instead — a child must never have
  to interpret a fault.
- **The mic is powered only while the button is physically held**, with the ring
  lit. The box lives in rooms with other people in them.
- **Encode after the button is released, never during capture.** There is no
  real-time constraint on a voice message.
- Quiet hours are enforced on the device, not by the sender's discipline.
- No transcription, no speech services, no third-party analytics, ever.
