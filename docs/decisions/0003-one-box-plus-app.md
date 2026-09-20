# ADR 0003 — One box, parent uses a phone

**Date:** 2026-09-20
**Status:** accepted — parent-end platform amended by [ADR 0004](0004-native-ios-app.md)

## Context

> **Amendment:** the parent end is a native iOS app, not a PWA. See
> [ADR 0004](0004-native-ios-app.md). Everything else below stands.

The child needs a physical object: a phone is not theirs, not always available,
and not the point. The parent already carries a device that records audio
perfectly well.

## Decision

Build one box for the child. The parent records and listens in a phone web app
(PWA — no app store, no install friction, works on either platform).

The wire protocol is designed as if both ends were boxes. The app is a client
that happens to be software, not a special case baked into the firmware.

## Alternatives considered

- **Two matching boxes** — emotionally the better answer, and still the likely
  endgame. But it doubles the build before anything has been proven to work,
  and the second box would be installed in the household where iterating is
  hardest.

## Consequences

- Half the hardware; M2 arrives much sooner.
- A second box can be added later without touching the protocol or the child's
  firmware. It joins as another client.
- Asymmetry to watch: the parent can send from anywhere at any time, and a
  child getting a message at 11pm is a design problem. Quiet hours belong in
  the box, not in the parent's discipline.
