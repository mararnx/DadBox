# Roadmap

Four streams. They converge at M2, when a message makes the full round trip.

```
  shopping ──► box ───────┐
                          ├──► M2: full loop ──► M3 robustness ──► M4 real box
  server ──────► ios ─────┘
```

## Streams

| Stream | Directory | Blocked by | Status |
| --- | --- | --- | --- |
| **Shopping** | [hardware/SHOPPING-LIST.md](../hardware/SHOPPING-LIST.md) | antenna: the HAT in hand; battery: bench measurements | bench parts and modem ordered |
| **Box** | [box/](../box/) | parts arriving | skeleton; logic unit-tested on the Mac |
| **Server** | [server/](../server/) | nothing — start today | skeleton |
| **iOS** | [ios/](../ios/) | server endpoints, Apple dev account | planned |

Server and iOS are not blocked by hardware. Both can be built and tested
against a fake box long before the real one records anything. Do that — it
means the day the parts arrive, only the box software is unknown.

## Milestones

- [ ] **M0 — It makes a sound.** `dadboxctl`, then: press Record, talk, press
      it again, press Play, hear it. No network. Proves mic, amp,
      capture-to-disk, Opus, the button lights, the shared mic/red-light pin,
      gating. *Box only.*
- [ ] **M1 — One way.** Modem HAT on, Tailscale up, then box → server → push →
      the parent hears it on a phone. *All four streams, minimum version of each.*
- [ ] **M2 — Round trip.** Parent → box, the Play button glows, chime, play.
      This is the point at which the thing exists.
- [ ] **M3 — Survives reality.** Offline queue, reconnect, adaptive polling,
      UPS module and battery reporting, quiet hours, mute, travel lock, travel
      between homes for a week without attention.
- [ ] **M4 — Real object.** Everything in the drilled aluminium enclosure:
      antenna outside, wiring sturdier than jumper wires, endurance-grade SD
      card, no breadboard. Off-the-shelf parts only — no custom PCB, no
      printed parts.
- [ ] **M5 — In service.** A month unattended, across both homes.

## Decisions from the review — resolved

| Finding | Decision | ADR |
| --- | --- | --- |
| Gesture / cap / gating / bag | Two lit buttons, Record and Play; nothing that moves; mic power tied to the red light; 0.5 s press rule and travel lock for the bag (supersedes the lid of [0007](decisions/0007-lid-gesture.md)) | [0016](decisions/0016-two-buttons-no-lid.md) |
| Battery board is half the box, a second charger and two days at best | First box is mains only; battery designed in, deferred | [0019](decisions/0019-mains-first-battery-deferred.md) |
| Notecard is the wrong shape | A bare LTE modem and our own server | [0006](decisions/0006-bare-modem-not-notecard.md) |
| Travels ≠ operates unplugged | A weekend unplugged, everything gated | [0005](decisions/0005-battery-required.md) |
| Two parents | In the protocol now, in the build later | [0008](decisions/0008-two-parents-later.md) |
| No-connection state; child's display overloaded | Button lights = child's; LINK + POWER LEDs = adults' | [0009](decisions/0009-two-led-vocabularies.md) |
| Eviction could lose a recording | Outbox never evicted; pulse only after fsync | [0010](decisions/0010-nothing-is-lost.md) |
| Enclosure | 1590DD-size die-cast aluminium; plate screwed down; antenna outside; round holes only | [0011](decisions/0011-aluminium-1590dd-enclosure.md) |
| Four boards → one | LILYGO T-SIM7080G-S3 → superseded by 0014 | [0012](decisions/0012-lilygo-t-sim7080g-s3.md) |
| Cat-M unsupported by the user's SIM provider | LTE Cat-1; Digital Republic Flat 1, always | [0013](decisions/0013-cat1-not-catm.md) |
| Dev process on an ESP32 vs a box you can SSH into | Raspberry Pi Zero 2 W + Waveshare SIM7670G Cat-1 HAT on USB; UPS Module 3S + three 18650s, 12.6 V barrel-jack charger (as revised 2026-09-21 after [EVALUATION](../hardware/EVALUATION.md)) | [0014](decisions/0014-raspberry-pi-zero-2w.md) |
| Ten-minute polling is too slow after a message and too often otherwise | 1 min on mains or for 90 min after use, 30 min idle on battery with the modem off in between; no SMS wake | [0015](decisions/0015-adaptive-polling.md) |
| Where the server runs; who can hear the audio | One managed host; audio end-to-end encrypted; iOS the only client; no server-side transcode (host proposed: Cloudflare) | [0017](decisions/0017-managed-hosting-e2ee.md) |
| Retention | Messages archived forever, on the server and in the app; no 24 h deletion | [0018](decisions/0018-archive-forever.md) |

Still open, per component: [components/](components/README.md).

## Before spending more money

Ordered on 2026-09-21: the enclosure, step drill and soldering iron; the Pi
Zero 2 W starter kit; the SIM7670G HAT; both buttons, mic, amp (plus a spare)
and speaker; a Debug Probe; jumper wires. The SIM and a 5 V micro-USB supply
are in hand. What remains waits on purpose:

1. **Antenna** (SMA pigtail + the 52 mm and 115 mm stubs) — after the HAT
   arrives and its antenna connector is confirmed. Then `AT+CSQ` on Sunrise 4G
   in both bedrooms decides which stub stays.
2. **Battery** (UPS Module 3S, three cells, second charger, panel-mount DC
   jack) — **deferred**: the first box is mains only ([ADR 0019](decisions/0019-mains-first-battery-deferred.md)).
3. **Measure the inside of the enclosure** before any layout or drilling.
4. Small parts before the box leaves home: endurance-grade SD card, rubber
   feet, 2 × 3 mm LEDs + 220 Ω, sturdier internal wiring.
5. Decide on the Apple Developer account ($99/yr vs 7-day re-signing).

Links and prices for everything: [hardware/bom/bom.csv](../hardware/bom/bom.csv) and [hardware/EVALUATION.md](../hardware/EVALUATION.md).
