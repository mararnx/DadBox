# Server concept

**Status:** draft, revised 2026-09-21. Decided: one managed host, end-to-end
encryption, iOS the only client ([ADR 0017](decisions/0017-managed-hosting-e2ee.md));
archive forever ([ADR 0018](decisions/0018-archive-forever.md)); host:
Supabase Pro, Zurich. Nothing here is built; PROTOCOL.md changes first.

The job: hold the audio, wake a phone immediately, know whether the box is
alive — without being able to listen, and without ever throwing a message away.

## Shape

```
  DadBox ───── HTTPS ─────►  ┌──────────── Supabase · Pro · Zurich (eu-central-2) ───┐
  bearer token: box          │  API       one Edge Function, `api` — the PROTOCOL.md │
                             │            endpoints; our own token check, JWT off    │ ── APNs ──► iPhone
  iPhone app ── HTTPS ────►  │  metadata  Postgres — RLS on, zero policies           │   "New message" + id,
  bearer token: parent-a     │  audio     Storage — private bucket, ciphertext,      │    never content
                             │            forever                                    │
                             │  clock     pg_cron, every minute ─► pg_net ─► `tick`  │
                             │  unused    Auth, Realtime, the auto-generated REST API│
                             └───────────────────────────────────────────────────────┘

  Keys:  box /data/keys (root 0600)  ·  iPhone Keychain (iCloud-synced)  ·  paper, in a drawer
         never on the host
```

Base URL: `https://<project>.supabase.co/functions/v1/api` — PROTOCOL.md paths
are relative to it. No custom domain needed (a paid add-on; the URL is
configuration on the box and in the app, not a promise).

Two clients, one contract. No accounts, no login page, no web UI: three
hardcoded identities, as the server was always meant to be.

Neither client ever holds a Supabase key. The anon key is not shipped
anywhere; the service-role key exists only inside the Edge Function.

## Protection, in layers

| # | Layer | What it stops |
| --- | --- | --- |
| 1 | **E2EE** — AES-256-GCM on the box / phone, decrypted only on phone / box | The host, a leaked API credential, a public-bucket mistake, a subpoena to the host. They hold ciphertext. |
| 2 | **Identity on every request** — a 256-bit bearer token per identity, stored server-side as SHA-256 only | Anonymous access. |
| 3 | **Least privilege per token** — the box can upload, and fetch **only its current inbox**; it can never list or fetch history. A parent sees only messages where they are `from` or `to`. v1 enforces `box → parent-a`. | A pulled SD card (token + key) reaching into the archive. Parent-b reading parent-a's thread, later. |
| 4 | **Nothing public** — private bucket, no signed URLs; RLS enabled on every table with **no policies**, so the auto-generated REST API returns nothing to anyone; only the Edge Function's service role reads or writes | Guessable links, direct database access, a leaked anon key. |
| 5 | **Hygiene** — secrets only in Supabase function secrets, 2FA on the Supabase and GitHub accounts, Auth sign-ups disabled, no analytics or logging of bodies, rate limit on unauthenticated requests | The supply chain and the account itself. |
| 6 | **Two copies of the archive** — Supabase Storage + the phone (and its backup). Pro's daily backups cover the database, **not** Storage objects | One of them disappearing. |
| 7 | **Audit** — every audio fetch, `played`, delete and settings change recorded with identity and time | Not knowing. |

**What the host can still see:** that messages exist, when, how long,
between which identities, and the box's telemetry. Not the audio.

## Encryption

```
container (PROTOCOL.md)      flags bit0 = 1
payload  =  key_id (1) ‖ nonce (12, random) ‖ AES-256-GCM ciphertext ‖ tag (16)
AAD      =  the 16 header bytes ‖ message id (26 ASCII)
crc32    =  over header + payload, as today — the server checks it without a key
```

- One 32-byte key **per parent ↔ box pair**. `key_id` names it, which gives
  two things: parent-b never holds parent-a's key ([ADR 0008](decisions/0008-two-parents-later.md)),
  and a key can be **rotated** — new `key_id` going forward, the old key kept
  on the phone to read the archive.
- The AAD binds ciphertext to its header and id: the server cannot swap the
  audio of two messages or alter a duration without the tag failing.
- Ceremony (one family, one box): the app generates the key and shows it as
  43 base64url characters + QR. It is baked into the box at flash time from a
  gitignored `.env`. On the phone it is an iCloud-synced Keychain item, so a
  new phone has it. A paper copy goes in a drawer — with an archive kept
  forever, losing every copy loses everything.
- CryptoKit on iOS, `cryptography` (AES-GCM) in the box's Python. Same
  vectors tested on both, on the Mac, before any hardware.

## Data model

```
identities      id 'box'|'parent-a'|'parent-b' · token_hash
push_devices    identity · apns_token · environment · updated_at
messages        id (ULID, client-minted) · seq · from · to · created_at · time_ok · duration_ms
                codec · key_id · bytes · chunk_total · crc32 · state · blob_key
                uploaded_at · delivered_at · played_at · deleted_at            unique (from, seq)
message_chunks  message_id · seq · data (≤ 32 KB)                              primary key (message_id, seq)
box_status      single row: last telemetry · last_checkin_at · next_due_at
checkins        at · telemetry                                                 pruned at 30 days
settings        single row · per-field updated_by / updated_at (who muted, when)
alerts          kind · raised_at · pushed_at · cleared_at                      so a late box pushes once
audit_log       at · identity · action · message_id
```

Chunks live in the database, not the bucket: the primary key *is* the
idempotency rule (a repeated chunk is an upsert), `upload-state` is one
`select seq`, and a 5-minute message is ~20 rows that vanish after assembly.
The assembled container goes to the bucket and stays there.

