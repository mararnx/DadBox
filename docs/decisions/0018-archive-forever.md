# ADR 0018 — Messages are archived forever

**Date:** 2026-09-21
**Status:** accepted (Marco, 2026-09-21)

## Context

PROTOCOL.md v0.2 deletes a message from the server 24 h after it is played.
That was a privacy measure for a server that could read the audio. It also
throws away the thing a parent will want most in ten years: the child's voice
at six.

With end-to-end encryption ([ADR 0017](0017-managed-hosting-e2ee.md)) the
server holds ciphertext it cannot play, so keeping it costs little privacy —
and at ~120 KB/min it costs almost no storage: an hour a month is under
100 MB a year.

## Decision

- **The server never deletes a completed message.** No 24 h clock, no expiry.
  `played` remains — it is the parent's feedback loop — but starts nothing.
- **The archive exists twice.** The server keeps the ciphertext; the iOS app
  keeps its own copy of every message it has fetched, so it is in the phone's
  backup too. One host failing, or one phone lost, loses nothing.
- **The box is not an archive.** Outbox: kept until the server confirms
  (`complete` → 2xx after a durable write and CRC match — [ADR 0010](0010-nothing-is-lost.md),
  unchanged). Inbox: removed after play, evictable under pressure, as before.
- The `expired` message state is unused; unplayed messages are still
  surfaced at 48 h, never reaped.
- Deleting is a deliberate act in the app, per message, by the parent it
  belongs to. The server then deletes the blob and keeps a tombstone row.

## Alternatives considered

- **24 h after played (v0.2)** — right for a server that can listen; wrong
  once it cannot, and irreversible by nature.
- **Archive on the phone only** — a lost or replaced phone without a good
  backup loses years. The server copy is cheap insurance.
- **Archive on the server only** — a free-tier host has no backups and an
  account can be closed. The phone copy is cheap insurance.

## Consequences

- **The key now guards everything ever said, not the last day's messages.**
  It syncs through iCloud Keychain (itself end-to-end encrypted), and a paper
  copy goes in a drawer. Lose every copy and the archive is noise.
- A key that leaks — e.g. from the box's SD card — exposes the archive to
  anyone who *also* has a parent token. The box therefore holds a token that
  can fetch **only its own inbox**, never history; and re-keying (new key
  going forward, old one kept on the phone for the archive) must be possible.
  `key_id` in the envelope exists for this.
- Storage is sized for decades: 10 GB ≈ 1,400 hours of 16 kbps Opus.
- The co-parent's one-page note (`components/security-privacy.md`, Consent)
  must say plainly that messages are kept, encrypted, and by whom they can be
  heard.
- Telemetry is not the archive: check-in history is still pruned at 30 days.
- PROTOCOL.md § Durability and retention, ARCHITECTURE.md § Retention and
  privacy, and `components/server.md` Q4 change with v0.3.
