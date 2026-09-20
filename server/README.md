# Server

Node + TypeScript + Fastify. Deliberately small.

```bash
npm install
npm run dev
```

## Job

1. Accept audio blobs from the box (via a Notehub route) and from the app.
2. Store them, briefly.
3. Wake the parent's phone with an APNs push.
4. Hold the device telemetry the app needs to tell *quiet* from *dead*.

That is all. No accounts, no user management, no web UI — one family, two
clients, hardcoded identities.

## Not blocked by hardware

Build this now, against the fake box in `../tools/`. Both this and the iOS app
can be finished before a single component arrives, which leaves the firmware as
the only genuine unknown on the day the parts land.

## Endpoints

See [../docs/PROTOCOL.md](../docs/PROTOCOL.md). All are stubs returning 501.

## Decisions still open

- **Where it runs.** Fly.io / Railway / a Pi at home. A Pi at home keeps a
  child's voice off other people's computers, at the cost of your uptime.
- **Blob storage.** Local disk is fine at this volume; S3-compatible if hosted.
- **Auth.** Notehub device identity may be enough for the box. The app needs
  something; a long-lived token in the Keychain is proportionate for one user.

## Non-negotiable

Encrypted at rest, TLS in transit, short retention after playback, and no
third-party analytics or speech services anywhere in the path.
