# ADR 0010 — Nothing a child recorded is ever lost

**Date:** 2026-09-20
**Status:** accepted — on the Pi ([ADR 0014](0014-raspberry-pi-zero-2w.md)) the capture streams to disk as it happens, so item 2's 30 s checkpoint becomes continuous; the outbox is a writable `/data` partition beside a read-only root

## Context

The box will be offline — in a bag, in a basement, in a dead spot — and a
child will record into it anyway. The earlier storage plan said "flash full →
oldest-first eviction". That is a way to lose a message.

## Decision

A recording that received its *got it* pulse is on flash and stays there until
the server has durably confirmed it. Specifically:

1. The pulse is given only after the container is written and fsynced. No
   pulse, no promise.
2. During capture, the PSRAM buffer is checkpointed to flash every 30 s, so a
   power loss mid-story costs at most 30 s.
3. The **outbox is never evicted**. The inbox may be — the server still has
   those and the box re-downloads.
4. A message leaves the outbox only after `complete` returns 2xx, and the
   server returns 2xx only after a durable write and a CRC match.
5. Retries back off and never give up. On boot, every interrupted upload
   resumes from the server's `upload-state`.
6. Ordering uses a monotonic `seq` from NVS, not the clock. A box with no RTC
   battery that was powered off does not know the time until it next connects.
7. On reconnect, telemetry reports how long the box was offline and what
   accumulated, so the app can tell the parent.

## Alternatives considered

- **Evict oldest** — simplest; loses messages. Rejected.
- **Stream every sample to flash** — makes even a mid-recording power loss
  lossless, at the cost of continuous flash wear. 30 s checkpoints are the
  compromise; revisit if the measured wear is fine.

## Consequences

- Capacity becomes a real number: ~10 MB of flash after the app and its OTA
  slot → ~20 minutes of ADPCM, ~3 h once Opus lands. That is a lot of offline
  messages for one child, and also finite.
- Full is the one case where "never lost" and "always accept" collide: the
  lid still records, and there is nowhere to put it. The fault pattern shows
  at 80 %. Whether the headroom is enough, or whether *never* needs a microSD
  slot, is an open question in `components/storage-queue.md`.
- Below 5 % battery the box sleeps and the lid does nothing. That is a
  refusal, not a loss — nothing was recorded — and the status LEDs show it.
- The server has to be as careful as the box: durable before 2xx, unplayed
  messages never reaped.
