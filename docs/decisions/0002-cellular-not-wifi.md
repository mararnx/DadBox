# ADR 0002 — Cellular, not Wi-Fi

**Date:** 2026-09-20
**Status:** accepted — module choice superseded by [ADR 0006](0006-bare-modem-not-notecard.md)

## Context

The box travels with the child between two homes. That is the deciding fact.

An earlier version of this ADR argued cellular because it avoids depending on
the other household's Wi-Fi password and goodwill. That reasoning was weak: the
co-parent is on board, so a password was never the obstacle, and cellular does
nothing about the larger question of whether a microphone is welcome in
someone's home — that is settled by conversation, not by radio.

The real argument is movement. A device that changes network every few days
must either be provisioned for two networks and handle roaming between them, or
carry its own. Two networks means two sets of credentials, two failure modes,
and a box that can silently go quiet in whichever house nobody is checking.

## Decision

Cellular. The box has one network and it comes with it.

> The original choice of a Blues Notecard as the module was reversed the same
> day — see ADR 0006. The *cellular* decision stands.

The Notecard's data plan is bundled with the hardware, so there is no monthly
bill, no carrier account, and no SIM to activate or let lapse.

## Alternatives considered

- **Dual Wi-Fi credentials** — free, and plausible now that both households
  cooperate. Rejected: two networks is two things that break, in two places,
  and the box would need re-provisioning after any router change in either home.
- **Bare LTE-M modem + data SIM** — cheaper hardware, but AT-command plumbing
  and a billing account that can lapse. Wrong trade for one unit.

## Consequences

- Works identically in both homes, in the car, at a grandparent's.
- Transmit bursts need a healthy cell and good decoupling — see
  [ADR 0005](0005-battery-required.md).
- Data is metered, though voice is small enough that this isn't a real limit.
- **Coverage must be checked at both addresses before ordering.**
