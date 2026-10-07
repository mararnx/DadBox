# iOS app

SwiftUI, native, APNs. [ADR 0004](../docs/decisions/0004-native-ios-app.md).

First build runs in the simulator. What exists and what doesn't:
[DESIGN.md § Built so far](DESIGN.md#built-so-far).

```
DadBoxKit/          protocol logic, no UI — container, envelope, API client, archive store
DadBox/             the app — SwiftUI
DadBox.xcodeproj    folder-synchronised: new files in DadBox/ need no project edit
Config/             Info.plist additions, entitlements
```

```bash
cd ios/DadBoxKit && swift test
```

```bash
open ios/DadBox.xcodeproj
```

Run the `DadBox` scheme on a simulator with the launch argument `-demo`, or tap
*Look around with demo data* on the setup screen. If `swift` or `xcodebuild`
complain about the Command Line Tools, prefix them with
`DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer`, or switch for good
with `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer`.

Before it runs on the iPhone: set the team and a real bundle id in the target's
Signing settings (the placeholder is `ma.arnold.dadbox.app`).

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
- A message is Time Sensitive and stays on the lock screen as a Live Activity
  until it is heard ([ADR 0027](../docs/decisions/0027-time-sensitive-and-live-activity.md)).
- Critical alerts are tempting and almost certainly wrong here — they need an
  Apple entitlement and would wake you at 3am for a voice message.
- Ship the "box hasn't checked in for N hours" alert early. It is the most
  important notification in the app, and it is not about messages.

## Setup needed

- Apple Developer account — paid membership since 2026-09-22, Team ID `N94V936YCU` (a free team cannot use APNs at all).
- Xcode. The logic package (`DadBoxKit`) builds and tests with the Command Line Tools alone.
- APNs key (.p8) + key id + team id, given to the server.

## Contract

[../docs/PROTOCOL.md](../docs/PROTOCOL.md). The app is a client of the same
protocol a second box would speak — nothing app-specific belongs in firmware.
