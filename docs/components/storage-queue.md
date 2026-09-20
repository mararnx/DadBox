# Storage & queue

**Role.** Nothing a child records is ever lost because the network was down,
and nothing lingers on the device longer than it must.

## Current design

> **Decided 2026-09-20:** outbox/inbox as container files with CRC; resume from `upload-state` on boot; flash-full → oldest-first eviction with a telemetry flag (Q2). OTA in scope for M3 (Q1) — it's a plain HTTPS fetch now that the box has an IP stack.

- Outbox and inbox as files on the TF card (FATFS, sync-on-write); the latest
  outbox message mirrored to a small LittleFS partition in the 4 MB flash.
- Each message is a directory: header, payload, and a small state file.
- Uploads are chunked and resumable; the message id is minted on-device;
  ordering is a monotonic `seq` from NVS, not the clock.
- **The outbox is never evicted** ([ADR 0010](../decisions/0010-nothing-is-lost.md)).
  The *got it* pulse is given only after fsync; deletion only on the server's
  2xx to `complete`, which itself follows a durable write and CRC match.
- During capture, the PSRAM buffer is checkpointed to flash every 30 s.
- The inbox may be evicted under pressure; the server re-serves it.

## Checked

- 4 MB flash minus two OTA app slots leaves under 1 MB — one message's worth
  of fallback, not a queue. The queue is the TF card: gigabytes, so capacity
  is not a question; card reliability is (see ADR 0013).
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
2. **Is ~20 minutes of offline audio enough headroom?** That is the outbox
   at ADPCM rates (~3 h once Opus lands). A week offline with forty 30-second
   messages fits. Full is the one place "never lost" and "always accept"
   collide: the lid records and there is nowhere to put it. Options:
   - accept the limit; fault pattern at 80 %, the co-parent sees it;
   - pull Opus forward from M3 to M1, for 10× the headroom;
   - add a microSD slot (~$3, gigabytes) so *never* means never — at the cost
     of a card that can corrupt, contacts that can oxidise, and one more
     thing to get wrong in the enclosure.
   Suggest: accept the limit for v1, Opus in M3, and revisit microSD only if
   the box actually spends long stretches offline.
   **Update ([ADR 0013](../decisions/0013-cat1-not-catm.md)):** the T-A7670G R2
   has **4 MB flash**, so the outbox *is* the TF card — a dependency after
   all. Mitigations: name-brand card, FATFS with sync-on-write, internal flash
   mirrors the latest message, missing/failed card → fault on the status LEDs
   and telemetry `fault: storage`. Capacity stops being a question.
3. **Inbox grace** — how long after play does a message survive on the box?
   Ties to "can the child replay" in [audio-playback.md](audio-playback.md).
4. **Favourites** — does anything ever get pinned on the device? Suggest no on
   the device; if favourites exist they live in the app.
5. **Boot recovery** — on power-up, resume every interrupted upload from the
   last acknowledged chunk. Does the server keep partial uploads, and for how
   long? Suggest: indefinitely — they are the other half of "never lost".
6. **Checkpoint interval** — 30 s during capture, or stream everything? 30 s
   is ~240 KB per write on a 16 kHz ADPCM stream; wear is modest. Measure.
7. **Flash encryption vs recovery** — with flash encryption on (M3), a dead
   box's queued messages cannot be recovered by pulling the chip. Is that the
   right trade? Probably yes: a lost box in the wrong hands matters more than
   a bricked one's last three messages. Say so explicitly.