## The protocol, serverless

| Endpoint | How |
| --- | --- |
| `PUT /messages/{id}` | Upsert by id; same metadata → 200, different → 409. Enforce `to`. |
| `PUT …/chunks/{seq}` | Raw body ≤ 32 KB. Upsert. 2xx after commit. |
| `GET …/upload-state` | `select seq from message_chunks where message_id = ?`. |
| `POST …/complete` | Already `uploaded` → 200 (idempotent). Else: all `chunk_total` present → stream chunks through CRC32 into one bucket `put` and **await it** → check CRC against the trailer → `update messages set state = 'uploaded'` and commit → **then** 2xx. APNs push afterwards (`waitUntil`). **This 2xx is the server's confirmation — the box deletes its outbox copy on it and not before** ([ADR 0010](decisions/0010-nothing-is-lost.md) item 4, unchanged). |
| `GET …/audio` | Streams from the bucket, `Range` passed through. Box: only ids in its current inbox. First fetch by the recipient sets `delivered`. |
| `POST …/played` | Recipient only. Feedback for the sender; starts no clock. |
| `GET /messages?after=&limit=` | Parents only. **New** — the protocol has no list endpoint today. The app pages through it to fill and verify its local archive. |
| `DELETE /messages/{id}` | Parents only, own messages. Deletes the blob, keeps a tombstone. **New.** |
| `POST /device/checkin` | Box only. One SQL function (`rpc`): update `box_status`, insert `checkins`, clear a `late` alert, return settings + inbox ids — a single database round trip. Runs every minute on mains: ~45 k invocations a month against Pro's 2 M. |
| `GET /device/status` | Parents only. Last telemetry, `last_checkin_at`, `late`, settings with who-set-what. **New.** |
| `pg_cron` → `pg_net` → `POST /tick` (shared secret), every minute | Box late (now > `next_due_at`, i.e. 2 × `next_checkin_s`) → alert + push, once. Unplayed > 48 h → push, once. Drop chunk rows of completed messages. Prune `checkins`. **Never** deletes audio, **never** reaps an incomplete upload. |

### PROTOCOL.md v0.3 — what changes first

1. § Open → specified: the encryption envelope; `flags bit0` mandatory.
2. `codec = 3` — AAC-LC in M4A, parent → box. iOS records it natively, the
   box decodes with `ffmpeg`. Replaces "the server may transcode".
3. New endpoints: `GET /messages`, `DELETE /messages/{id}`, `GET /device/status`.
4. `key_id` in the message object.
5. § Durability and retention: archive forever; `played` starts nothing;
   `expired` unused; box token scoped to its inbox.
6. § Transport: "no third party in the path" → "no third party that can read
   it", pointing at ADR 0017.

## The archive

| Where | What | Until |
| --- | --- | --- |
| Box outbox | own recordings | the server's 2xx on `complete` |
| Box inbox | parent's messages | played, or evicted under pressure |
| Host bucket | every message, ciphertext | forever, or a parent's explicit delete |
| iPhone | every message it has fetched, ciphertext + key in Keychain | forever; rides in the phone's backup |

Size: 16 kbps Opus ≈ 120 KB/min. An hour a month ≈ 90 MB a year. Pro's
included 100 GB is not a number this project will ever meet.

## Repo layout

```
server/
  supabase/
    functions/api/index.ts     routes (Hono): parse → core → respond      deploy with verify_jwt = false
    functions/api/core/        protocol logic, framework-free, unit-tested on the Mac (deno test)
    functions/api/container.ts header parse, CRC32 — no keys here, ever
    functions/api/apns.ts      ES256 JWT via WebCrypto, HTTP/2 fetch
    migrations/                schema · RLS enable · checkin() · pg_cron job
    config.toml
  .env.example                 names only
tools/fakebox/                 first thing to build: speaks v0.3 incl. encryption, drops mid-chunk on request
```

Local development is `supabase start` (Docker) on the Mac — Postgres, Storage
and the function, no cloud — with `fakebox` pointed at it.

Secrets, as Supabase function secrets and nowhere else: `APNS_KEY_P8`,
`APNS_KEY_ID`, `APNS_TEAM_ID`, `TICK_SECRET`. Box and app tokens come from a
one-off script that prints them once and stores only the hash.

## Cost

USD 25/month, flat; nothing here approaches a Pro quota. Set the spend cap on.

## To verify — in this order

1. **APNs from an Edge Function.** Deno's `fetch` negotiates HTTP/2; the JWT
   is ES256 via WebCrypto. Widely assumed, not well documented — Supabase's
   own examples go through Firebase, which is not an option here. A
   twenty-line spike before anything else; it needs the Apple Developer
   account.
2. Check-in latency from the modem including Edge Function cold starts — a
   once-a-minute caller should stay warm; p95 under 1 s.
3. `pg_cron` at one-minute cadence calling the function through `pg_net`.
4. Storage upload from the function is awaited and durable before `complete`
   answers; `Range` passes through on download.
5. The project really is in `eu-central-2`, and functions run there
   (`x-region`), not wherever the caller is nearest.

## Questions

1. ~~Which host?~~ — Supabase Pro, decided 2026-09-21.
2. **Can the parent delete a message from the archive?** Drafted as yes, per
   message, in the app. Or is forever *forever*?
3. **Parent-b and the archive** — own key, own thread, own archive; neither
   parent can read the other's. Confirm.
4. **Does the phone keep ciphertext or decrypted audio?** Suggest ciphertext
   + Keychain key: a stray device backup then reveals nothing.
