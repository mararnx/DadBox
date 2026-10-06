# ADR 0015 — Adaptive polling, no SMS wake

**Date:** 2026-09-21
**Status:** accepted — while the box has no battery ([ADR 0019](0019-mains-first-battery-deferred.md)) only the mains row applies
— the mains row is revised by the doorbell, [ADR 0021](0021-doorbell.md)
— revised 2026-10-06: the first 5 minutes after use poll every 15 s (see below)
— revised 2026-10-06: the travel lock is the idle cadence, whatever the power (see below)

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

## Revision 2026-10-06: just used

On the bench the doorbell was off and an answer took up to a minute to
reach a child waiting at the box. For **5 minutes after an upload completes
or a message plays**, the box checks in every **15 s**, on mains or battery,
doorbell joined or not: about 20 extra check-ins of a few hundred bytes per
use, while the modem is on anyway. The numbers are constants on the box
(`JUST_USED_S`, `JUST_USED_POLL_S`), not settings. The link counts as up
while the last good check-in is within 2 × the interval but never less
than 2 minutes, so the faster cadence does not make Record blink sooner.

## Revision 2026-10-06: locked means idle

The box sometimes runs from a power bank in a bag with the travel lock on.
A power bank looks exactly like mains (no gauge, ADR 0019), so the box kept
the modem registered, the doorbell open and checked in every minute.

**While the travel lock is on, the box uses the battery's idle row on any
power:** modem off between check-ins, a check-in every `idle_minutes`, the
doorbell closed. It beats the just-used rule too: nobody can play a reply in
a bag. Locking does not delay an upload already queued — that round runs
first, failures back off as always. **Unlocking checks in at once** and
reopens the doorbell, so what arrived meanwhile is there within seconds. The
link counts as up for 2 × the interval promised at the last good check-in
until a round fails, so Record does not blink "not ready" while that first
check-in runs.

The app already sees `locked` and `next_checkin_s` in telemetry; the server's
*late* rule follows `next_checkin_s`, so a locked box is not late at 2 min.
The saving is unmeasured: the Pi itself is most of the ~0.6 W. Not done: the
button lights stay as they are (user decision), and the Pi keeps both cores.

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
  Taken up as the doorbell in [ADR 0021](0021-doorbell.md). Worth doing later if a minute feels slow; carrier NAT timeouts and half-dead
  sockets make it the fussier option, and it changes nothing on battery.
- **Fixed 10 minutes** — see Context.
- **Window opened by inbound messages too** — a message arriving at 03:00
  would hold the modem on for 90 minutes while everyone sleeps. The child
  playing it opens the window; that is the moment a reply matters.

## Consequences

- Plugged in, a parent's message reaches the box in ≤ 1 minute, always.
- On battery, an idle box checks in 48 times a day instead of 144; a
  conversation costs ~90 min of registered modem (~20–30 mA at 5 V, ≈ 0.04 Ah)
  — noise against a ~36 Wh pack.
- Worst-case inbound latency on battery, outside a conversation, is 30
  minutes. The app says when the next check-in is due.
- At one check-in a minute, a check-in must stay small: one TLS session kept
  alive, a body of a few hundred bytes. ~1,400 requests a day is nothing for
  Flat 1 or the server, but the endpoint must not do per-request work that
  scales (no push on every check-in, no log line at info).
- The mains/battery distinction needs a trustworthy "external power present"
  signal from the power board, not just "charging" (a full pack on mains is
  not charging). Telemetry keeps `charging` and adds `mains`.
