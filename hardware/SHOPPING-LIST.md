# Shopping List

Re-cut 2026-09-21 after [EVALUATION.md](EVALUATION.md) (Option C) and the
user's decisions: aluminium 1590DD with a small rigid antenna, start on the
Pi 3A+, off-the-shelf parts only, Flat 1 always. Platform in
[ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md) (revised). Every
part with its link is in [bom/bom.csv](bom/bom.csv); this file is the order
of buying. Prices CHF incl. VAT as seen 2026-09-20.

**The Pi Zero 2 W cannot be bought this week.** Everything is developed on a
**Pi 3 Model A+** (same image, same pins). On the 3A+ the box is a mains
device; the weekend on battery waits for the Zero 2 W.

---

## Phase 1 — Bench: records and plays back · ~CHF 140 · order today

| Qty | Part | CHF | Source |
| --- | --- | --- | --- |
| 1 | **Adafruit NeoPixel ring 16 (44.5 mm)** — 2 in stock, **order first** | 14.90 | Play-Zone |
| 1 | Adafruit MAX98357A I2S amp | 8.90 | Play-Zone |
| 1 | **Raspberry Pi 3 Model A+** | 26.90 | Pi-Shop |
| 1 | Official Pi 12.5 W micro-USB PSU | 11.90 | Pi-Shop |
| 1 | Waveshare USB-C inline power meter | 10.90 | Pi-Shop |
| 1 | INMP441 I2S MEMS mic module | 3.10 | BerryBase CH |
| 1 | SN74AHCT125N level shifter | 0.50 | BerryBase CH |
| 1 | Speaker 4 Ω 3 W Ø40 × 17 mm | 8.90 | Bastelgarage |
| 1 | DFRobot reed door contact + magnet (lid sensor **and** mic power switch) | 7.90 | Bastelgarage |
| 1 | SanDisk High Endurance 32 GB microSD | 22.95 | Brack |
| 2 | Pololu 2811 high-side switch (ring gate + spare for the modem feed) | EUR 3.50 ea | Botland |
| 1 | USB-serial adapter (CP2102) or Pi Debug Probe — skip if in the drawer | ~10 | any |
| — | 3 mm LEDs, 220 Ω, 10 kΩ, jumper wire, perfboard | ~5 | any / drawer |

Add the phase-2 modem to the Pi-Shop order to save a shipment.

## Phase 2 — Online · ~CHF 60 + CHF 6/month

| Qty | Part | CHF | Source |
| --- | --- | --- | --- |
| 1 | **Waveshare A7670E LTE Cat-1 HAT** | 34.90 | Pi-Shop |
| 1 | Digital Republic **Flat 1** SIM — always, also while developing | 6/month | digitalrepublic.ch |
| 1 | Delock 88747 SMA bulkhead → MHF/U.FL pigtail | 7.32 | Reichelt CH |
| 1 | **Delock 90694** rigid LTE stub, 52 mm — the chosen antenna | 8.24 | Reichelt CH |
| 1 | Delock 90682 rigid LTE antenna, 115 mm — comparison / fallback | 9.16 | Reichelt CH |

The short stub's datasheet range stops at 824 MHz; Sunrise's indoor band 20
downlink is 791–821 MHz. It may be fine (band 3 is covered) — `AT+CSQ` in both
bedrooms with each antenna decides. **Check Sunrise 4G in both bedrooms first.**

## Phase 3 — Portable · ~CHF 110 · buy after measuring

| Qty | Part | CHF | Source |
| --- | --- | --- | --- |
| 1 | Waveshare UPS HAT (C): load-share charger, 5 V boost, INA219 gauge | 25.90 | Pi-Shop |
| 4 | Panasonic NCR18650GA 3300 mAh, protected, JST lead | 13.90 ea | Bastelgarage |
| 1 | 4-slot 18650 holder (takes 69.5 mm protected cells) | 4.90 | Bastelgarage |
| 1 | **Raspberry Pi Zero 2 W** — backorder now, notify at Pi-Shop + BerryBase CH | EUR 19.90 | Welectron |
| 1 | Short micro-USB OTG → USB-C cable (Zero 2 W ↔ modem) | ~5 | any |

Measure the tuned Pi and the modem (registered, transmitting, PWRKEY-off)
before buying cells: 3 vs 4 is decided by the meter, not by this list.

## Phase 4 — The real box · ~CHF 105

| Qty | Part | CHF | Source |
| --- | --- | --- | --- |
| 1 | **Hammond 1590DD** die-cast aluminium | 27.90 | Distrelec |
| 1 | 16 mm stainless flush button, RGB ring, IP65 | 19.90 | Bastelgarage |
| 1 | Adafruit USB-C round panel-mount extension + C→micro-B adapter | 1.75 + ~5 | BerryBase CH |
| 1 | 8 × 3 mm N45 disc magnets, 10 pack | 4.10 | supermagnete.ch |
| 1 | Second High Endurance card (spare image) | 22.95 | Brack |
| 1 | Second PSU (house B) | 11.90 | Pi-Shop |
| — | Opal acrylic 3 mm, piano hinge, rubber feet | 17.05 | Hornbach |

Off-the-shelf only, no 3D printing: the ring window is a 45 mm round hole with
a **square** of opal acrylic glued behind it (score and snap — no disc to
cut); the stainless button brings its own bezel. Round holes only: 45 mm ring
window, 16 mm button, 12–18 mm USB-C, 6.5 mm SMA, speaker grille as a drilled
pattern.

---

## Running total

~CHF 415 for everything including the meter, the spare card, both PSUs and
the Zero 2 W, plus CHF 6/month. Phases 1 + 2 (~CHF 200) get a working,
online, mains-powered box.

## Dropped

USB 4G sticks (E8372 / E3372 / MF79U) and TS-9 adapters, PowerBoost 1000C,
separate fuel gauge, 33 mm arcade button, hinged 24 cm antenna; and from
earlier lists the LILYGO boards, ESP32-S3, Notecard, 1NCE SIM, 3D-printing
filament, custom PCB. Reasons in EVALUATION.md and ADR 0014.
