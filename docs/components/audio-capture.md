# Audio capture

**Role.** Turn a child's voice into a file on disk, only while they mean to be
recording, and never otherwise.

## Current design

> **Platform change 2026-09-20 — [ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md).**

- I2S MEMS mic (MSM261S4030H0 / ICS-43434) on the Pi's I2S via the
  `googlevoicehat-soundcard` overlay (BCLK 18, LRCLK 19, data 20).
- Mic VDD behind the lid's reed contact, so "not recording" is an unpowered
  microphone, not a software promise ([ADR 0007](../decisions/0007-lid-gesture.md)).
- Lid opens → `arecord`/ALSA at 16 kHz mono 16-bit → written to `/data`
  **as it happens**. Lid closes → stop, trim, encode ([codec.md](codec.md)).
- Ring steady "listening" the whole time the mic is powered; no timer shown.
- Cap 5 minutes; under ~1 s of speech after trimming → discarded.

## Checked

- The Voice HAT overlay is exactly this mic + the MAX98357A; both directions
  on one I2S. Amp SD-mode must be wired to GPIO 16 or playback stays silent.
- The mic has no enable pin; gating is on VDD. It settles in tens of ms —
  discard the first ~100 ms so the message doesn't open with a click.
- Placement matters more than the mic: a port near the speaker or behind
  thick aluminium loses more than any mic choice gains. Mic faces up under
  the lid, exposed when open — which is the gesture.
- A child talks at the box from 20–60 cm at wildly varying levels: normalise
  after capture (`ffmpeg loudnorm` or a simple peak/RMS pass).
- Nothing is ever only in RAM: a power loss mid-story costs the last buffer.

## Questions

1. **Start/stop chimes** — a chime on lid-open makes "am I recording"
   unambiguous, but lands on the recording unless the first 200 ms are cut.
2. **Open-and-silent** — trims to nothing, sends nothing, no feedback. Right?
3. **Ambient noise** — none in v1; evaluate on real recordings from the box.
4. **Gain / normalisation** — post-capture only; which method, by ear.
