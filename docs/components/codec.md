# Codec

**Role.** Make a voice message small enough to upload in seconds and sound
like the person.

## Current design

- Capture: 16 kHz mono 16-bit PCM, ALSA, written to `/data` as it happens.
- After recording stops: trim silence, then `ffmpeg -i capture.wav -c:a
  libopus -b:a 16k -application voip out.opus` → Ogg Opus, ~120 KB/min.
- Wire: `codec = 2` (Opus in Ogg) inside the 16-byte container
  ([PROTOCOL.md](../PROTOCOL.md)). `codec = 1` (IMA-ADPCM) is reserved and
  unused.
- **No server-side transcode.** The audio is end-to-end encrypted, so the
  server cannot convert it ([ADR 0017](../decisions/0017-managed-hosting-e2ee.md)).
  The iOS app plays Ogg Opus itself; the box has `ffmpeg` and plays whatever
  the phone records — the protocol gains `codec = 3` (AAC-LC) for that
  direction.

## Checked

- A Cortex-A53 encodes 16 kHz Opus many times faster than real time; a
  5-minute message encodes in seconds. There is no codec constraint anywhere.
- Data is unlimited (Digital Republic Flat 1); the bitrate is about sound,
  not cost. 16 kbps `voip` is the speech sweet spot; 24 kbps if a child's
  voice sounds thin — decide by ear.
- Upload time on Flat 1 (0.5 Mbit/s up): ~10 s for a 5-minute message.

## Questions

1. **Bitrate** — 16 vs 24 kbps, by ear on real recordings from the box.
2. **Trim thresholds** — silence detection level and the < 1 s discard rule;
   tune on real recordings, not on the bench.
