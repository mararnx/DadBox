# iOS app

SwiftUI, native, APNs. [ADR 0004](../docs/decisions/0004-native-ios-app.md).

Not built yet — no Xcode project here. Create it when you start:
iOS app, SwiftUI, bundle id something like `com.<you>.dadbox`.

## Why native

Notification reliability is the product. A message from your child that you
notice six hours later defeats the whole device, and iOS web push is the wrong
place to economise. This app's real job is to be *loud and on time*.

## Screens

Two, and it should be hard to add a third. Full design: [DESIGN.md](DESIGN.md).

1. **Conversation** — one timeline, both directions, the whole archive above
   it. Tap-tap-review-send recorder at the bottom. Each message you sent says
   sent / on the box / **played 19:12**, because "did it arrive" is the
   question you'll actually have. A push opens it at the new message; nothing
   autoplays.
2. **Box** — battery, signal, last and next check-in, queue depth, faults in
   words, mute, quiet hours, the key. This screen exists so a flat battery in
   a school bag surfaces as a fact rather than as a child who seems to have
   stopped messaging.

## Push

- APNs, with the alert loud enough to be noticed. Consider a distinct sound.
- Critical alerts are tempting and almost certainly wrong here — they need an
  Apple entitlement and would wake you at 3am for a voice message.
- Ship the "box hasn't checked in for N hours" alert early. It is the most
  important notification in the app, and it is not about messages.

## Setup needed

- Apple Developer account — paid membership exists (a free team cannot use APNs at all).
- Xcode. The logic package (`DadBoxKit`) builds and tests with the Command Line Tools alone.
- APNs key (.p8) + key id + team id, given to the server.

## Contract

[../docs/PROTOCOL.md](../docs/PROTOCOL.md). The app is a client of the same
protocol a second box would speak — nothing app-specific belongs in firmware.
