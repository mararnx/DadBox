# Roadmap

Four streams. They converge at M2, when a message makes the full round trip.

```
  shopping ──► box ───────┐
                          ├──► M2: full loop ──► M3 robustness ──► M4 PCB+case
  server ──────► ios ─────┘
```

## Streams

| Stream | Directory | Blocked by | Status |
| --- | --- | --- | --- |
| **Shopping** | [hardware/SHOPPING-LIST.md](../hardware/SHOPPING-LIST.md) | phase 2: Sunrise 4G check | phase 1 ready |
| **Box** | [box/](../box/) | parts arriving (M0 parts only) | skeleton |
| **Server** | [server/](../server/) | nothing — start today | skeleton |
| **iOS** | [ios/](../ios/) | server endpoints, Apple dev account | planned |

Server and iOS are not blocked by hardware. Both can be built and tested
against a fake box long before the real one records anything. Do that — it
means the day the parts arrive, only the firmware is unknown.

## Milestones

- [ ] **M0 — It makes a sound.** `dadboxctl`, then: open lid (a toggle switch
      on the bench), talk, close, press play, hear it. No network. Proves mic,
      amp, capture-to-disk, Opus, gating. *Box only.*
- [ ] **M1 — One way.** Modem on, Tailscale up, then box → server → push →
      the parent hears it on a phone. *All four streams, minimum version of each.*
- [ ] **M2 — Round trip.** Parent → box, glow, chime, play. This is the point
      at which the thing exists.
- [ ] **M3 — Survives reality.** Offline queue, reconnect, battery reporting,
      quiet hours, mute, travel between homes for a week without attention.
- [ ] **M4 — Real object.** Custom PCB, printed enclosure, no breadboard.
- [ ] **M5 — In service.** A month unattended, across both homes.

## Decisions from the review — resolved

| Finding | Decision | ADR |
| --- | --- | --- |
| Gesture / cap / gating / bag | Lid: open to talk, close to send | [0007](decisions/0007-lid-gesture.md) |
| Notecard is the wrong shape | Bare LTE modem over PPP | [0006](decisions/0006-bare-modem-not-notecard.md) |
| Travels ≠ operates unplugged | A weekend unplugged, everything gated | [0005](decisions/0005-battery-required.md) |
| Two parents | In the protocol now, in the build later | [0008](decisions/0008-two-parents-later.md) |
| No-connection state; ring overloaded | Ring = child's; LINK + POWER LEDs = adults' | [0009](decisions/0009-two-led-vocabularies.md) |
| Eviction could lose a recording | Outbox never evicted; pulse only after fsync | [0010](decisions/0010-nothing-is-lost.md) |
| Enclosure | Hammond 1590DD aluminium; antenna outside; button through the wall | [0011](decisions/0011-aluminium-1590dd-enclosure.md) |
| Four boards → one | LILYGO T-SIM7080G-S3 → superseded | [0012](decisions/0012-lilygo-t-sim7080g-s3.md) |
| Cat-M unsupported by the user's SIM provider | LTE Cat-1/4; Digital Republic Flat 1 | [0013](decisions/0013-cat1-not-catm.md) |
| Dev process on an ESP32 vs a box you can SSH into | Raspberry Pi Zero 2 W (3A+ for now) + A7670E Cat-1 HAT; UPS HAT + four cells (revised 2026-09-21 after [EVALUATION](../hardware/EVALUATION.md)) | [0014](decisions/0014-raspberry-pi-zero-2w.md) |
| Ten-minute polling is too slow after a message and too often otherwise | 1 min on mains or for 90 min after use, 30 min idle on battery; no SMS wake | [0015](decisions/0015-adaptive-polling.md) |

Still open, per component: [components/](components/README.md).

## Before spending money

1. Sunrise 4G in both bedrooms (Digital Republic rides Sunrise). Near-certain.
2. A Pi Zero 2 W you can actually buy — scarce in CH today.
3. Measure the tuned Pi + gated modem on the bench **before** buying cells.
4. Decide on the Apple Developer account ($99/yr vs 7-day re-signing).

Links and prices for everything: [hardware/bom/bom.csv](../hardware/bom/bom.csv) and [hardware/EVALUATION.md](../hardware/EVALUATION.md).
