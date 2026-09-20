# ADR 0008 — Two parents in the protocol, one in the build

**Date:** 2026-09-20
**Status:** accepted

## Context

The child alternates homes. When they are with one parent, the box is in that
parent's house — and the natural thing is for the child to message the parent
they are *away* from. The co-parent is on board. Building that now doubles the
identity and routing work before anything exists.

## Decision

The protocol carries two parent identities and a `to` field on every message
from day one. The first build implements one parent. Nothing in the firmware
or server assumes there will only ever be one.

- Identities: `box`, `parent-a`, `parent-b`. `parent-b` is reserved and
  unused in v1.
- Every message has `from` and `to`. In v1 the box always sends to
  `parent-a`; the server enforces that.
- Telemetry carries a `house` field (`unknown | a | b`), reserved for a dock
  that identifies itself with a resistor. Unused in v1.

## Alternatives considered

- **One parent, ever** — simplest, and would have to be torn up the day the
  co-parent asks.
- **Both now** — right eventually; premature before the box makes a sound.

## Consequences

- No extra work in v1 beyond a field and an enum.
- Adding the second parent later is: a second app identity, a second push
  token, the dock ID, and a routing rule. No firmware change to the audio
  path, no protocol change.
- The child-facing UI never asks "who is this for". Routing is the box's
  problem, and later the dock's.
