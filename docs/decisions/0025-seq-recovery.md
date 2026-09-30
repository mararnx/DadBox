# ADR 0025 — A restarted seq counter recovers; one refused message never stops check-ins

**Date:** 2026-09-30
**Status:** accepted 2026-09-30. Implemented in PROTOCOL.md, the server, the
simulator's server and the box.

## Context

`seq` is a per-sender counter, the ordering key of every message. The box
keeps it in `/data/seq`. The 2026-09-30 re-flash rebuilt `/data` without that
file, so the box started again at 1. The server already held a seq 1 from the
box, and a test message sent over LTE got `409 seq already used by another
message`.

Two failures followed from that one answer:

1. **The message could never be sent.** The box retried the same metadata
   every round, forever. Had it been a child's recording, it would have sat
   in the outbox, safe on disk but never reaching the parent.
2. **The whole box went offline.** A round stopped at the first failed
   upload, so it never reached the check-in. For ten minutes the server saw
   no check-ins and Record would have blinked "not ready" (ADR 0024), all
   because of one message.

The app already avoids the first failure: `GET /messages` returns `max_seq`
and a reinstalled app continues from it. The box had nothing equivalent.

## Decision

- **The check-in response carries `max_seq`**, the highest seq the server
  holds from the box. The box raises its counter to at least that number, so
  a re-flashed box's first recording gets a fresh seq.
- **The seq-conflict `409` carries `max_seq` too.** A box that already has a
  recording in its outbox when it comes back (the round uploads before it
  checks in) raises its counter, gives that message the next seq, persists it
  and sends the metadata again. This is safe because the server has never
  seen that id, and because seq is metadata only: it is not in the sealed
  container, its AAD or its crc. Several such messages are renumbered in
  their original order, so they stay in order.
- **A server's 4xx on one message does not end the round.** The box keeps
  the message (the outbox is never evicted, ADR 0010), logs it, uploads the
  rest and still checks in. Only a transport failure or a 5xx ends a round,
  because then nothing else would get through either.

## Consequences

- A message that the server refuses for good stays in the outbox, and the
  telemetry's outbox count shows it. The app can say "1 message stuck" rather
  than "box offline". Clearing it is still a person's decision.
- Seq numbers can have gaps (the counter jumps past `max_seq`). Seq only
  orders messages; nothing counts on consecutive numbers.
- `/data/seq` is still worth keeping in backups, but losing it is no longer a
  fault.
- A server without this change still works with a box that has it: the box
  sees no `max_seq`, treats the 409 as a refused message and goes on checking
  in.
