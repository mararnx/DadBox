# Sourcing — Switzerland, ready to order

Researched 2026-09-20. Prices in CHF incl. VAT as shown on the day; stock
changes daily — re-check the links before paying. Component choices are
justified in [DOUBLE-CHECK.md](DOUBLE-CHECK.md).

## The one thing to know about Galaxus

The "third-party supplier" behind Galaxus's LILYGO, Waveshare and Purecrea
listings **is bastelgarage.ch**. Same stock, same box, marked up:

| Part | Galaxus | Bastelgarage direct |
| --- | --- | --- |
| LILYGO T-SIM7080G-S3 | 57.90 | **43.90** |
| Waveshare ESP32-S3 N16R8 | 24.90 | **18.90** |
| Hall sensor module | 8.90 | **3.90** |

Galaxus is still right for the parts it stocks *itself* (Adafruit, Delock,
Allnet). So: **two orders** — Bastelgarage direct for the maker modules,
Galaxus for the rest — or one Galaxus order for ~CHF 40 more. Both ship in
two days.

## Order 1 — Bastelgarage direct · CHF 66.60 · all in stock

| Qty | Part | CHF | Link |
| --- | --- | --- | --- |
| 1 | **LILYGO T-SIM7080G-S3** — ESP32-S3 16 MB/8 MB + SIM7080G + charger + 18650 holder + JST 2.0 + TF slot + nano-SIM; LTE & GPS antennas and headers included | 43.90 | [bastelgarage](https://www.bastelgarage.ch/lilygo-t-sim7080g-s3-mit-nb-iot-cat-m-und-gps) |
| 1 | I2S MEMS microphone module (MSM261S4030H0, 3.3 V, 1 mA) | 8.90 | [bastelgarage](https://www.bastelgarage.ch/i2s-mikrofon-modul) |
| 1 | Speaker 4 Ω 3 W **40 mm, 17 mm tall** | 8.90 | [bastelgarage](https://www.bastelgarage.ch/lautsprecher-4ohm-3w-40mm) |
| 1 | Magnetic door/window contact (reed + magnet, 330 mm lead, NO) — the lid switch *and* the mic's power switch | 4.90 | [bastelgarage](https://www.bastelgarage.ch/magnetischer-tur-fenster-kontakt) |

Out of stock there today, so bought on Galaxus instead: MAX98357 clone
(6.90), Neopixel ring sets (17.90 / 23.90), reed switch alone (1.30).

## Order 2 — Galaxus / Digitec · CHF 74.– + PSUs · mostly "at supplier", ~1 week

| Qty | Part | CHF | Stock | Link |
| --- | --- | --- | --- | --- |
| 1 | Adafruit MAX98357A I2S 3 W amp | 9.95 | >10 at supplier | [galaxus](https://galaxus.ch/de/s1/product/adafruit-i2s-3w-class-d-amplifier-breakout-max98357a-erweiterung-elektronikmodul-5998646) |
| 1 | Adafruit NeoPixel Ring 16 (44.5 mm OD) | 18.50 | **only 2** at supplier | [galaxus](https://www.galaxus.ch/en/s1/product/adafruit-neopixel-ring-16-x-ws2812-5050-rgb-led-diode-5998257) |
| 1 | Purecrea illuminated arcade button **33 mm** (24 mm hole) — side-wall mount, see DOUBLE-CHECK | 14.90 | >10 (bastelgarage) | [galaxus](https://www.galaxus.ch/en/s1/product/purecrea-arcade-button-illuminated-33mm-green-buttons-switches-36704979) |
| 1 | Allnet pigtail U.FL → SMA female, 30 cm | 9.75 | 4 at supplier | [galaxus](https://www.galaxus.ch/en/s1/product/allnet-antenna-pigtail-ufl-to-sma-f-30cm-antenna-cable-antenna-satellite-cables-31824258) |
| 1 | Delock LTE/HSPA/GSM stub antenna, SMA male, hinged, 24 cm, ≤4 dBi | 20.90 | 8 at supplier, 2 days | [digitec](https://www.digitec.ch/de/s1/product/delock-ltehspagsm-antenne-sma-stecker-mobilfunk-antenne-netzwerk-zubehoer-5833613) |
| 2 | USB-C PSU 5 V / 2 A (one per house) — any | ~10 ea | | |

Alternatives on Galaxus if the above slip: OEM 30 mm arcade button 11.90–12.70
([link](https://www.galaxus.ch/de/s1/product/oem-arcade-button-30mm-rot-transparent-schalter-taster-5999314));
Delock indoor LTE antenna with 3 m cable, 11.– — works, but a cable is not what
a box wants ([link](https://www.galaxus.ch/de/s4/product/delock-lte-antenne-mit-sma-stecker-auto-antenne-5741667)).

**Pigtail caveat:** the Allnet listing says "straight" and does not confirm a
panel-mount (flange/bulkhead) SMA. The one that does — Varia SMA-Flanschbuchse
→ U.FL 15 cm — is currently unavailable
([digitec](https://www.digitec.ch/de/s1/product/varia-pigtail-sma-buchse-zu-ufl-stecker-15-cm-elektronikkabel-stecker-16175454)).
A bulkhead SMA is what goes through an aluminium wall; if Allnet's isn't one,
a bulkhead adapter is CHF 3 anywhere.

## Order 3 — Distrelec · the enclosure

| Qty | Part | CHF | Link |
| --- | --- | --- | --- |
| 1 | **Hammond 1590DD** die-cast aluminium, natural, 188 × 120 × 37 mm, IP54 — **8 in stock, 1–2 days** | **27.91** | [distrelec.ch](https://www.distrelec.ch/en/die-cast-enclosure-1590-188x120x37mm-die-cast-aluminium-natural-ip54-hammond-1590dd/p/15011796) |

Not on Galaxus/Digitec (they carry the taller 1590E and 1590D). Distrelec is
the Swiss stockist; datasheet with inside dimensions at
[hammfg.com/part/1590DD](https://www.hammfg.com/part/1590DD).

## Order 4 — the SIM

| Part | Price | Link |
| --- | --- | --- |
| 1NCE IoT Lifetime Flat — 500 MB, 10 years, EU + Switzerland, no monthly fee | €12 one-off | [1nce.com pricing](https://www.1nce.com/en-eu/1nce-connect/pricing) |

**Verify before relying on it:** 1NCE sells B2B; confirm a private individual
can order in CH. Fallback that definitely sells to individuals and supports
LTE-M: Hologram (pay-as-you-go). Either way, confirm **LTE-M (Cat-M1)** —
not NB-IoT — coverage at both addresses on the network the SIM roams onto
(Swisscom in CH).

## Battery — not yet in stock anywhere convenient

Needed: a **protected** 18650 (≈3000 mAh, NCR18650B-class) **with JST-PH 2.0
leads** to plug into the LILYGO's JST and be strapped down — not in its spring
holder, which a school bag will bounce. The exact part exists — Purecrea
18650 3000 mAh with protection and JST-PH — but is unavailable today
([galaxus](https://www.galaxus.ch/de/s1/product/purecrea-li-ion-akku-3000ma-18650-mit-schutzelektronik-und-stecker-entwicklungsboard-kit-36169153),
set a notify). Not needed until phase 3.

## Temu / AliExpress

Couldn't verify prices — their pages block automated fetch. From experience:
INMP441 mic, MAX98357A clone, 16-pixel WS2812B ring all ~CHF 2–5 each, 2–4
weeks, no Swiss warranty, and counterfeit ICs are common on the amp. Fine for
**spares**; not for the one board (the LILYGO) the whole project sits on.
If you want the cheap route for the modules: search Temu for `INMP441`,
`MAX98357A`, `WS2812B 16 ring` and buy two of each.

## Totals

| | CHF |
| --- | --- |
| Bastelgarage | 66.60 |
| Galaxus / Digitec (incl. antenna 20.90, two PSUs ~20) | ~94 |
| Distrelec 1590DD | 27.91 |
| 1NCE SIM | ~12 |
| Battery (phase 3) | ~15 |
| **Total** | **~CHF 225** |

Down from ~215 USD on the old plan for *more* — the LILYGO replaces the
DevKitC, the modem breakout, the level shifter and the charger, and adds the
TF slot.

## Not sourced yet

- Two 3 mm LEDs + resistors (status LEDs) — any assortment, CHF 2.
- Bulkhead SMA (if Allnet's pigtail isn't one), CHF 3.
- Delock's cheaper "3G, GSM" antenna variant (13.50) is *not* the one — it may
  lack the LTE-M bands. Take the 20.90 LTE variant.
- Piano hinge + M3 hardware for the lid, acrylic disc for the ring window,
  speaker grille mesh — hardware store, phase 4.
- 1000 µF cap at the modem — only if resets appear; the LILYGO has its own.
