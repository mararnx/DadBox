# Shopping List

The two-button box ([ADR 0016](../docs/decisions/0016-two-buttons-no-lid.md))
on a Pi Zero 2 W with a Cat-1 HAT
([ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md)): aluminium 1590DD
clone, small rigid antenna, off-the-shelf parts only, Flat 1 always. Every
part with its link and status is in [bom/bom.csv](bom/bom.csv); where things
come from is in [SOURCING.md](SOURCING.md). Prices CHF incl. VAT.

## Ordered

| Date | Shop | Item | CHF | Notes |
| --- | --- | --- | --- | --- |
| 2026-09-21 | Pi-Shop | [**Raspberry Pi Zero 2 W starter kit**](https://www.pi-shop.ch/raspberry-pi-zero-2-w-starter-kit) — board, 16 GB microSD, USB OTG host cable, 2×20 header (to solder), mini-HDMI adapter | 42.90 | The deployment board. The kit's card is the bench card; the OTG cable is the modem's |
| 2026-09-21 | Bastelgarage | [**Waveshare SIM7670G 4G LTE/GPS HAT**](https://www.bastelgarage.ch/sim7670g-4g-lte-gps-hat-fur-raspberry-pi) — Cat-1, bands 20 and 28, LTE antenna and USB cable included | 55.90 | With the part in hand: power-key wiring, that the USB Ethernet mode persists across reboots, which antenna connector it has |
| 2026-09-21 | Bastelgarage | [**16 mm stainless momentary button, raised head, RGB ring, 5 V**](https://www.bastelgarage.ch/16mm-drucktaster-erhoht-mit-rgb-beleuchtung-5v-edelstahl) × 2 | 19.90 ea | **One is Record, one is Play.** 16 mm hole, flange Ø21.8, ~20 mm behind the panel — wall **or** top plate, decide with the box in hand. Common cathode, resistors built in, works at 3.3 V: LEDs straight from GPIO |
| 2026-09-21 | Bastelgarage | [DFRobot I2S MEMS mic module](https://www.bastelgarage.ch/i2s-mikrofon-modul) (MSM261S4030H0) | 8.90 | Its 3.3 V supply shares a GPIO with the record button's red LED |
| 2026-09-21 | Bastelgarage | [Seeed 5 W 4 Ω speaker in plastic enclosure](https://www.bastelgarage.ch/5w-4ohm-lautsprecher-in-kunststoffgehause), 50 × 45 × 22 mm | 7.90 | |
| 2026-09-21 | Bastelgarage | MAX98357 I2S amp module — spare | 7.90 | Same chip as the Adafruit one; the shop lists it as "MAX98367" |
| 2026-09-21 | Galaxus | [Adafruit MAX98357A I2S amp](https://galaxus.ch/de/s1/product/adafruit-i2s-3w-class-d-amplifier-breakout-max98357a-erweiterung-elektronikmodul-5998646) | 9.95 | Delivery 28–29 Sep |
| 2026-09-21 | Galaxus | Raspberry Pi Debug Probe | 12.70 | UART console on GPIO 14/15 — `tools/serial_capture.py` |
| 2026-09-21 | Temu | **1590DD-size die-cast aluminium enclosure**, 188 × 119 × 37.5 mm | 12.94 | A clone, not the Hammond. **Measure the inside (length, width, depth, corner bosses) before any layout or drilling** — clones differ by a millimetre or two |
| 2026-09-21 | Temu | M35 cobalt step drill, 5–23 mm | 8.48 | Covers every hole in the box |
| 2026-09-21 | Temu | Cordless USB soldering iron set | 11.61 | Fine for headers and wires; add solder and flux if not in the set |
| 2026-09-21 | — | Jumper wires | — | Module-to-header wiring on the bench; something sturdier before the box travels in a bag |

In hand: the Digital Republic **Flat 1** SIM
([digitalrepublic.ch](https://digitalrepublic.ch/en/smart-devices/), CHF
6/month) and a 5 V micro-USB supply — `vcgencmd get_throttled` tells if it
sags. Temu order total CHF 12.69 after credit.

## Still to buy

### After the modem HAT arrives

Confirm the HAT's antenna connector first, then order all three together.

| Qty | Part | CHF | Source |
| --- | --- | --- | --- |
| 1 | Delock 88747 SMA bulkhead → MHF/U.FL pigtail | 7.32 | [Reichelt CH](https://www.reichelt.com/ch/de/shop/produkt/wlan_kabel_sma_einbaubuchse_mhf_u_fl-179772) |
| 1 | **Delock 90694** rigid LTE stub, 52 mm | 8.24 | [Reichelt CH](https://www.reichelt.com/ch/de/shop/produkt/lte_antenne_sma_stecker_omnidirektional_starr-426541) |
| 1 | Delock 90682 rigid LTE antenna, 115 mm, 700–2700 MHz — comparison / fallback | 9.16 | [Reichelt CH](https://www.reichelt.com/ch/de/shop/produkt/lte_antenne_sma_stecker_omnidirektional_starr-426542) |

The short stub's datasheet range (824–960 / 1710–2170 MHz) starts above the
band 20 downlink, 791–821 MHz. `AT+CSQ` in both bedrooms with each antenna
decides; keep whichever holds signal. **Check Sunrise 4G in both bedrooms
first.**

### Deferred — battery ([ADR 0019](../docs/decisions/0019-mains-first-battery-deferred.md): the first box is mains only)

| Qty | Part | CHF | Source |
| --- | --- | --- | --- |
| 1 | **Waveshare UPS Module 3S** — 3 × 18650 in series, 5 V 5 A, charges while powering, INA219, case and 12.6 V 2 A supply included; 93 × 86 mm. **Barrel-jack charger, not USB** | 25.90 | [Bastelgarage](https://www.bastelgarage.ch/ups-usv-modul-5v-5a-unterbrechungsfreies-18650-akkuboard) |
| 3 | Panasonic NCR18650GA 3300 mAh, protected — same batch, same charge state; check the module's holders take 69.5 mm cells | 13.90 ea | [Bastelgarage](https://www.bastelgarage.ch/batterien-lipo-akkus/li-ion-akku-ncr18650ga-3300mah-mit-pcm-schutzelektronik-und-stecker) |
| 1 | Second 12.6 V 2 A (3S Li-ion) charger for house B | ~12 | any — match the plug with the first one in hand |
| 1 | Panel-mount DC barrel jack, round hole — the charge port through the wall | ~4 | any — buy with the UPS module in hand |

### Before drilling — the fixing kit ([ADR 0023](../docs/decisions/0023-enclosure-layout.md), [LAYOUT.md](LAYOUT.md))

All off the shelf; rows FX1–FX7, T3, P2, C1–2 in the BOM.

| Item | CHF | Where |
| --- | --- | --- |
| M2.5 nylon standoff, screw and nut assortment | ~12 | Bastelgarage / Galaxus |
| 3M VHB or 2 mm double-sided foam tape | ~10 | Hornbach / Galaxus |
| Closed-cell EVA foam, 10 mm | ~6 | craft shop / Hornbach |
| Adhesive cable-tie mounts + small ties | ~6 | Hornbach |
| Silicone wire 26 AWG + heat-shrink | ~18 | Bastelgarage |
| Medium threadlocker | ~9 | Hornbach |
| Kapton tape or a plastic sheet | ~6 | Bastelgarage / stationery |
| Twist drills 2 / 2.7 / 3 mm, centre punch, deburring tool, half-round file | ~23 | Hornbach |
| USB-C panel socket with a 30 cm tail to a USB-C plug — [Exsys EX-49222](https://www.exsys.ch/einbau-adapter-usb-c-buchse-zu-stecker-usb-3.2-gen-2-30-cm-EX-49222), 22.3–24 mm hole. **Not** the socket-to-socket EX-49195 in hand: it powers the box one way up only | 16.90 | exsys.ch |
| USB-C socket → micro-USB plug adapter (the tail to the Pi's PWR IN) — Delock 65927. Test it straight on the USB-C supply first: Pi boots = it has the CC resistors | ~8 | [Brack](https://www.brack.ch/delock-usb-2-0-adapter-usb-c-buchse--microb-usb-stecker-819951) |
| Short micro-USB → USB-C lead, Pi→HAT, [ordered 2026-09-25](https://www.galaxus.ch/en/s1/product/delock-usb-c-micro-usb-b-014-m-usb-20-usb-cables-17956770) (Delock, 0.14 m) | ~12 | any |

### Before the box leaves home

| Qty | Part | CHF | Source |
| --- | --- | --- | --- |
| 1 | SanDisk High Endurance 32 GB microSD — the deployed card; the bench card becomes the spare image | 22.95 | [Brack](https://www.brack.ch/sandisk-microsdhc-karte-high-endurance-uhs-i-32-gb-935760) |
| — | Rubber feet, self-adhesive | ~5 | [Hornbach](https://www.hornbach.ch/de/p/tarrox-rutsch-laermschutzpuffer-selbstklebend-transparent-o-10-x-3-mm-32-stueck/10565335/) |
| 2 | 3 mm LEDs + 220 Ω for LINK and POWER | ~2 | any / drawer |

Round holes only — positions and sizes in [LAYOUT.md](LAYOUT.md), 1:1 templates in `cad/`. No hole saw.

Parts considered and dropped are in [EVALUATION.md](EVALUATION.md) and ADRs
[0014](../docs/decisions/0014-raspberry-pi-zero-2w.md) and
[0016](../docs/decisions/0016-two-buttons-no-lid.md).
