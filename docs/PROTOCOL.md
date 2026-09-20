# Protocol v0.2 (draft)

The contract between the three code streams. Firmware, server and iOS app all
depend on this document; change it here first, then in the code.

Written as though both ends were boxes, and as though there were two parents
([ADR 0008](decisions/0008-two-parents-later.md)). The iOS app is a client that
happens to be software — nothing app-specific belongs in the firmware.

## Identities

| id | what | v1 |
| --- | --- | --- |
| `box` | the child's device | built |
| `parent-a` | the parent with the app | built |
| `parent-b` | the co-parent | **reserved** — protocol only |

Each identity authenticates with its own long-lived bearer token. Losing a
token lets someone *send*; it must never let them *listen* to what others sent
(see `components/security-privacy.md`).

## Audio format

| Property | Value |
| --- | --- |
| Sample rate | 16 kHz mono |
| Capture | I2S → IMA-ADPCM 4-bit, encoded as it goes, into PSRAM |
| Cap | 5 minutes (~2.4 MB ADPCM) |
| Wire codec, v1 | IMA-ADPCM (`codec = 1`), ~64 kbps, ~480 KB/min |
| Wire codec, M3+ | Opus 16 kbps (`codec = 2`), transcoded after the lid closes |
| Trim | leading/trailing silence removed; < 1 s of speech → discarded |

ADPCM in the capture path is a handful of integer ops per sample — there is no
real-time constraint worth the name. The rule is **no real-time-constrained
codec in the capture path**, not "no encoding during capture".

### Container

```
offset  size  field
0       4     magic      "DBX1"
4       1     version    1
5       1     codec      1 = IMA-ADPCM, 2 = Opus
6       1     channels   1
7       1     flags      bit0: encrypted (reserved)
8       4     sample_rate  u32 LE
12      4     duration_ms  u32 LE
16      …     payload
end-4   4     crc32 of header+payload, u32 LE
```

## Message object

```json
{
  "id": "01JAYZ3K7QW9E8RVX2M4N6P8TD",
  "from": "box",
  "to": "parent-a",
  "created_at": "2026-09-20T18:04:11Z",
  "duration_ms": 14200,
  "codec": 1,
  "bytes": 113600,
  "state": "queued" | "uploading" | "uploaded" | "delivered" | "played" | "expired"
}
```

`id` is a ULID minted **at the recording end** before the first byte is sent.
It is the idempotency key: retries of any request for the same `id` are the
same message. The server never mints ids.

In v1 the box always sends `to: parent-a`, and the server enforces it.

## Transport

The box has an IP stack (LTE-M over PPP, [ADR 0006](decisions/0006-bare-modem-not-notecard.md))
and speaks HTTPS directly to the server. No third party in the path.

### Upload (either direction)

```
PUT  /messages/{id}                      metadata; idempotent create
PUT  /messages/{id}/chunks/{seq}         raw bytes; header X-Chunk-Total
GET  /messages/{id}/upload-state         → { "received": [0,1,2,5] }
POST /messages/{id}/complete             server verifies crc32, sets uploaded
```

Chunk size **32 KB**. Chunks may arrive out of order and may repeat. On boot,
the box asks `upload-state` for every message in `uploading` and resumes from
the gaps. A message is invisible to the recipient until `complete` succeeds.

### Download

```
GET  /messages/{id}/audio                Range supported
POST /messages/{id}/played
```

### Check-in (box only)

One request does everything the box needs between events:

```
POST /device/checkin
  → body: telemetry (below)
  ← { "settings": {…}, "inbox": ["01J…", "01J…"] }
```

The box checks in on a timer (`settings.poll_minutes`, default 10, app-set
1-60) and immediately after any upload. Inbound latency is therefore the poll
interval; the parent controls the trade against battery from the app.

## Telemetry

```json
{
  "battery_pct": 68, "charging": false, "rssi": -91, "fw": "0.1.0",
  "outbox": 0, "inbox": 2, "uptime_s": 41022,
  "lid_open": false, "house": "unknown"
}
```

`house` is `unknown | a | b`, reserved for a dock ID resistor. The app surfaces
all of it; this is how a box dead in a bag gets noticed by an adult.

## Settings (server → box on every check-in)

```json
{
  "poll_minutes": 10,
  "mute": { "a": false, "b": false },
  "quiet_hours": { "start": "20:00", "end": "07:00", "tz": "Europe/Berlin" },
  "ring_brightness": 40,
  "volume": 70
}
```

Quiet hours: glow yes, chime no, play still works. Mute: no sound at all, glow
persists; the app shows who set it and when. Both are enforced on the device.

## Retention

- Deleted from the server 24 h after `played`.
- Unplayed messages do not expire silently; after 48 h the app is told.
- The box wipes each item from flash once played (inbox) or once `complete`
  succeeds (outbox). Flash full → oldest-first eviction, telemetry flag, no
  visible error.
- No transcription, no speech services, no third-party analytics anywhere.

## Open

- **On-device encryption** (flag bit0): recommended, not yet decided. Family
  key in NVS + Keychain; the server stores ciphertext.
- Opus transcode timing on the ESP32-S3 — measure before scheduling.
- Dock ID for `house`.
- OTA manifest format (M3).
