# Sourcing — Switzerland, ready to order

Re-researched 2026-09-20 (evening) for the Pi platform ([ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md))
with one constraint from the user: **immediate availability**. Prices CHF
incl. VAT as shown that day; stock changes daily. Reasoning per part in
[DOUBLE-CHECK.md](DOUBLE-CHECK.md).

## The situation with the Pi Zero 2 W

**Not buyable anywhere in Europe this week.** BerryBase CH 17.15 (notify only),
Bastelgarage 29.90 (out), Pi-Shop (out), Digitec/Galaxus quoting
**January 2027**, the official bundles out, Welectron DE "incoming", Pimoroni
UK empty. Raspberry Pi expects supply to improve over the autumn.

**What to do instead:** buy a **Raspberry Pi 3 Model A+** today — same
BCM2837B0 silicon, 512 MB, a full-size USB-A port the LTE stick plugs straight
into, and it boots the **identical OS image**. Develop on it, prove M0–M2,
then drop a Zero 2 W into the box when one lands. Or keep the 3A+ and accept a
larger pack (see DOUBLE-CHECK). Set a stock notify at BerryBase CH now.

## Order today

| Part | CHF | Stock / delivery | Link |
| --- | --- | --- | --- |
| **Raspberry Pi 3 Model A+** | 26.90 | **Sofort-Versand ab Lager** | [pi-shop.ch](https://www.pi-shop.ch/raspberry-pi-3-model-a) |
| **Hammond 1590DD** | 27.91 | 8 in stock, 1–2 days, same-day pickup possible | [distrelec.ch](https://www.distrelec.ch/en/die-cast-enclosure-1590-188x120x37mm-die-cast-aluminium-natural-ip54-hammond-1590dd/p/15011796) |
| I2S MEMS mic module (MSM261S4030H0) | 8.90 | in stock | [bastelgarage](https://www.bastelgarage.ch/i2s-mikrofon-modul) |
| Speaker 4 Ω 3 W 40 mm (17 mm tall) | 8.90 | in stock | [bastelgarage](https://www.bastelgarage.ch/lautsprecher-4ohm-3w-40mm) |
| Magnetic door contact (reed + magnet) — lid switch and mic power switch | 4.90 | in stock | [bastelgarage](https://www.bastelgarage.ch/magnetischer-tur-fenster-kontakt) |
| Adafruit MAX98357A I2S amp | 9.95 | >10 at supplier, ~1 week | [galaxus](https://galaxus.ch/de/s1/product/adafruit-i2s-3w-class-d-amplifier-breakout-max98357a-erweiterung-elektronikmodul-5998646) |
| Adafruit NeoPixel ring 16 | 18.50 | **2 left** at supplier, ~1 week | [galaxus](https://www.galaxus.ch/en/s1/product/adafruit-neopixel-ring-16-x-ws2812-5050-rgb-led-diode-5998257) |
| Illuminated arcade button 33 mm | 14.90 | >10 (bastelgarage) | [galaxus](https://www.galaxus.ch/en/s1/product/purecrea-arcade-button-illuminated-33mm-green-buttons-switches-36704979) |
| microSD 32 GB A1, name-brand | ~10 | any shop, today | — |
| USB-C/micro-USB 5 V 2.5 A PSU ×2 | ~10 ea | any shop, today | — |
| 74AHCT125 level shifter (ring data at 5 V) | ~3 | bastelgarage / any | — |
| 2 × 3 mm LEDs, resistors, 2 × 10 kΩ | ~3 | any | — |

MAX98357A and the ring are the only phase-1 parts with a ~1-week lead; the
Bastelgarage MAX98357 clone (6.90) is out today. If a week is too long, the
Distrelec search for "MAX98357" is worth a look — they had Adafruit stock at
2-hour pickup for other items.

## LTE stick — phase 2, but here is what is in stock

| Part | CHF | Stock / delivery | Notes |
| --- | --- | --- | --- |
| **Huawei E8372 (HiLink, LTE + Wi-Fi)** | 89.90 | **1 in stock**, day after tomorrow | [galaxus](https://www.galaxus.ch/de/s1/product/huawei-e8372-lte-3g-datenstick-router-8929882). Linux `cdc_ether`, TS-9 antenna ports, Wi-Fi hotspot can be disabled. Works; over-priced for what we use. |
| Huawei E3372h-320 | — | **unavailable** at Digitec | [digitec](https://www.digitec.ch/de/s1/product/huawei-e3372h-320-router-5837158) — the classic choice, out |
| Brovi E3372-325 / ZTE MF79U | ~30–40 / 18.40 | **unverified** — Brack and Digitec result lists didn't render for automated reading | Check [brack.ch](https://www.brack.ch/search?query=surfstick) and Digitec by hand: Brack ships next day. Both are HiLink-class sticks. |

Plus, for the aluminium box: **Delock TS-9 → SMA adapter** 
([digitec](https://www.digitec.ch/de/s1/product/delock-antennenadapter-sma-ts-9-antennenkabel-antennenkabel-5829274), ~CHF 10)
and the **Delock hinged LTE stub antenna** (20.90, [digitec](https://www.digitec.ch/de/s1/product/delock-ltehspagsm-antenne-sma-stecker-mobilfunk-antenne-netzwerk-zubehoer-5833613)).
An SMA bulkhead coupler (CHF 3) carries it through the wall.

SIM: **Digital Republic Flat 1**, CHF 6/month, unlimited, no contract —
[digitalrepublic.ch/en/smart-devices](https://digitalrepublic.ch/en/smart-devices/).
Does not support Cat-M/NB-IoT (their support page) — irrelevant now: the
stick is ordinary LTE.

## Power — phase 3, buy after measuring

| Part | CHF | Stock / delivery | Link |
| --- | --- | --- | --- |
| **Adafruit PowerBoost 1000C** (1 A charge, 1 A 5 V boost, load-share) | 21.70 | **15 in stock, 2–5 days** | [berrybase.ch](https://www.berrybase.ch/adafruit-powerboost-1000) |
| — same, Digitec | 31.50 | 7 at supplier, ~1 week | [digitec](https://www.digitec.ch/en/s1/product/adafruit-powerboost-1000-charger-diode-5998514) |
| Adafruit PowerBoost 500C | 11.63 | 44 in stock, **2-hour pickup** | [distrelec](https://www.distrelec.ch/en/search?q=adafruit%201944) — 500 mA output: **too small for a Pi + stick** |
| Protected 18650 cells ×3–6 | ~15 ea | Conrad has Fenix ARB-L18 (branded, ~25–34, some "Oct 20"); Galaxus Purecrea unavailable; Distrelec search unhelpful | Consider ordering cells from BerryBase (DE, 2–5 days) with the PowerBoost |
| Fuel gauge: SparkFun LiPo Fuel Gauge (MAX17043) or Adafruit ADS1115 | ~10–18 | Digitec | [SparkFun](https://www.digitec.ch/de/s1/product/sparkfun-lipo-fuel-gauge-elektronikmodul-5999111) · [ADS1115](https://www.digitec.ch/en/s1/product/adafruit-ads1115-16-bit-adc-4-ch-wgain-amplifier-add-on-electronics-modules-5998565) |
| PiJuice Zero | — | **discontinued** at Distrelec | — |

Bench power today: any 5 V / 2.5 A USB PSU. A USB power bank works for
carrying a prototype around but most auto-off below ~100 mA and many drop the
output when the charger is plugged in — not the final answer.

## Totals

| | CHF |
| --- | --- |
| Order today (3A+, box, audio, lid, button, SD, PSUs, small parts) | ~150 |
| Phase 2 (stick 30–90, adapter, antenna, coupler) | ~65–125 + 6/month |
| Phase 3 (PowerBoost, cells, gauge) | ~90–130 |
| Zero 2 W when available | ~20–30 |
| **Total** | **~CHF 330–430 + CHF 6/month** |

More than the ESP32 plan (~225): the Pi itself is cheap, the cells and the
stick are not. It buys a box you can SSH into.
