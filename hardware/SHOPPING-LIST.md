# Shopping List

Ordered in four phases. **Buy phase 1 only.** If the audio path disappoints —
and the mic and the enclosure acoustics are the two things most likely to — you
will have spent ~$50 finding out instead of ~$200.

Prices are rough estimates for sanity-checking a budget, not quotes. Check
before ordering.

---

## Phase 1 — Prove the audio (M0) · ~$55

Everything needed for: hold button, talk, release, press play, hear yourself.
No network, no battery.

| Qty | Part | Why this one | ~$ |
| --- | --- | --- | --- |
| 1 | ESP32-S3-DevKitC-1 **N16R8** | The R8 matters — 8 MB PSRAM holds the raw recording. A board without PSRAM cannot do this design. | 15 |
| 1 | ICS-43434 I2S mic breakout | Better noise floor than the INMP441 and worth it for a child's voice across a room. | 8 |
| 1 | MAX98357A I2S amp breakout | Digital in, speaker out, no DAC needed. | 6 |
| 1 | Speaker, 3 W 4 Ω, 40-50 mm | Full-range. The enclosure will matter more than the driver. | 5 |
| 2 | Arcade button, 60 mm | Big travel, survives a 7-year-old. Get spare microswitches. If the lid wins, one of these becomes a lid switch. | 6 |
| 1 | WS2812B ring, 16 px | The entire notification system. | 8 |
| 1 | Breadboard + jumper kit | | 7 |

**Check first:** does your ESP32-S3 board say N16R8? Many listings show a
generic photo and ship a PSRAM-less variant. This is the most common way to
lose a weekend.

---

## Phase 2 — Get it online (M1-M2) · ~$30-64

**On hold.** The module choice is open — see
[docs/REVIEW.md §3](../docs/REVIEW.md). The table below is the Notecard
option; the bare-modem option is a SIM7080G breakout (~$20) plus a flat-rate
IoT SIM (~€10). Only after phase 1 makes a sound, either way.

| Qty | Part | Why | ~$ |
| --- | --- | --- | --- |
| 1 | Blues Notecard Cellular (global SKU) | Bundled data, no SIM, no carrier account. [ADR 0002](../docs/decisions/0002-cellular-not-wifi.md) | 49 |
| 1 | Notecarrier-B | Carrier + I2C to the ESP32. | 15 |

**Check first — before ordering either:** cellular coverage at *both*
addresses, and the SKU's actual data allowance and binary payload limit. The
protocol's chunk size is currently a guess.

---

## Phase 3 — Make it portable (M3) · ~$35

The box travels with the child, so this stops being optional.
See [ADR 0005](../docs/decisions/0005-battery-required.md).

| Qty | Part | Why | ~$ |
| --- | --- | --- | --- |
| 1 | LiPo 3000 mAh **with integrated PCM** | Protection at the cell, not only in the charger. Non-negotiable in a device a child carries. | 14 |
| 1 | USB-C charger with **power path** | Runs while charging with a flat cell. | 10 |
| 1 | 1000 µF low-ESR cap + assorted decoupling | Modem transmit bursts brown out an undersized rail. | 3 |
| 1 | USB-C PSU 5 V 2 A | | 10 |

---

## Phase 4 — Make it real (M4) · ~$60+

Don't price this yet. PCB fabrication, filament, heat-set inserts, and whatever
the first enclosure revision teaches you. There will be a second revision.

---

## Assumed you already have

Soldering iron, multimeter, 3D printer, USB-C cables, hookup wire. Say if not —
a scope is *nice* for I2S debugging but far from required.

## Running total if all four phases land

~$215. Most of it deferred behind two checkpoints that can each kill the
approach cheaply.
