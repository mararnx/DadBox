# ADR 0007 — Open the lid to talk, close it to send

**Date:** 2026-09-20
**Status:** superseded by [ADR 0016](0016-two-buttons-no-lid.md) (2026-09-21) — two lit buttons, no lid. The bag problem and the mic guarantee described here are carried into 0016's consequences

## Context

Three earlier choices were mutually incompatible: hold-to-talk, a five-minute
cap, and "the mic is powered only while the button is physically held". No
child holds a button for three minutes of story. Separately, two large arcade
buttons on the outside of a box that lives in a school bag would record the
bag and play messages aloud in a classroom.

## Decision

The box has a lid.

- **Open** → a lid switch powers the microphone through a load switch (a
  physical guarantee, not a firmware one), the ring lights "listening", and
  the box records for up to five minutes with no time pressure shown.
- **Close** → recording stops, silence is trimmed, the message is encoded,
  queued and sent. One pulse on the ring.
- A single recessed **play** button lives on the outside, so listening
  doesn't require opening. Nothing else is on the outside but the ring.
- A closed box is transport-safe: nothing a bag can press.

Opening a lid is unmistakable to everyone in the room. That matters in a home
that isn't the sender's.

## Alternatives considered

- **Hold-to-talk, 90 s cap** — simplest hardware, raw PCM fits PSRAM,
  physical gating via the button. Rejected: long stories become two messages,
  and the bag problem still needs solving separately.
- **Press to start / press to stop** — five-minute cap, but the mic gate
  becomes a software promise, and the bag problem remains.
- **Latching arcade button** — a lid without the box. Loses the "obvious to
  the room" property.

## Consequences

- The enclosure gains a hinge and a switch. Pin hinge with a detent, or a
  magnetic lid with a hall sensor; either must be *reliable* before it is
  clever. A living hinge will not survive.
- Capture is now up to five minutes, which does not fit PSRAM as raw PCM. The
  capture path encodes IMA-ADPCM as it goes (4:1, trivially cheap, no
  real-time constraint worth the name) — 2.4 MB for the full cap. The rule
  "no encoding during capture" is restated as **no real-time-constrained
  codec in the capture path**. Optional transcode to Opus after the lid
  closes is an M3 upgrade that changes nothing else.
- Open-and-silent (a child opens it and says nothing): trim to nothing, send
  nothing, no feedback. Under ~1 s of speech: discarded.
- One arcade button leaves the BOM; a lid switch and a load switch join it.
