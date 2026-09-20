# ADR 0004 — Native iOS app, not a PWA

**Date:** 2026-09-20
**Status:** accepted — amends [ADR 0003](0003-one-box-plus-app.md)

## Context

ADR 0003 chose a phone web app for the parent end. The deciding requirement
turns out to be notification reliability: a message from your child that you
notice six hours later defeats the purpose of the device. Latency in the
parent's awareness is the product's core failure mode, not a polish issue.

iOS web push works only for sites added to the home screen, and is materially
less dependable than APNs. That is precisely the wrong place to economise.

## Decision

Native iOS app, SwiftUI, APNs for push. Requires an Apple Developer account
($99/yr) — or a free account with the 7-day re-signing cycle, which is tolerable
for a device only one person uses but annoying enough to be worth the fee.

## Alternatives considered

- **PWA** — no account, no Xcode, works on any phone. Rejected on push
  reliability alone.
- **PWA first, port later** — reasonable, but the protocol is small enough that
  building it twice saves nothing.

## Consequences

- Push is dependable, and Live Activities / lock-screen presence become options.
- The backend needs APNs credentials and a token store.
- Android is off the table without a second app. Acceptable: one parent, one
  phone, and the protocol stays client-agnostic if that ever changes.
- ADR 0003's core claim is unchanged — one box, parent on a phone, and the wire
  protocol written as though both ends were boxes.
