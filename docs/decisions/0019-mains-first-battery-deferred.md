# ADR 0019 — Mains first; the battery is deferred

**Date:** 2026-09-21
**Status:** accepted (user decision) — suspends the weekend-unplugged target of
[ADR 0005](0005-battery-required.md) until a battery is fitted

## Context

The box will be plugged in nearly all the time. The battery option found for
it — a Waveshare UPS Module 3S, three 18650s in series, 93 × 86 mm, charged
from its own 12.6 V barrel-jack supply — is half the floor of the enclosure,
a second charger for the other house, and about two days of runtime on a
Pi that cannot sleep. None of that helps get a first box working.

## Decision

- **The first box has no battery.** It runs from a 5 V micro-USB supply and
  is on only while plugged in. Unplugged means off; plugged in means it boots
  (~25 s) and carries on.
- **The design keeps the battery's place:** the left half of the enclosure
  floor stays free (93 × 86 mm), telemetry keeps `battery_pct`, `charging` and
  `mains`, and [ADR 0015](0015-adaptive-polling.md)'s battery cadences stay in
  the code. Without a battery the box reports `mains: true`,
  `battery_pct: null`, and always polls every minute with the modem on.
- The UPS Module 3S, three cells, the second 12.6 V charger and the DC panel
  jack leave the shopping list until the user asks for them.

## Consequences

- **Nothing is lost still holds**, and matters more: pulling the plug is now
  the normal way the box turns off. The capture is on disk while the child
  talks, every message write is fsync-then-rename, and the root filesystem is
  read-only — all of which were already rules. To verify on the bench: pull
  the plug mid-recording and mid-upload, repeatedly.
- A recording interrupted by a power cut is recovered at boot: what is on disk
  is trimmed, encoded and queued as if stop had been pressed.
- The POWER status LED is steady while external power is present on the USB
  port and off otherwise (user decision 2026-09-22; ARCHITECTURE.md § Status LEDs).
- The box cannot go to a grandparent's for a weekend without a socket — which
  is what ADR 0005 was for. That is accepted for now.
- The app's "quiet vs dead" question gets simpler and blunter: a box that has
  not checked in is unplugged, out of coverage, or broken.
- The charge-port question collapses to a 5 V inlet: a USB-C panel adapter
  with a short USB-C → micro-USB cable inside, or the supply's cable through a
  grommeted hole.
