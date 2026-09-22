# ADR 0021 — The doorbell: a ring that carries nothing

**Date:** 2026-09-22
**Status:** proposed — revises the mains and conversation-window rows of
[ADR 0015](0015-adaptive-polling.md); battery-idle is unchanged

## Context

On mains the box checks in every minute ([ADR 0015](0015-adaptive-polling.md)).
A parent's reply therefore reaches the child in up to 60 s, and the box makes
~1,440 check-ins a day to learn, almost every time, that nothing happened.

The user asked whether the box can receive push instead. It cannot, in the
usual sense: it sits behind carrier NAT on a data SIM, so nothing on the
internet can open a connection *to* it, and there is no APNs for a Linux box.
Anything that feels like push is the box holding a connection open and the
server speaking down it.

That connection is the fragile part. Carrier NAT drops idle flows after
minutes; LTE sockets die half-open without either end noticing. A design that
*depends* on the socket inherits all of that. A design that merely *benefits*
from it does not.

## Decision

**The server rings a doorbell. The ring carries nothing. The box answers the
door with an ordinary check-in.**

```
  parent sends ──► complete ──► messages.state = 'uploaded' ──┐  one transaction
                                                               ├─► realtime.send('{}', 'ring', topic)
  parent PATCHes settings ─────► settings row updated ────────┘  (broadcast only after commit)

  box ◄── wss, Supabase Realtime, topic doorbell:<128 random bits> ── "ring" {}
   └──► the same POST /device/checkin as always ──► inbox, settings ──► chime
```

1. **The ring is empty.** Event `ring`, payload `{}`. No id, no kind, no
   count. Everything the box learns, it learns from the authenticated
   check-in, exactly as today.
2. **The database rings, not the Edge Function.** A trigger on `messages`
   (to `box`, `uploading` → `uploaded`) and on `settings` calls
   `realtime.send()`. It is part of the same transaction, and Realtime
   broadcasts only what has committed: **the bell cannot ring for a message
   that is not yet durable**, and no code path can forget to ring.
3. **Every (re)connect is a knock.** The first thing the box does after
   joining the channel is check in. A ring lost while the socket was down is
   therefore never lost, only answered at the reconnect.
4. **The socket earns its place or steps aside.** "Connected" means joined
   and answering heartbeats, not "TCP open". Heartbeat every 25 s (also what
   keeps carrier NAT open); no reply in 10 s → the socket is dead, closed,
   and retried with the link worker's backoff (5 s · 2ⁿ, ≤ 5 min).
5. **The cadence follows the doorbell.** While it is connected, the timer
   check-in stretches to `poll.backstop_minutes` (10) — it exists for
   telemetry, liveness and a server that forgot to ring. While it is not,
   the box polls every `active_minutes` (1), exactly as ADR 0015 says today.
6. **The server can switch it off by omitting one field.** The check-in
   response carries `doorbell: { url, topic }` or nothing. No field, no
   socket: the box is an ADR 0015 box. The topic can be rotated at any
   check-in.
7. **Rings are rate-limited by the box.** At most one ring-triggered round
   per 5 s; rings during a round coalesce into one more round (the link
   worker's existing wake flag already does this).
8. **Battery-idle is untouched.** The modem is off between check-ins, so
   there is no socket. The doorbell opens whenever the modem is on anyway —
   mains, or a conversation window on battery.

| Box state | Modem | Doorbell | Timer check-in |
| --- | --- | --- | --- |
| Mains, or battery in a conversation window — doorbell joined | on | open | `backstop_minutes` (10) |
| Mains, or battery in a conversation window — doorbell not joined | on | reconnecting | `active_minutes` (1) |
| Battery, idle | off between check-ins | closed | `idle_minutes` (30) |

Plus, in every row: a check-in at once after a ring, a doorbell join, an
upload, a played message, and `dadboxctl checkin`.

### Why an empty ring on a public channel is safe

The channel is a Supabase Realtime *public* channel on an unguessable topic,
reached with the project's publishable key. It needs no trust, because it
carries nothing:

- **Forged rings** make the box check in more often, at most every 5 s,
  over an authenticated request that returns only what the box may see.
- **Missed rings** leave the box exactly where ADR 0015 already puts it.
- **An eavesdropper who learns the topic** learns *that* something changed
  for the box, and when — never what, never from whom. The topic lives only
  in Vault and in the box's `/data`, and a check-in can rotate it.

No failure of the doorbell can lose a message, deliver one to the wrong
place, or show the child anything. The worst case is today.

## Alternatives considered

- **Keep polling every minute (ADR 0015).** Still the fallback, and still
  correct. It is 1,440 requests a day to deliver a few messages ~30 s late
  on average.
- **Socket only, no timer.** Settings, telemetry and the `box_late` alert all
  ride on check-ins, and a half-open socket can look healthy for a long time.
  The backstop is what makes the socket optional.
- **Rings that carry the message id, or the settings.** Tempting and
  pointless: the box has to check in anyway to get the audio URL and verify
  it, and anything in the ring is something the channel must then protect.
- **Private Realtime channel with a minted JWT.** Supabase private channels
  authorise through Supabase Auth and RLS on `realtime.messages`; the box
  would need a JWT minted by our function and refreshed before expiry. More
  moving parts to guard a channel with nothing in it. Revisit if the topic
  leaking ever matters.
- **Edge Function WebSocket or HTTP long-poll.** Edge Functions have a
  wall-clock cap of minutes and no pub/sub between invocations; we would be
  rebuilding Realtime, worse.
- **MQTT broker.** A third party in the path ([ADR 0006](0006-bare-modem-not-notecard.md)).
- **SMS wake.** Rejected in [ADR 0015](0015-adaptive-polling.md) and still
  rejected: gateway account, per-message cost, a number anyone can text.

## Consequences

- **Parent → child on mains: seconds**, not up to a minute. Settings changed
  in the app (quiet hours, volume) land on the box as fast.
- **~10× fewer check-ins**: 144 a day instead of 1,440, and the Edge Function
  invocations with them. Heartbeats cost ~3,500 small frames a day on a flat
  data plan.
- **`box_late` fires later**: at 2 × `next_checkin_s` = 20 min instead of
  2 min while the doorbell is joined. A box that drops its socket falls back
  to 1-minute polling and reports that in `next_checkin_s`, so a real outage
  is still caught; a blip no longer pages anyone.
- **Telemetry gains `doorbell: true | false`** so the app can say "instant"
  or "every minute", and so a doorbell that never joins in the field is
  visible to an adult.
- **One new dependency on the box**: a small synchronous WebSocket client
  (`websocket-client`, pure Python). One new server piece: a trigger and two
  Vault secrets. Realtime being down degrades to ADR 0015, nothing more.
- **The simulator** gets an in-process doorbell next to its fake server, so
  every rule above is testable on the Mac.

## To verify — on the bench, before this is accepted

1. `realtime.send()` from a trigger reaches a Python client on a public
   channel of project `dadBox`, and only after commit.
2. Public channels are allowed in the project's Realtime settings.
3. Over the SIM7670G on the Digital Republic SIM: does a 25 s heartbeat keep
   the socket up, how many reconnects a day, and how long from `complete` to
   the chime. Record it in `docs/BUILD-LOG.md`.
4. Whether Realtime counts heartbeats against the Pro message quota (5 M a
   month; one box uses ~0.1 M even if it does).
