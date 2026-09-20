# Shopping List

Ordered in four phases. **Buy phase 1 only.** If the audio path disappoints —
and the mic and the enclosure acoustics are the two things most likely to — you
will have spent ~$55 finding out instead of ~$200.

Prices are rough estimates for sanity-checking a budget, not quotes. Check
before ordering.

---

## Phase 1 — Prove the audio (M0) · ~$60

Everything needed for: open lid (a switch, for now), talk, close, press play,
hear yourself. No network, no battery.

| Qty | Part | Why this one | ~$ |
| --- | --- | --- | --- |
| 1 | ESP32-S3-DevKitC-1 **N16R8** | The R8 matters — 8 MB PSRAM holds the recording. A board without PSRAM cannot do this design. | 15 |
| 1 | ICS-43434 I2S mic breakout | Better noise floor than the INMP441 and worth it for a child's voice across a room. | 8 |
| 1 | Load switch breakout, or a P-channel MOSFET + pull-up | The mic's power switch. This is how "only listens with the lid open" is true in hardware. | 3 |
| 1 | MAX98357A I2S amp breakout | Digital in, speaker out, no DAC needed. Has a shutdown pin — use it. | 6 |
| 1 | Speaker, 3 W 4 Ω, 40-50 mm | Full-range. The enclosure will matter more than the driver. | 5 |
| 1 | Toggle switch (stands in for the lid) | Any panel toggle. The real lid switch comes in phase 4. | 2 |
| 1 | Arcade button, 60 mm, + a spare microswitch | The play button. Big travel, survives a 7-year-old. | 4 |
| 1 | WS2812B ring, 16 px | The entire notification system. Diffuse it. | 8 |
| 1 | Logic-level N-MOSFET (e.g. 2N7002/AO3400-class) | Gates the ring's 5 V. Sixteen dark WS2812Bs draw ~16 mA; gated they draw nothing. | 1 |
| 2 | 3 mm LEDs + resistors | LINK and POWER status LEDs — the adults' channel, so the ring never has to show a fault. | 1 |
| 1 | Breadboard + jumper kit | | 7 |
| — | A cardboard box | Listen to it inside one. Seriously. | 0 |

**Check first:** does your ESP32-S3 board say N16R8? Many listings show a
generic photo and ship a PSRAM-less variant. This is the most common way to
lose a weekend.

---

## Phase 2 — Get it online (M1-M2) · ~$40

Only after phase 1 makes a sound. [ADR 0006](../docs/decisions/0006-bare-modem-not-notecard.md).

| Qty | Part | Why | ~$ |
| --- | --- | --- | --- |
| 1 | SIM7080G breakout **with level shifting** and a u.FL LTE antenna (Waveshare-style Cat-M/NB-IoT board) | LTE-M module the ESP32 drives over UART via `esp_modem`. **The module's UART is 1.8 V** — the breakout must shift it or nothing will work. | 25 |
| 1 | Flat-rate IoT SIM (1NCE-type: ~€10, 500 MB, 10 years, EU roaming) | One payment, no account to lapse. 500 MB is ~17 hours of ADPCM or ~70 hours of Opus. | 12 |
| 1 | 1000 µF low-ESR capacitor | Across the modem's supply. Transmit bursts brown out small rails; this is the #1 cause of random resets. | 2 |

**Check first — before ordering either:** LTE-M (Cat-M1) coverage at *both*
addresses, on the network the SIM roams onto. NB-IoT coverage doesn't count —
too slow for audio.

Fallback if modem bring-up fights back: a Blues Notecard + Notecarrier-B
(~$64) drops onto the same header. The protocol doesn't care.

---

## Phase 3 — Make it portable (M3) · ~$45

Target: a weekend unplugged. [ADR 0005](../docs/decisions/0005-battery-required.md).
**Buy the cell after measuring the gated idle current on the bench**, not before.

| Qty | Part | Why | ~$ |
| --- | --- | --- | --- |
| 1 | LiPo 3000-4000 mAh **with integrated PCM** and a thermistor | Protection at the cell, not only in the charger. Non-negotiable in a device a child carries. | 16 |
| 1 | USB-C charger with **power path** and a thermistor input (BQ24074-class breakout) | Runs while charging on a flat cell; won't charge a hot or cold cell. | 12 |
| 1 | Voltage divider + assorted decoupling | Battery sense on an ADC pin. | 2 |
| 1 | USB-C PSU 5 V 2 A | | 10 |
| 1 | Second USB-C PSU | One per house. The box should never travel with its charger. | 10 |

---

## Phase 4 — Make it real (M4) · ~$70+

Don't price this yet. PCB fabrication, filament (PETG/ASA shell, TPU bumper),
heat-set inserts, and the lid mechanism: pin hinge hardware + a microswitch,
or a magnet + hall sensor. There will be a second enclosure revision.

---

## Assumed you already have

Soldering iron, multimeter, 3D printer, USB-C cables, hookup wire. Say if not —
a scope is *nice* for I2S debugging but far from required. A USB current meter
(~$10) will matter a lot in phase 3.

## Running total if all four phases land

~$215. Most of it deferred behind two checkpoints that can each kill the
approach cheaply.
