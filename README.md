# DadBox

A voice messaging device for a parent and child who live apart. Press a button,
talk, let go — the other person hears it. No screen, no phone, no account.

> **Status:** designed, nothing built. Decisions recorded in `docs/decisions/`.
> Next action: check cellular coverage at both addresses, then order phase 1.

## Layout

| Path | What lives here |
| --- | --- |
| `hardware/schematics` | Circuit schematics (KiCad, Fritzing, PDF exports) |
| `hardware/pcb` | PCB layouts and fabrication outputs (Gerbers, drill files) |
| `hardware/cad` | Enclosure / mechanical CAD (STEP, STL, F3D) |
| `hardware/bom` | Bills of materials, supplier links, cost tracking |
| `firmware` | ESP32-S3 firmware (ESP-IDF) |
| `server` | Backend: blob storage, APNs push, device telemetry |
| `ios` | Parent's native iOS app (SwiftUI) |
| `docs` | Brief, architecture, protocol, roadmap, build log |
| `docs/decisions` | Decision records — one file per choice that was hard to make |
| `tools` | Scripts: flashing, test rigs, build helpers |
| `assets` | Photos, renders, datasheets |

## Start here

- [docs/BRIEF.md](docs/BRIEF.md) — what it is and why
- [docs/ROADMAP.md](docs/ROADMAP.md) — the four streams and what blocks what
- [docs/PROTOCOL.md](docs/PROTOCOL.md) — the contract all three code streams share
- [hardware/SHOPPING-LIST.md](hardware/SHOPPING-LIST.md) — phased; buy phase 1 only

`server/` and `ios/` are not blocked by hardware. Build them against a fake box
so that when the parts arrive, the firmware is the only unknown.
