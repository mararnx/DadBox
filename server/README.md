# Server

**Supabase, Pro plan, Zurich** ([ADR 0017](../docs/decisions/0017-managed-hosting-e2ee.md)):
one Edge Function for the API, Postgres, a private Storage bucket, `pg_cron`.
Design: [../docs/SERVER-CONCEPT.md](../docs/SERVER-CONCEPT.md). Deliberately small.

Project `dadBox`, ref `cjwmemfxvsrlqncieseq`, `eu-central-2`. The CLI runs
through npm — Homebrew on this Mac belongs to another user account:

```bash
npx supabase@2.117.0 <command>     # from server/, where supabase/ lives
```

`supabase/` is linked to that project. The database password, service-role
key and APNs key never enter this repo.

## Layout

```
supabase/functions/api/index.ts      routes: parse → core → respond
supabase/functions/api/core/         the protocol's rules and the container — no I/O, no framework
supabase/functions/api/apns.ts       push, straight to Apple; a logged no-op until the APNs secrets exist
supabase/migrations/                 schema · RLS on, zero policies · checkin() · pg_cron jobs
```

## Test, on the Mac

```bash
npm test          # core rules + the shared vectors in docs/testvectors — Node only, no install
npm run check     # deno check + lint of the whole function
```

Nothing is installed into this folder: it lives in a synced drive, so Deno and
the Supabase CLI come through `npx` with their caches elsewhere.

## Deploy

Each step changes the live project. The database password is asked for and
never stored here.

```bash
npm run supabase -- db push                          # the migration
npm run supabase -- functions deploy api --use-api   # --use-api: no Docker needed
npm run supabase -- secrets set TICK_SECRET=<random>
```

Then, once, in the SQL editor — the clock's address and its secret go into Vault:

```sql
select vault.create_secret('https://cjwmemfxvsrlqncieseq.supabase.co/functions/v1/api/tick', 'dadbox_tick_url');
select vault.create_secret('<the same random TICK_SECRET>', 'dadbox_tick_secret');
```

Tokens: `python3 ../tools/mint_token.py box` prints a token once and the SQL
that stores its hash. APNs secrets (`APNS_KEY_P8`, `APNS_KEY_ID`,
`APNS_TEAM_ID`, `APNS_TOPIC`) follow when the Apple Developer account exists.
Exercise everything with [`../tools/fakebox`](../tools/fakebox/fakebox.py);
`fakebox.py --as parent-a setup-code` prints what the iOS app's setup screen asks for.

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

See [../docs/PROTOCOL.md](../docs/PROTOCOL.md) v0.3. All implemented and, on 2026-09-22, exercised against the live project with the fake box: dropped-link resume, shuffled and repeated chunks, Range download, mute with who-set-what, `played` flowing back, the box-late alert raising once and clearing. Not yet: APNs (no key yet).

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
