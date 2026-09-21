# Server

**Role.** Hold audio briefly, wake a phone immediately, and know whether the
box is alive.

## Current design

> **Decided 2026-09-20:** box speaks HTTPS directly — no Notehub handler. Resumable 32 KB chunks, `/device/checkin` returns settings + inbox. Two parent identities in the protocol, one built ([ADR 0008](../decisions/0008-two-parents-later.md)). Retention: 24 h after played; unplayed surfaced at 48 h (Q4).

> **Decided 2026-09-21:** one managed host, audio end-to-end encrypted so the host cannot play it, iOS the only client — no web UI, no accounts ([ADR 0017](../decisions/0017-managed-hosting-e2ee.md)). **Messages are archived forever**; the 24 h deletion above is withdrawn ([ADR 0018](../decisions/0018-archive-forever.md)). The box still deletes from its outbox only on the server's 2xx to `complete`. Concept: [SERVER-CONCEPT.md](../SERVER-CONCEPT.md). Answers Q1 and Q3–Q5 below. **Host: Supabase, Pro plan, Zurich** — Edge Functions, Postgres, private Storage, `pg_cron`; the scheduler is `pg_cron`, not an in-process loop. PROTOCOL.md is at v0.3.

One Supabase Edge Function (Deno + TypeScript) speaking PROTOCOL.md v0.3;
Postgres for metadata, a private Storage bucket for ciphertext kept forever,
APNs push, telemetry, settings. The Fastify stubs in `server/src/index.ts`
predate this and are to be replaced — their endpoint comments carry over.

## Checked

- The box speaks HTTPS to the server directly (ADR 0006), so there is no
  Notehub route handler and no third-party inbound path. The stubs in
  `server/src/index.ts` reflect this.
- Resumable uploads: `PUT /messages/:id/chunks/:seq` with idempotent seq, and
  `GET /messages/:id/upload-state` on boot so the box knows where to resume.
  Simple, and works over a link that drops every 30 seconds.
- The "no check-in for N hours" alert needs a scheduler. A single cron-style
  loop inside the process is fine at this scale.
- Hosting decides who else can see the child's voice. A Pi at home is the
  most private and the least available. A small VPS in the EU is a
  reasonable middle. Either way: encrypt at rest, and prefer that the server
  never holds a key that can decrypt the audio (see
  [security-privacy.md](security-privacy.md)).
- Two parents (review §8) is mostly a server question: two device tokens for
  push, and a `to` field on the message.

## Questions

1. **Where does it run?** Home Pi, EU VPS, or a managed platform? Suggest a
   small EU VPS with disk encryption; home Pi only if the box's uptime is
   tolerable at "whenever the home internet is up".
2. **Two parents?** Does the co-parent get push and the ability to send? If
   yes, does the child's message go to *one* parent (routed by which house the
   box is in) or to both?
3. **Auth** — long-lived per-device tokens in NVS / Keychain, rotated never?
   For one family that is proportionate. Or short-lived tokens with refresh,
   which is more correct and more to build.
4. **Retention numbers** — delete N hours after `played`? Suggest 24 h. And
   unplayed messages: never expire? 30 days? A message the parent sent that
   the child never played is a signal the app should show, not silently reap.
5. **Backups** — none, deliberately? Audio is ephemeral by design; settings
   and tokens are the only state worth keeping.
6. **Fake box** — `tools/fakebox` is the first thing to build. Does it need to
   simulate a flaky link (drops mid-chunk), or just the happy path first?
