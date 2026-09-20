# Server

Node + TypeScript + Fastify. Deliberately small.

```bash
npm install
npm run dev
```

## Job

1. Accept audio in resumable 32 KB chunks from the box and from the app.
2. Store it, briefly.
3. Wake the parent's phone with an APNs push.
4. Answer the box's check-in with settings and an inbox summary.
5. Hold the telemetry the app needs to tell *quiet* from *dead*, and raise
   the "no check-in for N hours" alert — the most important one in the system.

The box speaks HTTPS directly (ADR 0006); there is no Notehub or other third
party in the path.

That is all. No accounts, no user management, no web UI — one family, two
clients, hardcoded identities.

## Not blocked by hardware

Build this now, against the fake box in `../tools/`. Both this and the iOS app
can be finished before a single component arrives, which leaves the firmware as
the only genuine unknown on the day the parts land.

## Endpoints

See [../docs/PROTOCOL.md](../docs/PROTOCOL.md). All are stubs returning 501.

## Decisions still open

See [../docs/components/server.md](../docs/components/server.md).

- **Where it runs.** A small EU VPS with disk encryption is the suggested
  middle; a Pi at home is more private and less available.
- **Blob storage.** Local disk is fine at this volume.
- **Auth.** Long-lived bearer token per identity (box, parent-a, and the
  reserved parent-b). Proportionate for one family.
- **On-device encryption.** Recommended; if adopted the server stores
  ciphertext it cannot play, and hosting becomes a pure availability question.

## Non-negotiable

Encrypted at rest, TLS in transit, short retention after playback, and no
third-party analytics or speech services anywhere in the path.
