# iOS app

**Role.** Be loud and on time. Then be honest about the box.

## Current design (ADR 0004)

> **Decided 2026-09-20:** one parent in v1; the app is built so a second identity is a config change, not a rewrite ([ADR 0008](../decisions/0008-two-parents-later.md)). Box-offline alert ships in M1. ~~Server-side transcode from whatever iOS records~~ — withdrawn: with E2EE the server cannot transcode ([ADR 0017](../decisions/0017-managed-hosting-e2ee.md)); the app uploads AAC-LC (`codec = 3`) and plays the box's Ogg Opus natively.
>
> **Decided 2026-09-21:** one conversation timeline instead of three tabs; tap-tap-review-send; 5-minute cap; no autoplay from a push; no widget or quick-record, ever; English only; archive both directions forever with the key in iCloud Keychain ([ADR 0018](../decisions/0018-archive-forever.md)); paid developer account exists. Design: [ios/DESIGN.md](../../ios/DESIGN.md). Answers Q2–Q7 below; Q1 stands as suggested (own thread, own key).

SwiftUI, APNs. Two screens — Conversation and Box — plus a one-time setup.

## Checked

- Push reliability is the product. Standard alerts are enough; Critical Alerts
  need an Apple entitlement and would wake the parent at 3 am for a voice
  message — wrong tool.
- The "box hasn't checked in" alert is the most important notification in the
  system and is *not* about a message. It should exist by M1.
- Recording on iOS: AVAudioRecorder to AAC-LC 16 kHz mono. The box decodes it
  with `ffmpeg`; nothing transcodes in between (ADR 0017).
- Playing the box's Ogg Opus: `AVAudioPlayer` opened a standard Ogg Opus file
  on macOS 26.4 (checked 2026-09-21) — no demuxer or codec library needed.
  Confirm on the iPhone.
- Background upload matters: a parent records in a lift, puts the phone away,
  and the message must still go. `URLSession` background configuration.
- A second parent (review §8) doubles the app users but not the app — same
  build, a different identity at first launch.

## Questions

1. **Two parents?** Same app, two identities? Can each see the other's
   messages to the child, or only their own? (Suggest: only their own — this
   is not a shared inbox.)
2. **What does "played" look like?** A tick? A timestamp — "played 17:42"?
   For a parent this is the *whole* feedback loop; get it right.
3. **Send from the lock screen / a widget?** Hold-to-record from a widget is
   the difference between "I use it every evening" and "I open the app
   sometimes".
4. **Recording length in the app** — same 5-minute cap as the box, or shorter
   for the child's attention span? Suggest 2 min from the parent side; the
   child can't skip.
5. **Live Activity** while a message is uploading / until it's played?
   Nice, not needed.
6. **Which alerts, exactly?** New message (loud). Box offline > N hours
   (loud). Battery < 20% (quiet). Muted by other household (quiet, once).
   Message unplayed after 48 h (quiet). Anything else?
7. **Free vs paid Apple account** — the 7-day re-sign is a real chore; will
   this actually get done weekly, or is the $99 cheaper than the nagging?
