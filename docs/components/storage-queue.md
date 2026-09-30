# Storage & queue

**Role.** Nothing a child records is ever lost because the network was down,
and nothing lingers on the device longer than it must.

## Current design

- **The SD card is the whole machine** ([ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md)):
  a read-only root overlay, and a writable ext4 `/data` partition for the
  outbox, inbox, logs and the service's own code (`/opt/dadbox` →
  `/data/app`). Every message write is **fsync-then-rename**.
- The capture is written to `/data` as it happens — nothing is ever only in
  RAM. A power loss mid-story costs the last buffer.
- `/data/outbox` and `/data/inbox` hold container files with a CRC
  ([PROTOCOL.md](../PROTOCOL.md)), each with a small state file
  (queued / uploading / uploaded).
- Uploads are chunked and resumable; on boot every interrupted upload resumes
  from the server's `upload-state`. The message id is minted on-device;
  ordering is a monotonic `seq` kept on `/data`, not the clock.
- **The outbox is never evicted** ([ADR 0010](../decisions/0010-nothing-is-lost.md)).
  The *got it* pulse is given only after fsync; deletion only on the server's
  2xx to `complete`, which itself follows a durable write and CRC match.
- **The box is not an archive** ([ADR 0018](../decisions/0018-archive-forever.md)).
  An inbox message is removed after play and may be evicted under pressure;
  the server keeps everything and re-serves it.
- Capacity is the card — gigabytes against ~120 KB/min. Telemetry carries
  `storage_pct`; at 80 %, or on any storage error, Record blinks blue
  (ADR 0024) and telemetry says `fault: storage`.
- **Cards:** the kit's 16 GB card on the bench; an endurance-grade card
  (SanDisk High Endurance) before the box leaves home. The bench card becomes
  the spare image in a drawer.
- Updates are `rsync` or `git pull` into `/data` over Tailscale, then
  `systemctl restart dadbox`. The overlay is never disabled in the field.

## Checked

- The failure to plan for is not a full card but a corrupt one. The overlay
  makes the OS power-loss safe; fsync-then-rename makes each message either
  whole or absent; a half-written capture must be recognisable as such on
  boot and recovered up to its last good buffer.
- A 16 kHz PCM stream is 32 KB/s — trivial for the card, and the reason
  streaming to disk costs nothing.
- Message state (queued / uploading / uploaded) is written atomically, the
  same way as the message.
- A box in another house that cannot be updated is a box that stays broken.
  Code on `/data` plus SSH over Tailscale is the update path; no separate OTA
  mechanism is needed.

## Questions

1. **Inbox grace** — removed *when* after play: at once, at the next
   check-in that reports `played`, or after a while so the child can hear it
   again? Ties to replay in [audio-playback.md](audio-playback.md) Q3.
2. **OS updates** — the service updates over SSH, but the root is read-only
   and stays so in the field. Security updates over years: a freshly imaged
   card swapped in by hand, or an overlay-off maintenance window at home?
3. **Partial uploads on the server** — kept how long? Suggest: indefinitely —
   they are the other half of "never lost".
4. **Favourites on the box?** Suggest no; the archive and anything like
   favourites live in the app.
5. **A pulled card** — the OS is not secret, but queued audio should be
   unreadable: messages are encrypted before they reach the outbox, the raw
   capture is not. How long does the raw capture live after encoding, and is
   it shredded or just unlinked? See [security-privacy.md](security-privacy.md).
6. **Power pull mid-write** — prove it: pull the supply during capture and
   during an upload, and check what boot recovers.
