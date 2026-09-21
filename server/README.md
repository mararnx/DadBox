# Server

**Supabase, Pro plan, Zurich** ([ADR 0017](../docs/decisions/0017-managed-hosting-e2ee.md)):
one Edge Function for the API, Postgres, a private Storage bucket, `pg_cron`.
Design: [../docs/SERVER-CONCEPT.md](../docs/SERVER-CONCEPT.md). Deliberately small.

> The Fastify skeleton in `src/` predates that decision and is to be replaced
> by `supabase/functions/api/`. Nothing below the stubs is implemented.

## Job

1. Accept audio in resumable 32 KB chunks from the box and from the app.
2. Store it — as ciphertext it cannot play, forever ([ADR 0018](../docs/decisions/0018-archive-forever.md)).
3. Wake the parent's phone with an APNs push.
4. Answer the box's check-in with settings and an inbox summary.
5. Hold the telemetry the app needs to tell *quiet* from *dead*, and raise
   the "no check-in for N hours" alert — the most important one in the system.

The box speaks HTTPS directly (ADR 0006); there is no relay service, and
nobody in the path — the host included — can read a message.

That is all. No accounts, no user management, no web UI — one family, two
clients, hardcoded identities.

## Not blocked by hardware

Build this now, against the fake box in `../tools/`. Both this and the iOS app
can be finished before a single component arrives, which leaves the firmware as
the only genuine unknown on the day the parts land.

## Endpoints

See [../docs/PROTOCOL.md](../docs/PROTOCOL.md). All are stubs returning 501.

## Decided

- **Where it runs.** Supabase Pro, Zurich. Nothing else in front of it.
- **Blob storage.** A private Storage bucket; assembled containers only.
  Chunks wait in Postgres until `complete`.
- **Auth.** Long-lived bearer token per identity, stored as SHA-256. The box's
  token reaches only its own inbox. Supabase Auth is not used; the function is
  deployed with `verify_jwt = false` and checks our tokens itself.
- **Encryption.** End to end. The server checks the CRC and never holds a key.

Still open: [../docs/components/server.md](../docs/components/server.md) and
the questions at the end of the concept.

## Non-negotiable

End-to-end encrypted, TLS in transit, RLS on every table with no policies,
nothing ever deleted, 2xx on `complete` only after a durable write and CRC
match, and no third-party analytics or speech services anywhere in the path.
