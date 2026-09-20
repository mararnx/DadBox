# Storage & queue

**Role.** Nothing a child records is ever lost because the network was down,
and nothing lingers on the device longer than it must.

## Current design

> **Decided 2026-09-20:** outbox/inbox as container files with CRC; resume from `upload-state` on boot; flash-full → oldest-first eviction with a telemetry flag (Q2). OTA in scope for M3 (Q1) — it's a plain HTTPS fetch now that the box has an IP stack.

- Outbox and inbox as files in a LittleFS partition on the 16 MB flash.
- Each message is a directory: header, payload, and a small state file.
- Uploads are chunked and resumable; the message id is minted on-device.
- Wiped from flash after confirmed upload (outbox) or after play + grace (inbox).

## Checked

- 16 MB flash minus app (~2 MB ×2 for OTA) leaves ~10 MB for storage — about
  80 minutes of Opus, or 20 minutes of ADPCM. Plenty for a queue, not for an
  archive. Good: the box is not supposed to be an archive.
- SPI flash writes at hundreds of KB/s — fast enough to stream PCM during
  capture if that route is chosen, but wear on the same sectors is a concern
  over years. LittleFS wear-levels; still, prefer not to write raw PCM.
- Power loss mid-write: LittleFS is power-fail safe at the file level, but the
  message state (queued/uploading/uploaded) must be written atomically, and a
  half-written payload must be recognisable as such on boot.
- OTA is not in the plan. It should be. A box in another house that cannot be
  updated is a box that stays broken.

## Questions

1. **OTA** — in scope for M3? Via HTTPS from our server is straightforward
   once the modem gives us an IP stack. Suggest yes; it is the difference
   between a fixable box and a returnable one.
2. **How many messages can wait?** If the box is offline for a week and the
   child records twenty, is that fine? Suggest: yes, until flash is full, then
   oldest-first eviction with a telemetry flag — never a visible error.
3. **Inbox grace** — how long after play does a message survive on the box?
   Ties to "can the child replay" in [audio-playback.md](audio-playback.md).
4. **Favourites** — does anything ever get pinned on the device? Suggest no on
   the device; if favourites exist they live in the app.
5. **Boot recovery** — on power-up, resume every interrupted upload from the
   last acknowledged chunk. Does the server keep partial uploads, and for how
   long?
