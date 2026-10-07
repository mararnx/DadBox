# ADR 0027 — A waiting message is Time Sensitive and stays on the lock screen

**Date:** 2026-10-07
**Status:** accepted (Marco, 2026-10-07). Server and app written; not yet
built in Xcode, not yet deployed. Reverses "no Time Sensitive" in
[ios/DESIGN.md](../../ios/DESIGN.md) § Notifications.

## Context

The app exists to be *loud and on time* ([ios/README.md](../../ios/README.md)).
In use it is not: the phone is on silent most of the day, a `message` push is
one haptic and a banner, and messages from the box were being found hours
later. A missed buzz leaves nothing behind that says "still waiting".

The first design ruled Time Sensitive out so a voice message could never beat
a Sleep focus. That protected the night at the cost of the day.

## Decision

1. **`message` is `interruption-level: time-sensitive`.** It breaks through
   a Focus and the scheduled summary, and stays on the lock screen for an
   hour. The app gains the `com.apple.developer.usernotifications.time-sensitive`
   entitlement; without it iOS delivers the same push as `active`, so the
   server may go first. The other kinds keep their levels.
2. **A message to a parent starts a Live Activity** — "Message waiting ·
   12 min" on the lock screen and in the Dynamic Island — by ActivityKit
   push-to-start, so it appears with the app not running.
3. **The server only starts; the app ends.** The app ends the activity when
   nothing from the box is left unheard. No update or end pushes, so no
   per-activity tokens travel to the server. One activity at a time: no
   start while another message from the last 8 h is unplayed.
4. **It carries an id and a second.** `attributes.id` (which message a tap
   opens) and `content-state.since` (upload time, Unix seconds). No content,
   no name ([ADR 0017](0017-managed-hosting-e2ee.md)); the waiting time is
   counted on the phone.

## Alternatives considered

- **Critical Alerts** — the only thing that sounds on a silent phone. Needs
  an entitlement Apple grants for health and safety, and would wake a parent
  at 3 am for a voice message. Still no.
- **Re-notify every few minutes until played** — works without an app
  change, but it is nagging by design; the Live Activity says the same thing
  without buzzing. Could be added later on the existing `/tick`.
- **A second channel (SMS with Emergency Bypass)** — the most reliable way
  to make sound on silent, at the price of a third party seeing that a
  message exists. Not now.
- **Update and end by push** — exact counts and an activity that clears
  itself on every device, but the app must be woken in the background to
  forward each activity's token. Fragile for one phone.

## Consequences

- Time Sensitive still makes **no sound on a silent phone** — it changes
  what a Focus lets through and how long the banner stays, not the ringer.
- A Sleep focus now lets a message through unless that Focus has *Time
  Sensitive Notifications* switched off. Quiet hours on the box are unchanged.
- iOS ends a Live Activity after 8 h (and clears it 4 h later). A message
  unheard for longer than that is back to being a notification.
- A message played only part-way is still unheard, so its activity stays
  and holds back the next one's.
- The app grows a third target, `DadBoxLive` (WidgetKit).
