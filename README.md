# DadBox

A voice messaging device for a parent and child who live apart. Open the lid,
talk, close it — the other person hears it. No screen, no phone, no account.

> **Status:** designed and reviewed, nothing built. Eight ADRs in `docs/decisions/`.
> Next action: check Sunrise 4G in both bedrooms, order phase 1, build
> `tools/fakebox`.

## Layout

| Path | What lives here |
| --- | --- |
| `hardware/schematics` | Circuit schematics (KiCad, Fritzing, PDF exports) |
| `hardware/pcb` | Only if a PCB ever happens — v1 is point-to-point on the LILYGO's headers |
| `hardware/cad` | Drill templates for the 1590DD lid and walls (PDF/DXF, 1:1) |
| `hardware/bom` | Bills of materials, supplier links, cost tracking |
| `firmware` | ESP32 firmware (ESP-IDF) for the LILYGO T-A7670G R2 |
| `server` | Backend: blob storage, APNs push, device telemetry |
| `ios` | Parent's native iOS app (SwiftUI) |
| `docs` | Brief, architecture, protocol, roadmap, build log |
| `docs/decisions` | Decision records — one file per choice that was hard to make |
| `tools` | Scripts: flashing, test rigs, build helpers |
| `assets` | Photos, renders, datasheets |

## Start here

- [docs/BRIEF.md](docs/BRIEF.md) — what it is and why
- [docs/REVIEW.md](docs/REVIEW.md) — architecture double-check: what holds, what doesn't
- [docs/components/](docs/components/README.md) — one file per component, with the open questions
- [docs/ROADMAP.md](docs/ROADMAP.md) — the four streams and what blocks what
- [docs/PROTOCOL.md](docs/PROTOCOL.md) — the contract all three code streams share
- [hardware/SHOPPING-LIST.md](hardware/SHOPPING-LIST.md) — phased; buy phase 1 only
- [hardware/SOURCING.md](hardware/SOURCING.md) — Swiss links and prices, ready to order
- [hardware/DOUBLE-CHECK.md](hardware/DOUBLE-CHECK.md) — every part checked against the 1590DD

`server/` and `ios/` are not blocked by hardware. Build them against a fake box
so that when the parts arrive, the firmware is the only unknown.
