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
| Capture | ALSA (I2S) → 16-bit PCM written to disk as it happens |
| Cap | 5 minutes |
| Wire codec, v1 | **Opus 16 kbps in an Ogg container** (`codec = 2`), ~120 KB/min, encoded with `ffmpeg` after the lid closes |
| Reserved | `codec = 1` IMA-ADPCM — unused on the Pi; kept so an ESP32 box could still speak the protocol |
| Trim | leading/trailing silence removed; < 1 s of speech → discarded |

The box is a Linux machine ([ADR 0014](decisions/0014-raspberry-pi-zero-2w.md));
encoding Opus is not a constraint of any kind. iOS decodes Opus natively; the
server may still transcode to AAC for the app if convenient.

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
  "seq": 184,
  "from": "box",
  "to": "parent-a",
  "created_at": "2026-09-20T18:04:11Z",
  "time_ok": true,
  "duration_ms": 14200,
  "codec": 1,
  "bytes": 113600,
  "state": "queued" | "uploading" | "uploaded" | "delivered" | "played" | "expired"
}
```

`id` is a ULID minted **at the recording end** before the first byte is sent.
It is the idempotency key: retries of any request for the same `id` are the
same message. The server never mints ids.

`seq` is a monotonic per-sender counter kept in NVS. **It is the ordering key,
not `created_at`.** The box has no RTC battery: after a cold start it does not
know the time until it next connects, and messages recorded in that window get
a best-effort `created_at` with `time_ok: false`. The app shows those as
"recorded while offline" rather than inventing a time.

In v1 the box always sends `to: parent-a`, and the server enforces it.

## Transport

The box is a Linux machine with an LTE Cat-1 modem that appears as a USB
Ethernet interface ([ADR 0006](decisions/0006-bare-modem-not-notecard.md),
[ADR 0013](decisions/0013-cat1-not-catm.md), [ADR 0014](decisions/0014-raspberry-pi-zero-2w.md))
and speaks HTTPS directly to the server. No third party in the path — which is
also why there is no SMS wake ([ADR 0015](decisions/0015-adaptive-polling.md)).
Data is unlimited; the poll cadence is a battery/latency trade only.

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

The box checks in on a timer and immediately after any upload. The cadence
is adaptive ([ADR 0015](decisions/0015-adaptive-polling.md)), chosen by the
box from `settings.poll`:

| Box state | Modem | Interval |
| --- | --- | --- |
| On mains | stays on | `active_minutes` (default 1) |
| On battery, conversation window open | stays on | `active_minutes` |
| On battery, idle | off between check-ins | `idle_minutes` (default 30, app-set 5-60) |

A conversation window opens when an upload completes or the child plays a
message, lasts `active_window_minutes` (default 90), and restarts on each such
event. A message arriving does not open one. Inbound latency is therefore
≤ 1 minute whenever the box is plugged in or the child has just used it, and
`idle_minutes` otherwise. Every check-in reuses one TLS session and stays a
few hundred bytes.

## Telemetry

```json
{
  "battery_pct": 68, "charging": false, "mains": false, "rssi": -91, "fw": "0.1.0",
  "outbox": 0, "outbox_bytes": 0, "outbox_oldest_s": 0, "storage_pct": 12,
  "inbox": 2, "uptime_s": 41022, "offline_s": 0, "next_checkin_s": 1800,
  "lid_open": false, "house": "unknown", "fault": null
}
```

- `mains` — external power present. Not the same as `charging`: a full pack
  on mains is not charging. Selects the poll cadence.
- `next_checkin_s` — when the box intends to check in next. The server and
  the app call the box *late* after 2 × this, not after a fixed interval.
- `offline_s` — seconds since the last *successful* check-in, as seen by the
  box. Non-zero on the first check-in after a gap; the app uses it to say
  "the box was offline for 14 h — these 3 messages are from then".
- `outbox_oldest_s` — age of the oldest unsent message. The other half of that
  sentence.
- `storage_pct` — outbox flash in use. The fault pattern shows at 80 %.
- `fault` — `null`, or one of `storage`, `modem`, `capture`, `charger`. Mirrors
  the alternating status-LED pattern so the app can say what the LEDs mean.
- `house` is `unknown | a | b`, reserved for a dock ID resistor.

The app surfaces all of it; this is how a box dead in a bag gets noticed by an
adult.

## Settings (server → box on every check-in)

```json
{
  "poll": { "active_minutes": 1, "active_window_minutes": 90, "idle_minutes": 30 },
  "mute": { "a": false, "b": false },
  "quiet_hours": { "start": "20:00", "end": "07:00", "tz": "Europe/Berlin" },
  "ring_brightness": 40,
  "volume": 70
}
```

Quiet hours: glow yes, chime no, play still works. Mute: no sound at all, glow
persists; the app shows who set it and when. Both are enforced on the device.

## Durability and retention

[ADR 0010](decisions/0010-nothing-is-lost.md): nothing a child recorded is lost.

- The box gives its *got it* pulse only after the container is fsynced to the
  outbox. The **outbox is never evicted.**
- `POST /messages/{id}/complete` returns 2xx **only after** the server has
  durably stored the assembled blob and verified the CRC. The box deletes from
  its outbox only on that 2xx. Until then, two copies or none — never zero
  after a pulse.
- The inbox on the box *may* be evicted under pressure; the server still holds
  the message and the box re-downloads it.
- Deleted from the server 24 h after `played`.
- Unplayed messages never expire silently; after 48 h the app is told.
- No transcription, no speech services, no third-party analytics anywhere.

## Open

- **On-device encryption** (flag bit0): recommended, not yet decided. Family
  key in NVS + Keychain; the server stores ciphertext.
- Whether the app plays Ogg Opus directly or the server transcodes to AAC.
- Dock ID for `house`.
- OTA manifest format (M3).
