# ADR 0005 — Battery, and how to be responsible about it

**Date:** 2026-09-20
**Status:** accepted

## Context

The box travels with the child. It will be in a bag, in a car, and unplugged
for hours at a time. Mains-only is no longer an option, so the earlier concern
about putting a lithium cell in a child's bedroom has to be answered rather
than avoided.

## Decision

Internal LiPo with USB-C charging, chosen and built for abuse:

- **Protected cell** with an integrated PCM — over-charge, over-discharge and
  short-circuit protection at the cell, not just in the charger IC.
- **Power-path charging** so the box works while plugged in with a flat battery.
- The cell is mechanically captive and cannot be reached without tools. No
  removable battery door, no coin cells anywhere in the design.
- Charge current conservative, and no charging outside 0-45°C.
- Bulk capacitance near the modem so transmit bursts don't brown out the rail.

## Alternatives considered

- **Mains-only** — safest and simplest, but incompatible with travel.
- **Off-the-shelf USB power bank inside the enclosure** — pre-certified and
  genuinely safer, at the cost of bulk and an awkward charge/discharge dance.
  Worth reconsidering if the custom power path proves troublesome.

## Consequences

- Battery state of charge is now something the parent app must show. A box that
  dies in a bag is the silent-failure mode this project cares most about.
- Enclosure must manage heat and hold the cell rigidly.
- Charging becomes a habit someone has to own — the app should say so before
  it's a problem, not after.
