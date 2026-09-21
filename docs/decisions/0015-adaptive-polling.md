# ADR 0015 — Adaptive polling, no SMS wake

**Date:** 2026-09-21
**Status:** accepted

## Context

Inbound latency was one number: `poll_minutes`, default 10. That is wrong in
both directions. When the child has just sent something, the parent usually
answers within minutes and ten minutes is a long time to a child sitting next
to a box. When nothing has happened since yesterday, ten minutes wakes the
modem 144 times a day for nothing.

Two facts reshape it: the box is **plugged in most of the time** (the battery
is for weekends and car rides), and a Pi cannot sleep, so the modem is the
only thing polling costs.

The user proposed: after sending, poll every minute for 1.5 h, then every
30 minutes — or wake the box by SMS instead.

## Decision

Three cadences, chosen by the box, parameters from the server:

| State | Modem | Check-in |
| --- | --- | --- |
| **On mains** | stays on | every `active_minutes` (1) |
| **On battery, conversation window open** | stays on | every `active_minutes` (1) |
| **On battery, idle** | off between check-ins | every `idle_minutes` (30) |

- A **conversation window** opens when the box finishes an upload or the
  child plays a message, and lasts `active_window_minutes` (90). Each such
  event restarts it. Both are things the child did with the box; a message
  merely *arriving* does not open one.
- Unplugging drops to the battery rules at once; plugging in goes to mains
  cadence at once. The check-in after any upload stays.
- Telemetry gains `next_checkin_s` so the server and the app know when the box
  is *late* rather than guessing from a fixed interval. The LINK LED rule
  becomes "within 2 × the current interval".
- Quiet hours change nothing here: they silence the chime, not the link.

Settings change from `poll_minutes` to a `poll` object
([PROTOCOL.md](../PROTOCOL.md)). The app exposes `idle_minutes` only.

## Alternatives considered

- **SMS wake.** Technically possible — Digital Republic data SIMs receive SMS
  and the A7670E can raise RI on one. Rejected:
  - The server would need an SMS gateway: a third party in the path
    ([ADR 0006](0006-bare-modem-not-notecard.md)), per-message cost, and an
    account to keep alive for years.
  - The modem must stay registered to hear the SMS, so it saves nothing over
    leaving the modem on and polling — which needs no one else.
  - SMS delivery is best-effort and unordered; polling would have to remain as
    the backstop anyway. Two mechanisms, one of them untestable from the Mac.
  - The SIM's number becomes an input anyone can text.
- **Long-poll / held connection on mains** — seconds instead of a minute.
  Worth doing later if a minute feels slow; carrier NAT timeouts and half-dead
  sockets make it the fussier option, and it changes nothing on battery.
- **Fixed 10 minutes** — see Context.
- **Window opened by inbound messages too** — a message arriving at 03:00
  would hold the modem on for 90 minutes while everyone sleeps. The child
  playing it opens the window; that is the moment a reply matters.

## Consequences

- Plugged in, a parent's message reaches the box in ≤ 1 minute, always.
- On battery, an idle box checks in 48 times a day instead of 144; a
  conversation costs ~90 min of registered modem (~20–30 mA at 5 V, ≈ 0.04 Ah)
  — noise against a 13 Ah pack.
- Worst-case inbound latency on battery, outside a conversation, is 30
  minutes. The app says when the next check-in is due.
- At one check-in a minute, a check-in must stay small: one TLS session kept
  alive, a body of a few hundred bytes. ~1,400 requests a day is nothing for
  Flat 1 or the server, but the endpoint must not do per-request work that
  scales (no push on every check-in, no log line at info).
- The mains/battery distinction needs a trustworthy "external power present"
  signal from the power board, not just "charging" (a full pack on mains is
  not charging). Telemetry keeps `charging` and adds `mains`.
