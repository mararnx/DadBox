# Audio playback

**Role.** Play the parent's voice loudly and clearly enough to be heard across
a child's bedroom, and play nothing in a school bag.

## Current design

- MAX98357A I2S amp, 3 W into a 4 Ω 40-50 mm full-range driver.
- Amp held in shutdown except while playing or chiming.
- Oldest unplayed message first; `played` reported on next sync.

## Checked

- MAX98357A's gain is set by a pin, not software. Volume control has to be done
  by scaling samples in firmware, which costs headroom. Fine for speech.
- Speaker in an enclosure with a mic 5 cm away: no echo problem (async), but a
  playing speaker must never coincide with a powered mic — the state machine
  already forbids it.
- The driver is not the bottleneck. Enclosure volume and port design are.
  Phase 1 should be listened to inside a cardboard mock-up, not on the bench.
- Playing a message aloud in a shared room is a feature and a liability — the
  other household hears every message. That is a placement and volume question
  for [controls-ui.md](controls-ui.md), not an audio one.

## Questions

1. **Volume** — fixed, a physical knob, app-set, or child-adjustable? Suggest:
   app-set with a night-time ceiling, no control on the box.
2. **Chime** — one chime on new-message arrival (outside quiet hours), none, or
   the parent's own voice saying the child's name? The last is lovely and
   free — it's just a message the parent records once.
3. **Replay** — can the child replay a message after it's played? How many
   times, for how long? Ties to retention.
4. **Skip / next** — with three messages waiting, does play run through all of
   them, or one per press? Suggest one per press, ring shows the remainder.
5. **Interrupt** — pressing play during playback: stop, or ignore?
6. **Headphones** — no. But say so, because someone will ask.
