# ADR 0012 — One board: LILYGO T-SIM7080G-S3

**Date:** 2026-09-20
**Status:** superseded by [ADR 0013](0013-cat1-not-catm.md) — the user's SIM provider does not support Cat-M; board is now the T-A7670G R2 (Cat-1)

## Context

The plan was an ESP32-S3-DevKitC-1 plus a SIM7080G breakout (with level
shifting for its 1.8 V UART) plus a BQ24074 charger plus wiring between them.
Sourcing turned up a Swiss-stocked board that already is all of that.

## Decision

The **LILYGO T-SIM7080G-S3** (CHF 43.90, bastelgarage.ch): ESP32-S3 with
16 MB flash / 8 MB PSRAM, SIM7080G on UART (TX 4, RX 5, PWRKEY 46, DTR 7,
RI 6), USB-C charging at up to 500 mA, an 18650 holder **and** a JST 2.0
battery connector, a TF-card slot (GPIO 10–13), a nano-SIM slot, and an IPEX
LTE antenna in the box. 110 × 32 × 19.5 mm.

ADR 0006 is unchanged in substance: it is still a bare SIM7080G driven by
`esp_modem` over PPP, with our own server and nobody in between. What changes
is that the modem, its power and its level shifting are someone else's
finished board.

## Alternatives considered

- **DevKitC + breakouts** — the previous plan. More parts, more wiring, a
  1.8 V trap, and ~the same money.
- **Notecard** — still the fallback if PPP fights back; see ADR 0006.

## Consequences

- Phase 1 buys one board instead of one board plus three modules, and the
  audio proof runs on the final MCU.
- Two variants exist — with an AXP2101 PMU and a "Standard" without. **Confirm
  which one Bastelgarage ships.** PMU gives software control of rails and a
  real fuel gauge; Standard needs an ADC divider for battery %.
- The 18650 spring holder is not trusted in a bag: a protected cell with
  JST-PH 2.0 leads plugs into the JST and is strapped down
  ([ADR 0005](0005-battery-required.md)).
- 500 mA charge current → ~7 h from flat for 3000 mAh. Overnight, not lunch.
- The TF slot gives the never-lost outbox effectively unlimited headroom if
  it is ever needed ([ADR 0010](0010-nothing-is-lost.md)). Internal flash
  stays primary.
- Pin assignments in `firmware/main/dadbox_config.h` move to this board's map.
