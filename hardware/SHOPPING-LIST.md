# Shopping List

Re-cut 2026-09-20 around the 1590DD enclosure and the LILYGO board. Links,
prices and stock are in [SOURCING.md](SOURCING.md); the reasoning behind each
part is in [DOUBLE-CHECK.md](DOUBLE-CHECK.md). Prices CHF incl. VAT, as seen on
the day.

**Buy phase 1 only.** It now proves the audio *and* the fit in the real box.

---

## Phase 1 — Audio proof in the real enclosure (M0) · ~CHF 165

| Qty | Part | Why | CHF | Source |
| --- | --- | --- | --- | --- |
| 1 | **LILYGO T-A7670G R2** | The whole computer: ESP32 WROVER, A7670G **Cat-1**, GNSS, JST LiPo charging, SIM. LTE + GPS antennas included. [ADR 0013](../docs/decisions/0013-cat1-not-catm.md) | 37.90 | Bastelgarage |
| 1 | microSD 8–32 GB, name-brand | The never-lost outbox — the board has 4 MB flash | ~8 | any |
| 1 | PCF8574 I²C expander module | Slow signals (LEDs, gates, lid, button); the WROVER is short on pins | ~3 | Bastelgarage |
| 1 | **Hammond 1590DD** | The box. Buy now so fit is proven with the audio. 8 in stock. | 27.91 | Distrelec |
| 1 | I2S MEMS mic module (MSM261S4030H0) | 3.3 V, 1 mA — the reed contact switches it directly | 8.90 | Bastelgarage |
| 1 | Adafruit MAX98357A I2S amp | Fed from VBAT → ~1.5 W into 4 Ω. Has a shutdown pin. | 9.95 | Galaxus |
| 1 | Speaker 4 Ω 3 W **40 mm, 17 mm tall** | The only one that fits 32 mm inside | 8.90 | Bastelgarage |
| 1 | Adafruit NeoPixel ring 16 (44.5 mm) | The child's entire display. Only 2 in stock — order first. | 18.50 | Galaxus |
| 1 | Magnetic door contact (reed + magnet) | Lid sensor **and** mic power switch | 4.90 | Bastelgarage |
| 1 | Illuminated arcade button 33 mm | Play. Side-wall mounted (24 mm hole). | 14.90 | Galaxus |
| 2 | 3 mm LEDs + 220 Ω | LINK and POWER status LEDs | ~2 | any |
| 1 | Logic-level N-MOSFET (AO3400-class) or P-FET | Gates the ring's supply | ~1 | any / drawer |
| — | Jumper wire, a short 5-way ribbon, M3 screws | Ribbon crosses the hinge | ~5 | drawer |

**Confirmed:** the R2 has the TF card slot (SPI on GPIO 14/2/15/13) and an
18650 holder as well as the JST connector. Add two 10 kΩ resistors for the
lid and button pull-ups (input-only pins).

---

## Phase 2 — Get it online (M1-M2) · ~CHF 31 + CHF 6/month

Only after phase 1 sounds right inside the box.

| Qty | Part | Why | CHF | Source |
| --- | --- | --- | --- | --- |
| 1 | Digital Republic **Flat 1** data SIM | Unlimited, Sunrise 4G, no contract. Flat 0.4 (CHF 4) also works. | 6 / month | digitalrepublic.ch |
| 1 | Pigtail u.FL → **bulkhead** SMA female | Through the back wall — aluminium blocks the included antenna | 9.75 | Galaxus (Allnet; confirm flange) |
| 1 | Delock LTE/GSM stub antenna, SMA male, hinged, 24 cm | Outside the box. The LTE variant, not the 13.50 "3G/GSM" one. | 20.90 | Digitec |

**Check first:** Sunrise 4G coverage at both addresses — near-certain, but
look at the bedroom, not the street.

---

## Phase 3 — Make it portable (M3) · ~CHF 35

Target: a weekend unplugged ([ADR 0005](../docs/decisions/0005-battery-required.md)).
**Buy the cell after measuring the gated idle current.**

| Qty | Part | Why | CHF | Source |
| --- | --- | --- | --- | --- |
| 1 | **Protected** 18650 ≈3000 mAh **with JST-PH 2.0 leads** | On the JST, strapped down — not in the spring holder | ~15 | Galaxus (Purecrea, notify) |
| 2 | USB-C PSU 5 V / 2 A | One per house; the box never travels with its charger | ~10 ea | Galaxus |

---

## Phase 4 — Make it real (M4) · hardware store

Piano hinge (≈120 mm) + M3 hardware, neodymium catch magnet, 3 mm acrylic
disc (ring diffuser), speaker mesh, rubber feet, a step drill and a 45 mm
hole saw if you don't own them. No PCB: point-to-point on the LILYGO's
headers is fine for one unit.

---

## Dropped from the old list

ESP32-S3-DevKitC-1, SIM7080G breakout, level shifter, BQ24074 charger, 60 mm
arcade button, 50 mm speaker, hall sensor module, 3D-printing filament and
inserts, custom PCB. See [DOUBLE-CHECK.md](DOUBLE-CHECK.md) for each.

## Running total

~CHF 225 across four phases. A USB current meter (~CHF 10) will pay for
itself in phase 3.
