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
| **Shopping** | [hardware/SHOPPING-LIST.md](../hardware/SHOPPING-LIST.md) | phase 1: nothing · phase 2: **module decision** ([REVIEW §3](REVIEW.md)) | phase 1 ready |
| **Firmware** | [firmware/](../firmware/) | parts arriving (M0 parts only) | skeleton |
| **Server** | [server/](../server/) | nothing — start today | skeleton |
| **iOS** | [ios/](../ios/) | server endpoints, Apple dev account | planned |

Server and iOS are not blocked by hardware. Both can be built and tested
against a fake box long before the real one records anything. Do that — it
means the day the parts arrive, only the firmware is unknown.

## Milestones

- [ ] **M0 — It makes a sound.** Hold record, release, press play, hear it.
      No network. Proves mic, amp, buffer, buttons. *Firmware only.*
- [ ] **M1 — One way.** Box → backend → push → the parent hears it on a phone.
      *All four streams, minimum version of each.*
- [ ] **M2 — Round trip.** Parent → box, glow, chime, play. This is the point
      at which the thing exists.
- [ ] **M3 — Survives reality.** Offline queue, reconnect, battery reporting,
      quiet hours, mute, travel between homes for a week without attention.
- [ ] **M4 — Real object.** Custom PCB, printed enclosure, no breadboard.
- [ ] **M5 — In service.** A month unattended, across both homes.

## Decisions outstanding

From [REVIEW.md](REVIEW.md). Each revises an ADR; none blocks phase 1.

1. Recording gesture — hold / toggle / **lid** (§1, §2, §5)
2. Cellular module — Notecard / **bare modem + PPP** (§3)
3. Battery — survive transit / operate unplugged, and for how long (§4)
4. Two parents — does the co-parent get the app (§8)

## Before spending money

1. **Cellular coverage at both addresses.** Everything rests on it.
2. Verify the Notecard SKU's bundled data allowance and its binary payload
   limit — the protocol's chunking assumes a number nobody has checked.
3. Decide on the Apple Developer account ($99/yr vs 7-day re-signing).
