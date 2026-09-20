# iOS app

SwiftUI, native, APNs. [ADR 0004](../docs/decisions/0004-native-ios-app.md).

Not built yet — no Xcode project here. Create it when you start:
iOS app, SwiftUI, bundle id something like `com.<you>.dadbox`.

## Why native

Notification reliability is the product. A message from your child that you
notice six hours later defeats the whole device, and iOS web push is the wrong
place to economise. This app's real job is to be *loud and on time*.

## Screens

There are three, and it should be hard to add a fourth.

1. **Listen** — waiting messages, big play button, oldest first. Opens straight
   to the newest unplayed message from a push notification.
2. **Send** — hold to record, release to send. Same 5-minute cap as the box.
   Shows delivered / played state, because "did it arrive" is the question
   you'll actually have.
3. **Box** — battery, signal, last sync, queue depth, mute, quiet hours.
   This screen exists so a flat battery in a school bag surfaces as a fact
   rather than as a child who seems to have stopped messaging.

## Push

- APNs, with the alert loud enough to be noticed. Consider a distinct sound.
- Critical alerts are tempting and almost certainly wrong here — they need an
  Apple entitlement and would wake you at 3am for a voice message.
- Ship the "box hasn't checked in for N hours" alert early. It is the most
  important notification in the app, and it is not about messages.

## Setup needed

- Apple Developer account ($99/yr), or a free account and re-signing weekly.
- APNs key (.p8) + key id + team id, given to the server.

## Contract

[../docs/PROTOCOL.md](../docs/PROTOCOL.md). The app is a client of the same
protocol a second box would speak — nothing app-specific belongs in firmware.
