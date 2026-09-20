# Roadmap

Four streams. They converge at M2, when a message makes the full round trip.

```
  shopping ──► firmware ──┐
                          ├──► M2: full loop ──► M3 robustness ──► M4 PCB+case
  server ──────► ios ─────┘
```

## Streams

| Stream | Directory | Blocked by | Status |
| --- | --- | --- | --- |
| **Shopping** | [hardware/SHOPPING-LIST.md](../hardware/SHOPPING-LIST.md) | phase 2: LTE-M coverage check | phase 1 ready |
| **Firmware** | [firmware/](../firmware/) | parts arriving (M0 parts only) | skeleton |
| **Server** | [server/](../server/) | nothing — start today | skeleton |
| **iOS** | [ios/](../ios/) | server endpoints, Apple dev account | planned |

Server and iOS are not blocked by hardware. Both can be built and tested
against a fake box long before the real one records anything. Do that — it
means the day the parts arrive, only the firmware is unknown.

## Milestones

- [ ] **M0 — It makes a sound.** Open lid (a toggle switch on the bench),
      talk, close, press play, hear it. No network. Proves mic, amp, ADPCM,
      PSRAM, gating. *Firmware only.*
- [ ] **M1 — One way.** Modem bring-up, then box → server → push → the parent
      hears it on a phone. *All four streams, minimum version of each.*
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
| Notecard is the wrong shape | Bare LTE-M modem over PPP | [0006](decisions/0006-bare-modem-not-notecard.md) |
| Travels ≠ operates unplugged | A weekend unplugged, everything gated | [0005](decisions/0005-battery-required.md) |
| Two parents | In the protocol now, in the build later | [0008](decisions/0008-two-parents-later.md) |

Still open, per component: [components/](components/README.md).

## Before spending money

1. **LTE-M (Cat-M1) coverage at both addresses.** Not NB-IoT. Everything
   rests on it.
2. The SIM7080G breakout must level-shift its 1.8 V UART.
3. Decide on the Apple Developer account ($99/yr vs 7-day re-signing).
