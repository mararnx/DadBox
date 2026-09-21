# ADR 0017 — One managed host, the audio end-to-end encrypted, iOS the only client

**Date:** 2026-09-21
**Status:** accepted (Marco, 2026-09-21) — host chosen the same day: Supabase, Pro plan

## Context

The server was sketched as Node + Fastify on a small EU VPS with local-disk
blobs (`components/server.md`, Q1). The preference is a managed platform: no
machine to patch, no disk to watch, free or nearly so. A first draft put
Vercel in front of Supabase and added a web page for listening; both were
dropped the same day — one host, not two, and no web UI.

A managed platform means someone else holds the disk and terminates TLS.
`components/security-privacy.md` already names the fix — encrypt on the box
and on the phone with a key the server never has — but left it "recommended,
open". On someone else's infrastructure, and with an archive that is kept
forever ([ADR 0018](0018-archive-forever.md)), it stops being optional.

## Decision

1. **One managed host.** API, database, blobs and scheduler all live with a
   single provider. No second vendor in front of it.
2. **The audio is end-to-end encrypted in v1.** AES-256-GCM, container flag
   bit0. Keys live on the box and in the iPhone Keychain. The host stores and
   moves ciphertext and cannot play it.
3. **The iOS app is the only human-facing client.** No web UI, no accounts,
   no login page — identities stay the three bearer tokens of PROTOCOL.md.
   That was the server's original shape and it is kept.
4. **Host: Supabase, on the Pro plan, region Zurich (`eu-central-2`).** Edge
   Functions (the API), Postgres (metadata), a private Storage bucket (the
   audio), `pg_cron` + `pg_net` (the clock). Pro, not Free, because Free has
   no backups and pauses a project after 7 days without activity — a dead box
   plus a paused project is exactly when the "box is late" alert matters.
   Design in [SERVER-CONCEPT.md](../SERVER-CONCEPT.md).

Consequence of 2: **no server-side transcode.** The server cannot read the
audio, so it cannot convert it. The box has `ffmpeg` and plays whatever the
phone records; the protocol gains `codec = 3` (AAC-LC).

## Alternatives considered

| Host | Cost | For | Against |
| --- | --- | --- | --- |
| **Supabase Pro** — chosen | USD 25/month | Postgres; familiar; good dashboard; daily database backups; 100 GB of blobs; never pauses; a Zurich region | The price of not thinking about it. Auth and RLS-for-browsers go unused. Database backups do not cover Storage objects — hence the phone's copy (ADR 0018). US company on AWS |
| Supabase Free | 0 | Same stack | 1 GB of blobs, **no backups, pauses after 7 days without activity** |
| Cloudflare Workers + R2 + D1 | 0–5 USD/month | 10 GB free, never pauses, cron built in, no cold start | 10 ms CPU limit on the free plan; SQLite-flavoured D1; less familiar. The fallback if Supabase ever disappoints |
| **PocketBase on a small EU VPS** (Hetzner, ~EUR 4/month) | ~CHF 50/year | One Go binary, SQLite + files, EU company, everything in one place | A machine to patch and back up — what this ADR set out to avoid |
| **Firebase** | ~0 | FCM makes push trivial | Google; analytics SDKs by default; against the spirit of "no third-party analytics" |
| **CloudKit** | 0 | Apple-native, push built in | No server logic or scheduler — nothing can raise "the box is late"; awkward from a Linux box |
| **Pi at home** | 0 | Most private | The box-is-dead alert must not depend on a home router |
| **Vercel + Supabase** (first draft) | 0–25 | — | Two vendors for one small API; only made sense with a web UI |

With E2EE in place every one of these holds ciphertext, so the choice is
about availability, durability and upkeep — not about who can listen.

## Consequences

- "Nobody but our server is in the path" becomes "nobody in the path can
  *hear* it". ARCHITECTURE.md and PROTOCOL.md § Transport need that sentence
  changed, honestly.
- **PROTOCOL.md goes to v0.3 first** (list in the concept): encryption moves
  from Open to specified, `codec = 3`, `GET /messages`, `GET /device/status`,
  retention per ADR 0018.
- The iOS app must play Ogg Opus itself — the transcode-to-AAC escape hatch
  in `components/codec.md` is gone.
- Serverless has no long-running loop: the "box is late" alert runs from the
  host's cron, not from a Node process.
- The Fastify skeleton in `server/` is replaced by one Supabase Edge Function
  (Deno, Hono router). Its comments and endpoint list carry over. Protocol logic stays
  framework-free in `server/src/core/`, so changing host is a weekend.
- Lose the key, lose the archive. The key ceremony, iCloud Keychain sync and
  a paper copy become part of setup (`components/security-privacy.md` Q2).
- What the host still sees: that messages exist, when, how long, between
  which identities, and the box's telemetry. Not the audio. APNs pushes carry
  "New message" and an id — never content.
