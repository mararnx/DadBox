# Audio capture

**Role.** Turn a child's voice into a file on disk, only while they mean to be
recording, and never otherwise.

## Current design

- DFRobot I2S MEMS mic (MSM261S4030H0, 3.3 V, ~1 mA) on the Pi's I2S via the
  `googlevoicehat-soundcard` overlay (BCLK 18, LRCLK 19, data in 20), sharing
  the bus with the amp ([audio-playback.md](audio-playback.md)).
- **Mic VDD is the same GPIO pin as the record button's red LED**
  ([ADR 0016](../decisions/0016-two-buttons-no-lid.md)). No red light → the
  mic has no power. A wiring fact, not a software promise.
- Record pressed (≥ 0.5 s) → pin high → ALSA at 16 kHz mono 16-bit → written
  to `/data` **as it happens**. Second press, the 5-minute cap, or ~20 s of
  continuous silence → stop, pin low, trim, encode ([codec.md](codec.md)).
- The button is steady red the whole time the mic is powered; no timer shown.
- Under ~1 s of speech after trimming → discarded silently: nothing queued,
  no *got it*.
- Never while playing — the state machine forbids a powered mic and a live
  amp at the same time.

## Checked

- The Voice HAT overlay is exactly this pairing — an I2S mic plus the
  MAX98357A, both directions on one bus. Do not also load `max98357a`. Amp
  SD_MODE must be wired to GPIO 16 or playback stays silent.
- The mic has no enable pin; gating is on VDD. It settles in tens of ms —
  discard the first ~100 ms so the message doesn't open with a click.
- Placement matters more than the mic: a port near the speaker or behind
  thick aluminium loses more than any mic choice gains
  ([enclosure.md](enclosure.md) Q5).
- A child talks at the box from 20–60 cm at wildly varying levels: normalise
  after capture (`ffmpeg loudnorm` or a simple peak/RMS pass).
- Nothing is ever only in RAM: a power loss mid-story costs the last buffer.

## Questions

1. **Is a GPIO pin a clean enough mic supply?** It also feeds an LED. Listen
   for hum or hash on the first recordings; an RC filter on the mic side if
   needed.
2. **Does the mic stay unpowered while the amp plays?** BCLK and LRCLK are
   shared and run during playback; verify with a meter on the mic's VDD that
   they don't back-feed it. The privacy rule rests on this.
3. **Silence auto-stop** — ~20 s and what level? A child thinking is not a
   child who has finished. Tune on real recordings.
4. **Start chime** — makes "am I recording" unambiguous, but the amp and the
   mic are never on together, so it would have to finish before the pin goes
   high. The red light may be enough.
5. **Ambient noise** — none in v1; evaluate on real recordings from the box.
6. **Gain / normalisation** — post-capture only; which method, by ear.
