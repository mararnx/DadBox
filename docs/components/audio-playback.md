# Audio playback

**Role.** Play the parent's voice loudly and clearly enough to be heard across
a child's bedroom, and play nothing in a school bag.

## Current design

- MAX98357A I2S class-D amp into a Seeed 5 W 4 Ω speaker in its own plastic
  enclosure (50 × 45 × 22 mm), on the same I2S bus and
  `googlevoicehat-soundcard` overlay as the mic
  ([audio-capture.md](audio-capture.md)).
- Amp held in shutdown (SD_MODE on GPIO 16) except while playing or chiming.
- **Play** plays the oldest unheard message, one per press; the button is
  steady warm while it plays and goes back to breathing if more are waiting.
  With nothing new waiting it repeats the last message heard, which the box
  keeps on disk for that purpose (ADR 0020).
  `played` is reported at the next check-in, and playing opens the
  conversation window ([ADR 0015](../decisions/0015-adaptive-polling.md)).
- One gentle chime when a message arrives — suppressed by quiet hours. Play
  still works during quiet hours. There is no mute (ADR 0020).
- Volume is the `volume` setting from the app, applied in software. No
  control on the box.
- In a bag: the ≥ 0.5 s press and the travel lock
  ([controls-ui.md](controls-ui.md)) are what stop a message playing aloud in
  a classroom.

## Checked

- MAX98357A's gain is set by a pin, not software. Volume is done by scaling
  samples, which costs headroom. Fine for speech.
- Speaker in an enclosure with a mic a few cm away: no echo problem (async),
  but a playing speaker must never coincide with a powered mic — the state
  machine already forbids it.
- The driver is not the bottleneck. The grille and how the speaker sits
  against the aluminium are ([enclosure.md](enclosure.md) Q4). Listen inside
  a cardboard mock-up, not on the bench.
- Playing a message aloud in a shared room is a feature and a liability — the
  other household hears every message. That is a placement and volume question
  for [controls-ui.md](controls-ui.md), not an audio one.

## Questions

1. **Volume at night** — should the app-set volume have a quiet-hours
   ceiling, enforced on the device?
2. **Chime** — the stock chime, or the parent's own voice saying the child's
   name? The last is lovely and free — it's just a message the parent records
   once.
3. ~~Replay~~ — decided 2026-09-22 (ADR 0020): the last played message stays
   on the box and Play repeats it when nothing new is waiting. Older ones are
   the app's archive.
4. **Interrupt** — pressing Play during playback: stop, restart, or ignore?
   And Record during playback?
5. **Headphones** — no. But say so, because someone will ask.
