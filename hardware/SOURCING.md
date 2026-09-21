# Sourcing — where things come from

One table per shop for the current parts. Status, reasons and refs are in
[bom/bom.csv](bom/bom.csv); what is ordered and what waits is in
[SHOPPING-LIST.md](SHOPPING-LIST.md); the alternatives that were weighed are
in [EVALUATION.md](EVALUATION.md). Prices CHF incl. VAT as seen on
2026-09-21; stock changes daily.

## Pi-Shop — [pi-shop.ch](https://www.pi-shop.ch)

| Part | CHF |
| --- | --- |
| [Raspberry Pi Zero 2 W starter kit](https://www.pi-shop.ch/raspberry-pi-zero-2-w-starter-kit) — board, 16 GB microSD, OTG cable, header | 42.90 |
| [Official Pi 12.5 W micro-USB PSU](https://www.pi-shop.ch/raspberry-pi-12-5w-micro-usb-power-supply-2254) — only if the supply in hand sags | 11.90 |

## Bastelgarage — [bastelgarage.ch](https://www.bastelgarage.ch)

| Part | CHF |
| --- | --- |
| [Waveshare SIM7670G 4G LTE/GPS HAT](https://www.bastelgarage.ch/sim7670g-4g-lte-gps-hat-fur-raspberry-pi) | 55.90 |
| [16 mm stainless RGB button, raised head](https://www.bastelgarage.ch/16mm-drucktaster-erhoht-mit-rgb-beleuchtung-5v-edelstahl) × 2 | 19.90 ea |
| [DFRobot I2S MEMS mic module](https://www.bastelgarage.ch/i2s-mikrofon-modul) | 8.90 |
| [Seeed 5 W 4 Ω speaker in plastic enclosure](https://www.bastelgarage.ch/5w-4ohm-lautsprecher-in-kunststoffgehause) | 7.90 |
| MAX98357 I2S amp module (spare; listed as "MAX98367") | 7.90 |
| [Waveshare UPS Module 3S](https://www.bastelgarage.ch/ups-usv-modul-5v-5a-unterbrechungsfreies-18650-akkuboard) — phase 3 | 25.90 |
| [Panasonic NCR18650GA 3300 mAh protected](https://www.bastelgarage.ch/batterien-lipo-akkus/li-ion-akku-ncr18650ga-3300mah-mit-pcm-schutzelektronik-und-stecker) × 3 — phase 3 | 13.90 ea |

## Galaxus — [galaxus.ch](https://www.galaxus.ch)

| Part | CHF |
| --- | --- |
| [Adafruit MAX98357A I2S amp](https://galaxus.ch/de/s1/product/adafruit-i2s-3w-class-d-amplifier-breakout-max98357a-erweiterung-elektronikmodul-5998646) — ~1 week | 9.95 |
| Raspberry Pi Debug Probe | 12.70 |

## Reichelt CH — [reichelt.com/ch](https://www.reichelt.com/ch/)

| Part | CHF |
| --- | --- |
| [Delock 88747 SMA bulkhead → MHF/U.FL pigtail](https://www.reichelt.com/ch/de/shop/produkt/wlan_kabel_sma_einbaubuchse_mhf_u_fl-179772) | 7.32 |
| [Delock 90694 rigid LTE stub, 52 mm](https://www.reichelt.com/ch/de/shop/produkt/lte_antenne_sma_stecker_omnidirektional_starr-426541) | 8.24 |
| [Delock 90682 rigid LTE antenna, 115 mm](https://www.reichelt.com/ch/de/shop/produkt/lte_antenne_sma_stecker_omnidirektional_starr-426542) | 9.16 |

## Temu, Brack, Hornbach, Digital Republic

| Shop | Part | CHF |
| --- | --- | --- |
| Temu | 1590DD-size die-cast aluminium enclosure (clone), 188 × 119 × 37.5 mm | 12.94 |
| Temu | M35 cobalt step drill, 5–23 mm | 8.48 |
| Temu | Cordless USB soldering iron set | 11.61 |
| Brack | [SanDisk High Endurance 32 GB microSD](https://www.brack.ch/sandisk-microsdhc-karte-high-endurance-uhs-i-32-gb-935760) | 22.95 |
| Hornbach | [Self-adhesive rubber feet](https://www.hornbach.ch/de/p/tarrox-rutsch-laermschutzpuffer-selbstklebend-transparent-o-10-x-3-mm-32-stueck/10565335/) | ~5 |
| Digital Republic | [Flat 1 data SIM](https://digitalrepublic.ch/en/smart-devices/) — unlimited, 1 / 0.5 Mbit/s, Sunrise network, no contract | 6 / month |

Any shop: 2 × 3 mm LEDs + 220 Ω, the second 12.6 V 2 A charger and the
panel-mount DC jack — the last two are matched to the UPS module's plug with
the module in hand.

## Worth knowing

- **Pi Zero 2 W bare boards are out of stock across Europe.** The Pi-Shop
  starter kit was in stock on 2026-09-21; that is why the kit was bought.
- **Galaxus sometimes resells Bastelgarage stock at a markup** — the DFRobot
  mic was 16.90 there against 8.90 at Bastelgarage. Check Bastelgarage first.
- **Bastelgarage's generic 4-channel logic level converter** is rated
  28.8 kbit/s and cannot drive LEDs. If the button LEDs are too dim at 3.3 V,
  the answer is two 74AHCT125, not that board.
- **Bastelgarage's 3-slot 18650 holder takes 65–66 mm cells only**; protected
  cells are 69.5 mm. Check the UPS module's holders before buying cells.
- **Digitec, Galaxus, Distrelec and Brack pages block automated fetches.**
  Prices and stock there must be checked in a browser.
- **Temu enclosures are clones.** Hammond's 1590DD is ~183 × 113–115 × 32–33
  inside; measure this one before layout or drilling.
- **Swiss consumer SIMs are plain LTE** — no LTE-M or NB-IoT (ADR 0013). Any
  SIM7080G-class board is a dead end.
