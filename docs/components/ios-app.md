# iOS app

**Role.** Be loud and on time. Then be honest about the box.

## Current design (ADR 0004)

> **Decided 2026-09-20:** one parent in v1; the app is built so a second identity is a config change, not a rewrite ([ADR 0008](../decisions/0008-two-parents-later.md)). Server-side transcode from whatever iOS records. Box-offline alert ships in M1.

SwiftUI, APNs. Three screens: Listen, Send, Box.

## Checked

- Push reliability is the product. Standard alerts are enough; Critical Alerts
  need an Apple entitlement and would wake the parent at 3 am for a voice
  message — wrong tool.
- The "box hasn't checked in" alert is the most important notification in the
  system and is *not* about a message. It should exist by M1.
- Recording on iOS: AVAudioRecorder to AAC is trivial; producing Opus for the
  box needs a small library or server-side transcode. Server-side transcode is
  simplest: the app uploads whatever iOS makes, the server produces what the
  box wants. That also keeps codec choice off the phone.
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
