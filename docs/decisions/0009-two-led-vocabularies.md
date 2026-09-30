# ADR 0009 — Two LED vocabularies: the ring is the child's, status LEDs are the adults'

**Date:** 2026-09-20
**Status:** superseded by [ADR 0024](0024-no-status-leds-record-says-ready.md) — no status LEDs; Record shows ready / not ready. Earlier revised by [ADR 0016](0016-two-buttons-no-lid.md): the child's channel is now the two buttons' lights, not a ring. Read "the ring" below as "the button lights"; the rule (no error state on the child's channel) is unchanged

## Context

The original state table said *no connection → nothing visible*. That kept the
child from ever interpreting a fault, but it also meant a box that had been
offline for three days looked identical to one with nothing to say — in both
houses, to everyone. Silence reads as "Dad stopped messaging".

The obvious fix — put a link state on the ring — would give the ring a fourth
word, and the ring's whole value is that a six-year-old never has to read it.

## Decision

Two separate channels, physically separate, with separate audiences.

- **The ring** speaks only to the child: *waiting*, *listening*, *playing*,
  and one pulse for *got it*. It never shows link, battery or faults. It has
  no error state.
- **Two small discrete LEDs** — LINK and POWER, low on the box beside the
  USB-C port — speak to whichever adult is in the room. Off means fine.
  Patterns, not colours, carry the meaning. A combined alternating pattern is
  the one fault signal, reserved for things an adult must act on.

The full logic and priority order is in [ARCHITECTURE.md](../ARCHITECTURE.md#indication).

## Alternatives considered

- **Link state on the ring** (e.g. a slow dim pulse for "sleeping") — rejected:
  a fourth word for the child, and ambiguous against "waiting".
- **Nothing, ever, on the box** — the previous decision. Rejected for the
  reason above: the silence has an emotional cost, and the co-parent, who is
  on board, has no way to help.
- **App-only** — correct but insufficient: the app is in the other house.

## Consequences

- Two more GPIOs, two LEDs, two resistors. Negligible cost and power (10 ms
  blinks at low brightness).
- The "sleeping" ring state is removed.
- "The box has no error state" becomes "the *ring* has no error state".
- The co-parent can glance and know whether the thing is alive, without an
  app and without asking the child.
