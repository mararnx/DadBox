# Shopping List

Re-cut 2026-09-20 (evening) for the Pi platform ([ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md)).
Links, stock and prices in [SOURCING.md](SOURCING.md); reasoning in
[DOUBLE-CHECK.md](DOUBLE-CHECK.md). Prices CHF incl. VAT as seen that day.

**The Pi Zero 2 W cannot be bought this week anywhere in Europe.** Phase 1
therefore uses a **Raspberry Pi 3 Model A+** (in stock at Pi-Shop, same
silicon, same OS image); the Zero 2 W replaces it in the box later.

---

## Phase 1 — Audio proof in the real enclosure (M0) · ~CHF 150 · order today

| Qty | Part | Why | CHF | Source |
| --- | --- | --- | --- | --- |
| 1 | **Raspberry Pi 3 Model A+** | Development board now; Zero 2 W later. USB-A takes the stick directly. | 26.90 | Pi-Shop (ships from stock) |
| 1 | **Hammond 1590DD** | The box. Fit is proven with the audio. | 27.91 | Distrelec (1–2 days / pickup) |
| 1 | microSD 32 GB A1, name-brand | Root (read-only overlay) + `/data`. Buy a second one later as the spare image. | ~10 | any |
| 1 | I2S MEMS mic module | ALSA capture via the `googlevoicehat-soundcard` overlay | 8.90 | Bastelgarage |
| 1 | Adafruit MAX98357A I2S amp | Same overlay — this pair *is* the Voice HAT | 9.95 | Galaxus (~1 week) |
| 1 | Speaker 4 Ω 3 W 40 mm, 17 mm tall | Only one that fits 32 mm inside | 8.90 | Bastelgarage |
| 1 | Adafruit NeoPixel ring 16 | The child's display. **2 left** — order first. | 18.50 | Galaxus (~1 week) |
| 1 | 74AHCT125 level shifter | Ring data: 3.3 V logic → 5 V WS2812 | ~3 | Bastelgarage / any |
| 1 | Magnetic door contact (reed + magnet) | Lid sensor **and** mic power switch | 4.90 | Bastelgarage |
| 1 | Illuminated arcade button 33 mm | Play. Side-wall mounted. | 14.90 | Galaxus |
| 2 | 3 mm LEDs + resistors; 2 × 10 kΩ pull-ups | LINK / POWER status LEDs; lid & button inputs | ~3 | any |
| 1 | Logic-level MOSFET ×2 | Ring supply gate; later the stick's VBUS gate | ~2 | any / drawer |
| 2 | USB PSU 5 V ≥ 2.5 A (micro-USB for the 3A+) | One per house | ~10 ea | any |
| — | Jumper wire, a short 5-way ribbon, M3 screws, a cardboard box | | ~5 | drawer |

---

## Phase 2 — Get it online (M1-M2) · ~CHF 65–125 + CHF 6/month

| Qty | Part | Why | CHF | Source |
| --- | --- | --- | --- | --- |
| 1 | USB 4G stick, HiLink class | Appears as USB Ethernet; no AT, no PPP. **Huawei E8372** is in stock (89.90, dear); Brovi E3372-325 / ZTE MF79U cheaper if Brack/Digitec have them — check by hand. | 30–90 | Galaxus / Brack |
| 1 | Digital Republic **Flat 1** data SIM | Unlimited, Sunrise 4G, no contract | 6/month | digitalrepublic.ch |
| 1 | Delock TS-9 → SMA adapter | The stick's antenna port to the wall | ~10 | Digitec |
| 1 | SMA bulkhead coupler | Through the aluminium | ~3 | any |
| 1 | Delock hinged LTE stub antenna, SMA | Outside the box | 20.90 | Digitec |

**Check first:** Sunrise 4G in both bedrooms.

---

## Phase 3 — Make it portable (M3) · ~CHF 90–130

Target: a weekend unplugged ([ADR 0005](../docs/decisions/0005-battery-required.md)).
**Measure the tuned Pi + gated stick on the bench first.** The cell count
depends on which Pi ends up in the box: ~3 × 18650 for a Zero 2 W, ~5–6 for
a 3A+.

| Qty | Part | Why | CHF | Source |
| --- | --- | --- | --- | --- |
| 1 | Adafruit PowerBoost 1000C | 1 A charge + 1 A 5 V boost, load-sharing | 21.70 | BerryBase CH (15 in stock, 2–5 days) |
| 3–6 | Protected 18650 ~3000 mAh (1S, parallel) | The pack | ~15 ea | BerryBase / Conrad (Fenix ARB-L18) |
| 1 | LiPo fuel gauge (MAX17043) or ADS1115 | Battery % for the app | ~10–18 | Digitec |
| 1 | Zero 2 W (when available) | Halves the Pi's share of the budget | ~20–30 | BerryBase CH notify |

---

## Phase 4 — Make it real (M4) · hardware store

Piano hinge + M3, catch magnet, 3 mm acrylic disc, speaker mesh, rubber
feet, step drill, 45 mm hole saw. No PCB.

---

## Dropped from the previous lists

LILYGO T-A7670G R2 / T-SIM7080G-S3, ESP32-S3-DevKitC-1, PCF8574 expander,
SIM7080G breakout, BQ24074, Notecard, 1NCE SIM, 60 mm button, 50 mm speaker,
hall sensor module, 3D-printing filament, custom PCB. See DOUBLE-CHECK.md.

## Running total

~CHF 330–430 plus CHF 6/month. A USB current meter (~CHF 10) will pay for
itself in phase 3.
