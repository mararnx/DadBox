# DadBox

A hardware + software maker project.

> **Status:** scaffold only. The project brief still needs to be filled in —
> see [docs/BRIEF.md](docs/BRIEF.md).

## Layout

| Path | What lives here |
| --- | --- |
| `hardware/schematics` | Circuit schematics (KiCad, Fritzing, PDF exports) |
| `hardware/pcb` | PCB layouts and fabrication outputs (Gerbers, drill files) |
| `hardware/cad` | Enclosure / mechanical CAD (STEP, STL, F3D) |
| `hardware/bom` | Bills of materials, supplier links, cost tracking |
| `firmware` | Embedded code that runs on the device |
| `software` | Host-side code: app, CLI, web UI, services |
| `docs` | Brief, build log, wiring notes |
| `docs/decisions` | Decision records — one file per choice that was hard to make |
| `tools` | Scripts: flashing, test rigs, build helpers |
| `assets` | Photos, renders, datasheets |

## Getting started

Nothing to build yet. Fill in `docs/BRIEF.md` first — what the box does,
what it runs on, and how the hardware and software talk to each other.
Toolchain setup lands here once those are picked.
