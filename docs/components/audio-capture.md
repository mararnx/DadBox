# Audio capture

**Role.** Turn a child's voice into PCM in memory, only while they mean to be
recording, and never otherwise.

## Current design

- ICS-43434 I2S MEMS mic → ESP32-S3 I2S RX → 16 kHz mono 16-bit PCM in PSRAM.
- Mic VDD behind a load switch driven by the record control, so "not recording"
  is an unpowered microphone, not a software promise.
- Ring lit the whole time the mic is powered.

## Checked

- **Buffer math was wrong** — see [review §2](../REVIEW.md). 5 min does not fit
  in 8 MB PSRAM as raw PCM. Fix follows the gesture decision.
- ICS-43434 has no enable pin; gating has to be on VDD. Its start-up time after
  power is tens of ms — the first ~100 ms after the gesture should be discarded
  so the message doesn't open with a click.
- Mic placement matters more than mic choice: a port near the speaker, or
  behind thick plastic, will lose more than the ICS-43434 gains over an INMP441.
- A child talks *at* the box from 20-60 cm, at a wide range of levels. Some
  automatic gain will be needed; done post-capture, it costs nothing.

## Questions

1. **Gesture** — hold, toggle, or lid? (Decides cap, buffer, gating, enclosure.)
2. **Cap** — 90 s hold, or 5 min lid/toggle? Is there a *minimum*? A 0.4 s
   accidental press should probably be discarded, not sent.
3. **Start/stop feedback** — a chime on start and on send, or silent? A chime
   on start makes "am I recording" unambiguous for the child, but ends up on
   the recording unless the first 200 ms are trimmed.
4. **Pre-roll** — should the box capture the ~300 ms before the gesture
   registers so the first word isn't clipped? Only possible if the mic is
   already powered, which contradicts hard gating. Likely answer: no, and
   accept a short lead-in.
5. **Silence handling** — if the child opens the lid and says nothing for 30 s,
   send it, or drop it? Suggest: trim leading/trailing silence, and drop
   anything under ~1 s of speech.
6. **Ambient** — any noise reduction, or trust the mic? Suggest none in v1;
   evaluate on real recordings from the enclosure before adding DSP.
7. **What the LED does during capture** — fill toward the cap, or a steady
   "listening" state with no time pressure? For a lid with a 5-min cap, time
   pressure is probably unwanted.
