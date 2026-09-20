# Codec

**Role.** Make a voice message small enough to upload in seconds and sound
like the person.

## Current design

> **Platform change 2026-09-20 — [ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md):**
> the box is a Linux machine; `ffmpeg` is on it.

- Capture: 16 kHz mono 16-bit PCM, ALSA, written to `/data` as it happens.
- After the lid closes: trim silence, `ffmpeg -i capture.wav -c:a libopus
  -b:a 16k -application voip out.opus` → Ogg Opus, ~120 KB/min.
- Wire: `codec = 2` (Opus in Ogg) inside the 16-byte container. `codec = 1`
  (IMA-ADPCM) stays reserved so an ESP32 box could still speak the protocol.
- iOS decodes Opus natively; the server may transcode to AAC for the app if
  Ogg playback proves awkward.

## Checked

- A Cortex-A53 encodes 16 kHz Opus many times faster than real time; a
  5-minute message encodes in seconds. There is no codec constraint anywhere.
- Data is unlimited (Digital Republic); the bitrate is about sound, not cost.
  16 kbps `voip` is the speech sweet spot; 24 kbps if a child's voice sounds
  thin — decide by ear.
- Upload time on Flat 1 (0.5 Mbps up): ~10 s for a 5-minute message.

## Questions

1. **Ogg Opus straight to the app, or server-side AAC?** Try Ogg first
   (AVFoundation plays it on recent iOS); fall back to transcoding.
2. **Bitrate** — 16 vs 24 kbps, by ear on real recordings from the box.
3. **Trim thresholds** — silence detection level and the < 1 s discard rule;
   tune on real recordings, not on the bench.
