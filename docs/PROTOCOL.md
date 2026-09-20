# Protocol v0 (draft)

The contract between the three code streams. Firmware, server and iOS app all
depend on this document; change it here first, then in the code.

Written as though both ends were boxes. The iOS app is a client that happens to
be software — nothing app-specific belongs in the firmware.

## Audio format

| Property | Value |
| --- | --- |
| Sample rate | 16 kHz mono |
| Capture | 16-bit PCM into PSRAM while the button is held |
| Encode | **After release**, never in the capture path |
| Codec | Opus @ 16 kbps (fallback: IMA-ADPCM if the encoder proves painful) |
| Max length | 5 minutes (~600 KB Opus) |
| Container | Raw Opus packets with a 16-byte header, see below |

Five minutes rather than sixty seconds: data is effectively free here, and
cutting a child off mid-story is a real cost.

## Message object

```json
{
  "id": "01JAYZ3K7QW9E8RVX2M4N6P8TD",
  "from": "box" | "parent",
  "created_at": "2026-09-20T18:04:11Z",
  "duration_ms": 14200,
  "codec": "opus-16k-16",
  "bytes": 28400,
  "state": "queued" | "uploaded" | "delivered" | "played" | "expired"
}
```

`id` is a ULID generated **at the recording end**, before the first byte is
sent. It is the idempotency key: the device may retry an upload any number of
times and the server must treat repeats as the same message. Never let the
server mint ids — a device that loses its uplink mid-upload has to be able to
resume without creating duplicates.

## Child → parent

1. Button held → capture to PSRAM. Ring fills as the cap approaches.
2. Released → encode, write to the flash outbox with `state: queued`.
3. Box syncs: chunks the payload into Notes, uploads, marks `uploaded`.
4. Notehub routes to the backend, which reassembles and stores the blob.
5. Backend sends an APNs push to the parent's phone.
6. App plays it → `POST /messages/:id/played`.

## Parent → child

1. App records, uploads, gets `state: uploaded`.
2. Backend queues it as an inbound Note for the box.
3. Box picks it up on its next sync, reassembles, stores in the flash inbox,
   marks `delivered`. Ring breathes, one segment per waiting message.
4. Quiet hours suppress the chime but not the glow — a child should be able to
   see that something is waiting without being woken by it.
5. Child presses play → `played` reported on the next sync.

## Chunking

Notecard payloads are limited; a 600 KB message will not fit in one Note.

```
chunk = { mid, seq, total, bytes }
```

Reassembly is the receiver's problem. Chunks may arrive out of order and may
repeat. A message is only complete when all `total` chunks are present — until
then it is invisible to the user at both ends.

**Chunk size is unverified.** Confirm the Notecard's real binary payload limit
before building against an assumed 4 KB.

## Telemetry (box → backend, every sync)

```json
{
  "battery_pct": 68, "charging": false, "rssi": -91,
  "fw": "0.1.0", "outbox": 0, "inbox": 2, "uptime_s": 41022
}
```

The app surfaces all of it. This is how a box dead in a bag gets noticed by an
adult instead of being read as silence by a child.

## Controls

- **Mute** — settable by either household, visible to both in the app. A
  known-off is better than a mystery silence.
- **Quiet hours** — enforced on the device, not by the sender's discipline.

## Retention

Messages are deleted a fixed, short interval after `played`. The box wipes each
item from flash once it is played or confirmed uploaded. No transcription, no
third-party analytics, no speech services anywhere in the path.

## Open

- Auth between box and backend — Notehub device identity may be sufficient.
- Does a failed send ever become visible to the child? Current answer: no.
- Favourites: a way to keep a message from expiring. Undecided.
