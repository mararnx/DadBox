# DadBox

A voice messaging device for a parent and child who live apart. Open the lid,
talk, close it — the other person hears it. No screen, no phone, no account.

> **Status:** designed and reviewed, nothing built. Fourteen ADRs in `docs/decisions/`.
> Next action: find a Pi Zero 2 W, order phase 1, build `tools/fakebox`.

## Layout

| Path | What lives here |
| --- | --- |
| `hardware/schematics` | Circuit schematics (KiCad, Fritzing, PDF exports) |
| `hardware/pcb` | Only if a PCB ever happens — v1 is point-to-point on the Pi's 40-pin header |
| `hardware/cad` | Drill templates for the 1590DD lid and walls (PDF/DXF, 1:1) |
| `hardware/bom` | Bills of materials, supplier links, cost tracking |
| `box` | The box's Python service (Raspberry Pi Zero 2 W, Linux) |
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
- [docs/DEV-PROCESS.md](docs/DEV-PROCESS.md) — the build–flash–log loop, what Claude drives itself, what needs a human
- [docs/PROTOCOL.md](docs/PROTOCOL.md) — the contract all three code streams share
- [hardware/SHOPPING-LIST.md](hardware/SHOPPING-LIST.md) — phased; buy phase 1 only
- [hardware/SOURCING.md](hardware/SOURCING.md) — Swiss links and prices, ready to order
- [hardware/EVALUATION.md](hardware/EVALUATION.md) — the hardware options weighed against what Swiss shops stock

`server/` and `ios/` are not blocked by hardware. Build them against a fake box
so that when the parts arrive, the firmware is the only unknown.
