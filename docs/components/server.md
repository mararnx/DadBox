# Server

**Role.** Hold audio briefly, wake a phone immediately, and know whether the
box is alive.

## Current design

Node + TypeScript + Fastify. Stubbed endpoints in `server/src/index.ts`.
Blob storage, short retention, APNs push, telemetry, settings.

## Checked

- With a bare modem, the server gets simpler: the box speaks HTTPS to it
  directly. With a Notecard, it also needs a Notehub route handler and a
  Notehub API client for inbound. The stubs currently assume Notecard; they
  will change with that decision.
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
