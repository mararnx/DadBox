# Protocol v0.3 (draft)

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

Each identity authenticates with its own long-lived bearer token (256 random
bits; the server stores only its SHA-256). Losing a token lets someone *send*;
it must never let them *listen* — the audio is end-to-end encrypted
([ADR 0017](decisions/0017-managed-hosting-e2ee.md)) and the token is not the key.

Tokens are scoped. The **box** token can upload, check in, and fetch only the
messages in its current inbox — never a list, never history. A **parent**
token reaches only messages where that parent is `from` or `to`.

## Audio format

| Property | Value |
| --- | --- |
| Sample rate | 16 kHz mono |
| Capture | ALSA (I2S) → 16-bit PCM written to disk as it happens |
| Cap | 5 minutes |
| Wire codec, v1 | **Opus 16 kbps in an Ogg container** (`codec = 2`), ~120 KB/min, encoded with `ffmpeg` after recording stops |
| Parent → box | **AAC-LC in M4A** (`codec = 3`) — what iOS records natively; the box decodes it with `ffmpeg`. Ogg Opus (`codec = 2`) is equally valid in this direction |
| Reserved | `codec = 1` IMA-ADPCM — unused on the Pi; kept so an ESP32 box could still speak the protocol |
| Trim | leading/trailing silence removed; < 1 s of speech → discarded |

The box is a Linux machine ([ADR 0014](decisions/0014-raspberry-pi-zero-2w.md));
encoding Opus is not a constraint of any kind. **The server never transcodes**
— it cannot read the audio. The iOS app plays Ogg Opus itself — iOS 26 reads it
natively through `AVAudioPlayer` (verified 2026-09-21, `ios/DESIGN.md` § Audio);
the box plays whatever the app sends.

Byte-exact examples of the container and the encryption below are in
[testvectors/container-v1.json](testvectors/container-v1.json). Every
implementation — box, app, fake box — must produce and accept them.

### Container

```
offset  size  field
0       4     magic      "DBX1"
4       1     version    1
5       1     codec      1 = IMA-ADPCM, 2 = Ogg Opus, 3 = AAC-LC (M4A)
6       1     channels   1
7       1     flags      bit0: encrypted — always 1; the server rejects 0
8       4     sample_rate  u32 LE
12      4     duration_ms  u32 LE
16      …     payload
end-4   4     crc32 of header+payload, u32 LE
```

### Encryption

Every payload is encrypted at the recording end and decrypted only at the
listening end ([ADR 0017](decisions/0017-managed-hosting-e2ee.md)). The server
stores and moves ciphertext.

```
payload  =  key_id (1) ‖ nonce (12, random per message) ‖ AES-256-GCM ciphertext ‖ tag (16)
AAD      =  the 16 header bytes ‖ the message id (26 ASCII bytes)
```

- The plaintext is the encoded audio file (Ogg or M4A) exactly as the codec
  field says.
- One 32-byte key per parent ↔ box pair. `key_id` 1 = the first `parent-a`
  key, 2 = the first `parent-b` key; higher values are rotations. A receiver
  keeps old keys to read old messages.
- The AAD binds the ciphertext to its header and id: a server cannot swap the
  audio of two messages or alter `duration_ms` without the tag failing.
- The crc32 covers header + (encrypted) payload, so the server verifies
  integrity without a key.
- Keys live in `/data/keys` on the box (root, 0600) and in the iPhone
  Keychain. Never on the server, never in this repo.

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
  "codec": 2,
  "key_id": 1,
  "bytes": 113600,
  "state": "queued" | "uploading" | "uploaded" | "delivered" | "played",
  "uploaded_at": "2026-09-20T18:04:31Z",
  "delivered_at": "2026-09-20T18:04:40Z",
  "played_at": null
}
```

`id` is a ULID minted **at the recording end** before the first byte is sent.
It is the idempotency key: retries of any request for the same `id` are the
same message. The server never mints ids.

`uploaded_at`, `delivered_at` and `played_at` are set by the server, on its
clock, and are `null` until they happen. "Played 19:12" is the sender's whole
feedback loop; `state` alone cannot say it.

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
and speaks HTTPS directly to the server. The server is a managed host
([ADR 0017](decisions/0017-managed-hosting-e2ee.md)): there is no third party
in the path **that can read a message** — and no relay service, which is
also why there is no SMS wake ([ADR 0015](decisions/0015-adaptive-polling.md)).
Data is unlimited; the poll cadence is a battery/latency trade only.

All paths below are relative to one configured base URL (for Supabase:
`https://<project>.supabase.co/functions/v1/api`). Every request carries
`Authorization: Bearer <token>`.

### Upload (either direction)

```
PUT  /messages/{id}                      metadata; idempotent create → the message object
PUT  /messages/{id}/chunks/{seq}         raw bytes; header X-Chunk-Total
GET  /messages/{id}/upload-state         → { "received": [0,1,2,5], "complete": false }
POST /messages/{id}/complete             server verifies crc32, sets uploaded → the message object
```

