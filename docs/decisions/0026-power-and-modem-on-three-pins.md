# ADR 0026 — 5 V in on the header; the modem HAT on three pins

**Date:** 2026-10-02
**Status:** proposed — confirm with the inlet part in hand and the first boot
on header power. Revises the pin-for-pin join in
[ADR 0023](0023-enclosure-layout.md) and the micro-USB power in
[ADR 0014](0014-raspberry-pi-zero-2w.md).

## Context

- The HAT sits under the Zero (ADR 0023). From its schematic it needs only
  three of the 40 pins: **5 V**, **ground** and **P4** (pin 7, its power key
  through DIP switch 3). Joining all 40 also joins pins 8/10 (the modem's
  UART, behind DIP 1/2) and every pin the leads on top use — a wrong DIP
  setting or a short below would reach the buttons and the console.
- The pins joining the boards are soldered in from below. Pins on the
  **even row, the board's edge**, are the ones a soldering iron reaches.
- Power through the micro-USB "PWR IN" needs the inlet's tail to end in a
  micro-USB plug, an angled one since the ports face the speaker (ADR 0023),
  and a plug can work loose in a bag.

## Decision

- **Three header pins join the Zero to the HAT**, soldered in from below,
  no others:

  | Pin | Signal | Row | Why this pin |
  | --: | --- | --- | --- |
  | 4 | 5 V | even, edge | the HAT has 5 V on 2 and 4; pin 2 stays the amp's |
  | 6 | GND | even, edge | the ground next to it: 5 V and ground side by side |
  | 7 | GPIO 4 → HAT P4 (power key) | odd, inner | **fixed by the HAT**: DIP 3 routes PWR only to P4. The one inner pin |

- **5 V comes in on the same two pins**: the inlet's red lead on the top of
  pin 4, its black lead on the top of pin 6 — one lead per pin, as everywhere.
  The modem then takes its current straight off the joined pin; only the
  Zero's and the amp's share crosses the Zero's 5 V rail.
- The micro-USB "PWR IN" stays empty for good.

## Consequences

- **No protection on this path.** The header has nothing against reversed
  wires or more than ~5.25 V: one wrong lead destroys the Zero and the HAT.
  Check polarity with a meter before the first plug-in; red and black only.
- **Never two supplies at once:** nothing in PWR IN while the header is fed.
- One ground pin carries all the return current. The supply is limited to
  2.5 A, inside what a header pin carries (~3 A); the inlet leads are
  0.5 mm² (AWG 20) at least, soldered, not crimped.
- The modem's UART (pins 8/10) is no longer joined at all, so DIP 1/2 can no
  longer collide with the debug probe; the debug probe stays on 8, 10, 14.
- **The inlet changes (Shopping stream):** the USB-C socket's tail must end
  in two wires, and something on it must carry the CC resistors (5.1 kΩ) or
  a USB-C supply will not switch 5 V on. The Delock 65927 micro-USB adapter
  drops out. Test whatever is chosen straight on the USB-C supply, both ways
  up, with a meter on the wires, before soldering it to the Zero.
- Pins 2 (amp) and 4 (inlet) are both 5 V; the amp keeps pin 2.
