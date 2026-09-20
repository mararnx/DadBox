# Codec

**Role.** Make a voice message small enough for cellular, without ever putting
a real-time constraint on the firmware.

## Current design

- Opus, 16 kHz mono, ~16 kbps. ~120 KB per minute.
- Encoded after the gesture ends, from the capture buffer, in a background task.
- Fallback: IMA-ADPCM (4:1, ~480 KB/min) if Opus proves painful on the S3.

## Checked

- The rule should be **no real-time-constrained codec in the capture path**.
  ADPCM in the capture path is fine — it is cheaper than the I2S DMA copy. This
  reopens the 5-minute cap (see [audio-capture.md](audio-capture.md)).
- libopus on a 240 MHz ESP32-S3 at 16 kHz, complexity ≤ 3, should encode
  faster than real time, but that is belief not measurement. ESP-ADF ships an
  Opus encoder component. **Measure before committing** — a 5-minute message
  that takes 4 minutes to encode is fine; one that fails to allocate is not.
- Data budget: at 16 kbps, 500 MB is ~70 hours of audio. At ADPCM's 64 kbps it
  is ~17 hours. Both are years of use for one family, so the codec choice is
  about *comfort*, not necessity.
- The iOS side decodes Opus natively (AVFoundation handles it in a CAF/Ogg
  container). ADPCM would need a small decoder in the app.

## Questions

1. **Opus, or ADPCM and be done?** ADPCM: zero integration risk, four times the
   data, needs a decoder in the app. Opus: better sound at a tenth the size,
   one unverified dependency. Suggest: ADPCM for M0/M1, Opus as an M3
   upgrade that changes nothing else — the container header carries the codec id.
2. **Two-stage?** Capture as ADPCM, then transcode to Opus after release. Halves
   PSRAM need and keeps the 5-minute cap without streaming to flash.
3. **Bitrate** — 12, 16, or 24 kbps? 16 is the usual speech sweet spot.
   Decide by ear on real recordings.
4. **Container** — the 16-byte header in PROTOCOL.md: magic, version, codec id,
   sample rate, duration, and a CRC. Is that enough, or should it be Ogg so
   iOS can play it with zero code?