The metadata body is the message object without `id`, `from`, `state` and the
server timestamps: `seq`, `to`, `created_at`, `time_ok`, `duration_ms`,
`codec`, `key_id`, `bytes` — `bytes` being the size of the whole container.
The same `id` with different metadata is `409`. `X-Chunk-Total` is
⌈bytes / 32768⌉; every chunk is exactly 32 KB except the last. `complete`
answers `409 { "missing": [3,4] }` while chunks are missing and `422` when the
assembled container contradicts its metadata, is not encrypted, or fails its
crc — and `200` again, harmlessly, on every retry after it has succeeded.

Chunk size **32 KB**. Chunks may arrive out of order and may repeat. On boot,
the box asks `upload-state` for every message in `uploading` and resumes from
the gaps. A message is invisible to the recipient until `complete` succeeds.

### Download

```
GET  /messages/{id}/audio                Range supported; delivered once the recipient has been sent the last byte
POST /messages/{id}/played               recipient only; feedback for the sender, starts no clock
```

### Archive and state (parents only)

```
GET    /messages?cursor={c}&limit={n}    → { "messages": [ … ], "cursor": "…", "more": false, "max_seq": 41 }
GET    /messages/{id}                    one message object — refresh its state
GET    /device/status                    → { "telemetry": {…}, "last_checkin_at": "…", "late": false,
                                             "settings": {…}, "settings_meta": { "mute.a": { "by": "parent-a", "at": "…" } } }
PATCH  /settings                         partial settings object → the same shape as /device/status returns
PUT    /push-token                       { "apns": "<hex>", "environment": "production" | "sandbox" }
```

- `GET /messages` returns the caller's thread **in order of last change** —
  a message reappears when its state moves — so the app orders the timeline
  itself, by `uploaded_at`. `cursor` is opaque; omit it to start from the
  beginning, pass the last one back to get only what is new or changed. Keep
  asking while `more` is true.
  `max_seq` is the highest `seq` the server has seen **from the caller**, so a
  reinstalled app continues its counter instead of reusing one.
- `PATCH /settings`: a parent may set `poll`, `quiet_hours`, `led_brightness`,
  `volume`, and **only its own** mute (`mute.a` by `parent-a`, `mute.b` by
  `parent-b`). Anything else → 403. Every field records who set it and when.
- `PUT /push-token` is idempotent per identity and device token.

The app keeps its own copy of every message it fetches
([ADR 0018](decisions/0018-archive-forever.md)); `GET /messages` is how it
fills and verifies that copy.

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

## Push (server → iPhone)

APNs, sent by the server directly. Payloads carry a kind and ids — **never
content, never a name** ([ADR 0017](decisions/0017-managed-hosting-e2ee.md)).

| `kind` | Sent when | Carries | APNs |
| --- | --- | --- | --- |
| `message` | `complete` succeeds for a message to this parent | `id` | alert, `mutable-content: 1` — the phone fetches, verifies and retitles it |
| `played` | the box posts `played` for this parent's message | `id` | background, `content-available: 1` |
| `box_late` | now > 2 × `next_checkin_s` since the last check-in; once per outage | — | alert |
| `fault` | telemetry `fault` becomes non-null; once per fault | `fault` | alert |
| `battery_low` | `battery_pct` < 20 on battery; once per discharge | `battery_pct` | passive |
| `unplayed_48h` | a parent's message is unplayed 48 h after `uploaded_at`; once per message | `id` | passive |

Pushes are hints. The truth is whatever `GET /messages` and
`GET /device/status` say when the app next asks.

## Telemetry

```json
{
  "battery_pct": 68, "charging": false, "mains": false, "rssi": -91, "fw": "0.1.0",
  "outbox": 0, "outbox_bytes": 0, "outbox_oldest_s": 0, "storage_pct": 12,
  "inbox": 2, "uptime_s": 41022, "offline_s": 0, "next_checkin_s": 1800,
  "recording": false, "locked": false, "house": "unknown", "fault": null
}
```

- `battery_pct`, `charging` — `null` while no battery is fitted
  ([ADR 0019](decisions/0019-mains-first-battery-deferred.md)); `mains` is then always true.
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
- `locked` — the travel lock is engaged ([ADR 0016](decisions/0016-two-buttons-no-lid.md)).
  Without it, a locked box in a bag looks like a child who stopped talking.
- `house` is `unknown | a | b`, reserved for a dock ID resistor.

The app surfaces all of it; this is how a box dead in a bag gets noticed by an
adult.

## Settings (server → box on every check-in)

```json
{
  "poll": { "active_minutes": 1, "active_window_minutes": 90, "idle_minutes": 30 },
  "mute": { "a": false, "b": false },
  "quiet_hours": { "start": "20:00", "end": "07:00", "tz": "Europe/Berlin" },
  "led_brightness": 40,
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
- **The server never deletes a completed message**
  ([ADR 0018](decisions/0018-archive-forever.md)). `played` starts no clock.
  There is no delete endpoint in v1. The archive exists twice:
  on the server, and on the phone.
- The box is not an archive: outbox until the 2xx above; inbox until played
  (or evicted under pressure).
- Unplayed messages are never reaped; after 48 h the app is told.
- Telemetry history is not the archive: check-ins are pruned at 30 days.
- No transcription, no speech services, no third-party analytics anywhere.

## Open

- Key ceremony and rotation procedure (`components/security-privacy.md` Q2).
- Dock ID for `house`.
- OTA manifest format (M3).
