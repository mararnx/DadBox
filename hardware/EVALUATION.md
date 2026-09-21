# Hardware evaluation from scratch — 2026-09-20

A clean-sheet evaluation of what DadBox needs and what is buyable in Switzerland
this week. Derived only from the functional brief (lid, one button, ring, cellular,
weekend on battery, nothing lost, Claude Code develops on it). Prior part choices
were deliberately not consulted; where the result agrees with them, that is
convergence, not inheritance.

Prices are CHF incl. VAT as seen on 2026-09-20 unless marked. "Verified" means a
second pass fetched the shop page and confirmed name, price and stock text; a
handful of Digitec/Galaxus/Distrelec/Brack pages that block automated fetches
were checked by hand in a browser the same evening (marked *browser*).

## 1. What the hardware must do

| # | Requirement | Hardware consequence |
| --- | --- | --- |
| 1 | Lid open = mic on, physically | Reed/hall/microswitch in the mic's 3.3 V feed **and** read by a GPIO |
| 2 | 16 kHz mono, 5 min, on disk while talking; Opus after | I2S MEMS mic; persistent, journaled storage; enough CPU for Opus offline |
| 3 | ~3 W playback + chime, amp with shutdown | I2S class-D amp with SD pin; 40–50 mm full-range speaker |
| 4 | 16-LED ring, gated to 0 mA; two status LEDs | WS2812 ring on a switched 5 V rail; 3.3→5 V shifter; 2 GPIO LEDs |
| 5 | Never lose a recording | ext4 + fsync/rename (Linux) or an append-only CRC log (MCU); high-endurance card |
| 6 | Cellular, own server, modem gated between check-ins | LTE **Cat-1/Cat-4** (no Swiss consumer SIM exposes LTE-M/NB-IoT); a GPIO on the modem's supply or PWRKEY |
| 7 | 60 h unplugged, charge overnight while running, gauge, cutoff | Load-sharing charger/UPS, 1S Li-ion pack, I2C gauge |
| 8 | Quiet hours on device | Network time; RTC optional |
| 9 | Claude Code develops on it | Linux + SSH over Tailscale is the strong preference; MCU is serial-only |
| 10 | Rugged hinged box, round holes, 45 mm ring window | See §5 |

## 2. Facts that settle things (verified today)

- **Radio tech.** Swiss consumer data SIMs are plain LTE. Digital Republic's support
  page says Cat-M1/NB-IoT are not supported; LTE-M is only sold on business IoT
  contracts (Swisscom CMP CHF 49/month platform fee). 2G is gone, Swisscom and
  Sunrise 3G ended end-2025. So: **LTE Cat-1 (bis) or Cat-4 modules only.** Any
  SIM7080G/LTE-M board is a dead end.
- **SIM.** [Digital Republic Flat 0.4 / 1 / 10](https://digitalrepublic.ch/en/smart-devices/)
  at CHF 4 / 6 / 10 per month, unlimited but speed-capped, free SIM or eSIM, CHF 0
  activation, no minimum term (verified). Runs on Sunrise. A 600 KB message takes
  ~30 s at 0.2 Mbit/s up; fine for the box, slow for a Tailscale session, so develop
  on Flat 10 and drop to Flat 1 in the field (tier changes month to month). Every
  Swiss SIM needs an online ID check. Fallbacks on Swisscom's network:
  [Mucho DATAMINI](https://muchomobile.ch/de/prepaid/schweiz-europa-internet/datamini)
  CHF 9.90/30 days (page shows 5 GB), Swisscom Prepaid Plus CHF 5/30 days at 128 kbit/s.
- **Raspberry Pi Zero 2 W is not buyable this week.** Pi-Shop.ch, BerryBase CH,
  Bastelgarage, Pimoroni, Pi Hut, Adafruit: out of stock. Reichelt CH: ETA 6 March
  2027. [Welectron](https://www.welectron.com/Raspberry-Pi-Zero-2-W) EUR 19.90 "im
  Zulauf" (verified). Digitec marketplace *browser*: CHF 50.70, delivery
  15 Jan–1 Feb 2027. The **[Pi 3 Model A+](https://www.pi-shop.ch/raspberry-pi-3-model-a)**
  is on the shelf (CHF 26.90, "Sofort-Versand ab Lager", verified), boots the same
  image with the same overlays and GPIO map, but idles at ~2× the current.
- **Other Linux boards** fail on software, not price: Orange Pi Zero 2W / Banana Pi
  M4 Zero have no working I2S in Armbian; Radxa Zero 3W only from Hong Kong and
  the eMMC variants are sold out; Luckfox Lyra Zero W is Buildroot-only; Pi 3B+/4/5
  idle at 2–3 W (110–160 Wh per weekend).
- **Audio.** One duplex I2S overlay (`googlevoicehat-soundcard`, in-tree in
  rpi-6.12) gives mic capture and MAX98357A playback on one bus with the amp's
  SD_MODE on GPIO16. Do not load `max98357a` alongside it. Because I2S takes
  GPIO18–21, the ring must be driven from **SPI0 MOSI (GPIO10)** with rpi_ws281x.
  Audio HATs with WM8960 are out-of-tree DKMS and cannot gate the mic; the Codec
  Zero's onboard mic cannot be lid-switched either.
- **Ring.** The only 16-LED ring that fits a 45 mm window and is on a Swiss shelf is
  the Adafruit 44.5 mm NeoPixel (2 pcs at Play-Zone, 2 at BerryBase, RGBW variant
  15 at BerryBase). Generic 16-rings are 68–70 mm. WS2812 DIN needs ≥3.5 V: use an
  SN74AHCT125 and tie its /OE to the ring's gate GPIO. Dark current ~10–16 mA per
  ring, so the 5 V rail must be switched high-side.
- **Cells.** 18650 protected Panasonic NCR18650GA 3300 mAh with JST lead at
  Bastelgarage (CHF 13.90, in stock). Bastelgarage's 3-slot holder only takes
  65–66 mm cells; protected cells are 69.5 mm, so use the **4-slot holder**
  (77.5 × 79.4 × 22.3 mm) or the single leaded holders.
- **Enclosure.** Hammond 1590DD *browser*: Distrelec CHF 25.82 excl. VAT, 8 in stock,
  1–2 days. Inside ≈ 183 × 115 × 33 mm (from the Hammond drawing; confirm before
  drilling). Aluminium is a Faraday cage: antenna outside via an SMA bulkhead.
  ABS alternative with real height: Hammond 1591USBK 120 × 120 × 59 mm, Distrelec
  CHF 8.55 excl. VAT, 31 in stock *browser*; ABS is RF-transparent, so the modem's
  own stub antenna can stay inside. Wooden hinged box (CreaDiva 30 × 20 × 13.5 cm,
  Galaxus CHF 35.95, 10 in stock *browser*) if a child-friendly look matters more
  than compactness.

## 3. Power arithmetic used below

Weekend = 60 h. Cells nominal 3.6 V, boost efficiency 88 %, 20 % margin:

```
Ah needed ≈ I_avg(A at 5 V) × 60 h × 5 V ÷ (3.6 V × 0.88) × 1.2  =  I_avg × 114
```

| Average draw at 5 V | Ah with margin | Protected 3.3 Ah cells |
| --- | --- | --- |
| 100 mA | 11.4 | 4 (3 gives ~52 h) |
| 125 mA | 14.2 | 5 (4 gives ~56 h) |
| 200 mA (Pi 3A+) | 22.8 | 7 — not a weekend box |
| 15 mA at 3.7 V (MCU lane) | 1.1 | 1 |

Modem duty at 10-minute polls: ~30 s on per poll = 5 %. A USB stick at ~350 mA →
~18 mA average; a Cat-1 module at ~150 mA → ~8 mA. Halving the poll rate halves it.

## 4. The three options

### Option A — Linux + USB 4G stick, hand-wired breakouts ("classic")

**Thesis.** The box is a Debian machine with an Ethernet interface that happens to
be cellular. Claude Code gets SSH, journalctl, ALSA and Python; the modem needs no
AT commands. Cost: one hand-modified USB cable to gate the stick, and a stick that
is a consumer product (mode-switch quirks on ARM).

| Group | Part | Vendor / link | CHF | Stock (2026-09-20) |
| --- | --- | --- | --- | --- |
| Compute (now) | Raspberry Pi 3 Model A+ | [Pi-Shop.ch](https://www.pi-shop.ch/raspberry-pi-3-model-a) | 26.90 | ab Lager, verified |
| Compute (target) | Raspberry Pi Zero 2 W | [Welectron](https://www.welectron.com/Raspberry-Pi-Zero-2-W) · [Pi-Shop notify](https://www.pi-shop.ch/raspberry-pi-zero-2-w) | EUR 19.90 | incoming, verified |
| Modem | ZTE MF79U Cat-4 HiLink stick, 2× TS-9 | [Reichelt CH](https://www.reichelt.com/ch/de/shop/produkt/surfstick_4g_lte_usb_weiss-344252) | 32.01 | ab Lager, 3–4 days, verified |
| Modem alt | Huawei/Brovi E3372-325 (CRC-9 ports, needs a CRC-9→SMA pigtail) | [Galaxus](https://www.galaxus.ch/en/s1/product/huawei-e3372-325-routers-24422582) · [Reichelt](https://www.reichelt.com/ch/de/shop/produkt/surfstick_4g_lte_usb_weiss_mobilfunknetzwerkmodem-439722) | 33.50 / 40.86 | Galaxus 25–26 Sep *browser*; Reichelt ab Lager |
| Antenna | Delock 88487 SMA bulkhead → TS-9 pigtail | [Reichelt CH](https://www.reichelt.com/ch/de/shop/produkt/wlan_kabel_sma_einbaubuchse_ts-9-179748) | 8.29 | ab Lager |
| Antenna | Delock 12635 hinged LTE stub, SMA | [Reichelt CH](https://www.reichelt.com/ch/de/shop/produkt/antenne_lte_sma_stecker_omnidirektional_kippgelenk-281035) | 24.12 | ab Lager |
| Modem gate | Pololu 2811 high-side MOSFET switch (SV), 2 A | [Botland](https://botland.store/digital-switches/4853-mini-switch-slide-mosfet-sv-45-40v4a-with-protection-before-reverse-current-pololu-2811-5904422300050.html) | EUR 3.50 | 24 h, EU |
| Modem cable | Short micro-USB OTG cable (Zero 2 W) with VBUS cut and routed through the Pololu switch | any shop | ~5 | unverified |
| Power | Waveshare UPS HAT (C): load-sharing, 1.8 A boost, INA219 gauge | [Pi-Shop.ch](https://www.pi-shop.ch/uninterruptible-power-supply-ups-hat-for-raspberry-pi-zero) | 25.90 | ab Lager, verified |
| Power alt | bq24074 charger 1.5 A + Pololu S13V30F5 5 V/3 A + MAX17048 gauge | [Pi-Shop](https://www.pi-shop.ch/adafruit-universal-usb-dc-solar-lithium-ion-polymer-charger-bq24074) · [Botland](https://botland.store/converters-step-up-step-down/19768-step-upstep-down-voltage-regulator-s13v30f5-5v-3a-pololu-4082-5904422347529.html) · [Pi-Shop](https://www.pi-shop.ch/adafruit-max17048-lipoly-liion-fuel-gauge-and-battery-monitor-stemma-jst-ph-qt-qwiic) | 21.80 + EUR 14.50 + 9.90 | all in stock, verified |
| Cells | 4× Panasonic NCR18650GA 3300 mAh protected, JST lead | [Bastelgarage](https://www.bastelgarage.ch/batterien-lipo-akkus/li-ion-akku-ncr18650ga-3300mah-mit-pcm-schutzelektronik-und-stecker) | 55.60 | Lagernd |
| Holder | 4-slot 18650 holder (65–70 mm cells) | [Bastelgarage](https://www.bastelgarage.ch/4-fach-18650-batteriefach-batteriehalter) | 4.90 | Lagernd |
| Mic | INMP441 I2S MEMS module | [BerryBase CH](https://www.berrybase.ch/inmp441-mems-omnidirektionales-mikrofonmodul-i2s-interface) | 3.10 | 100+, verified |
| Mic alt | Adafruit SPH0645 | [Play-Zone](https://www.play-zone.ch/de/adafruit-i2s-mems-microphone-breakout-sph0645lm4h.html) | 9.90 | >20, verified |
| Amp | Adafruit MAX98357A I2S 3 W | [Play-Zone](https://www.play-zone.ch/de/adafruit-i2s-3w-class-d-amplifier-breakout-max98357a.html) | 8.90 | >20, verified |
| Speaker | 4 Ω 3 W Ø40 × 17 mm | [Bastelgarage](https://www.bastelgarage.ch/lautsprecher-4ohm-3w-40mm) | 8.90 | Lagernd |
| Ring | Adafruit NeoPixel Ring 16 (44.5 mm) | [Play-Zone](https://www.play-zone.ch/de/adafruit-neopixel-ring-16-x-ws2812-5050-rgb-led.html) · [BerryBase RGBW](https://www.berrybase.ch/en/adafruit-neopixel-ring-16-x-5050-rgbw-leds-with-integrated-drivers-cool-white) | 14.90 / 10.80 | 2 pcs / 15 pcs |
| Shifter | SN74AHCT125N | [BerryBase CH](https://www.berrybase.ch/en/sn74ahct125n-quad-level-shifter-dil-14) | 0.50 | 100+, verified |
| Ring gate | second Pololu 2811, or IRLML6402 + adapter | Botland / [Reichelt](https://www.reichelt.com/ch/de/shop/produkt/mosfet_p-ch_-20v_-3_7a_0_065r_sot-23-108743) | EUR 3.50 / 1.35 | in stock |
| Lid | DFRobot reed door contact + magnet (mic VDD in series, GPIO via 100 k) | [Bastelgarage](https://www.bastelgarage.ch/dfrobot-magnetschalter-tur-fenster-kontakt) | 7.90 | Lagernd, verified |
| Magnets | 8 × 3 mm N45 discs, 10 pack (catch + actuator) | [supermagnete](https://www.supermagnete.ch/scheibenmagnete-neodym/scheibenmagnet-8mm-3mm_S-08-03-N) | 4.10 | 1–2 days |
| Button | 16 mm stainless flush momentary, RGB ring, IP65 (20 mm behind panel) | [Bastelgarage](https://www.bastelgarage.ch/bauteile/schalter-taster/16mm-drucktaster-mit-rgb-beleuchtung-5v-edelstahl) | 19.90 | Lagernd |
| Status LEDs | 3 mm assortment + resistors | Play-Zone / Reichelt | ~5 | in stock |
| Storage | SanDisk High Endurance 32 GB ×2 (one spare) | [Brack](https://www.brack.ch/sandisk-microsdhc-karte-high-endurance-uhs-i-32-gb-935760) | 45.90 | 41 in stock |
| PSU | Official Pi 12.5 W micro-USB ×2 (one per home) | [Pi-Shop](https://www.pi-shop.ch/raspberry-pi-12-5w-micro-usb-power-supply-2254) | 23.80 | ab Lager |
| Port | Adafruit USB-C round panel-mount extension (12–18 mm hole) + C→micro-B adapter | [BerryBase CH](https://www.berrybase.ch/en/adafruit-usb-c-panel-mount-verlaengerungskabel-rund-mit-gewinde-und-schutzkappe-30cm) | 1.75 + ~5 | 20 pcs |
| Enclosure | Hammond 1590DD die-cast | [Distrelec](https://www.distrelec.ch/en/search?q=hammond%201590DD) | 27.90 | 8 in stock *browser* |
| Mechanical | opal acrylic 3 mm (ring window), piano hinge, rubber feet | [Hornbach](https://www.hornbach.ch/de/p/acrylcolorplatte-glatt-opal-500-x-250-x-3-mm/8055677/) · [hinge](https://www.hornbach.ch/de/p/stangenscharnier-32x400-mm-vermessingt/10485654/) · [feet](https://www.hornbach.ch/de/p/tarrox-rutsch-laermschutzpuffer-selbstklebend-transparent-o-10-x-3-mm-32-stueck/10565335/) | 17.05 | in stock |
| SIM | Digital Republic Flat 1 | [digitalrepublic.ch](https://digitalrepublic.ch/en/smart-devices/) | 6 / month | free SIM |

**Total ≈ CHF 385** (with 4 cells, two cards, two PSUs). Bench subset to reach
"records and plays back": Pi 3A+, mic, amp, speaker, reed, card, PSU ≈ CHF 95.

**Compatibility.** I2S on GPIO18/19/20/21, amp SD on GPIO16, ring on GPIO10 via
AHCT125 (/OE tied to the ring-gate GPIO), reed in series with the mic's 3V3 (mic
≤1.4 mA; contact rated 50 mA), INA219 at 0x43 on I2C. Stick: `usb_modeswitch` then
`cdc_ether`, DHCP from 192.168.0.1 (ZTE). On a Zero 2 W the stick hangs off the OTG
port (`dwc2`, `dr_mode=host`); on a 3A+ it plugs straight in. Gating the stick's
VBUS with the Pololu switch is the one hand-made cable. MF79U's Wi-Fi hotspot must
be disabled in its web UI or it costs ~100 mA.

**Fit in the 1590DD (inside ≈ 183 × 115 × 33).** Base: 4-cell holder 78 × 79 × 22
along the back; Zero 2 W + UPS HAT stack 65 × 30 × ~17 beside it; stick 102 × 32 × 14
flat along the front; amp/mic/shifter on a small perfboard. Lid: ring (Ø44.5 × 2.5)
under the 45 mm window, speaker Ø40 × 17 cone-up beside the ring, over the Pi stack
(17 + 17 = 34 mm — **marginal**; put the speaker over the stick side, 14 + 17 = 31).
Button 16 mm through the front wall (needs 20 mm behind panel: OK). SMA bulkhead
(6.5 mm hole) back wall, USB-C (12–18 mm) front wall. Round holes only. With a 3A+
(65 × 56) everything still lies flat but the stick's 100 mm plus the board's 65 mm
must run the long way. Verdict: fits, with 2–3 mm to spare in height.

**Power.** Zero 2 W 100 mA + stick 18 mA + ring resting 2 mA + gauge/LEDs 5 mA ≈
125 mA → 14 Ah with margin → **4 cells gives ~56 h, 5 cells the full margin**;
30-minute polls bring 4 cells to ~62 h. On the 3A+: ~225 mA → not a weekend box;
bench and plugged-in use only. Charging 13 Ah at the UPS HAT's ~1 A ≈ 14 h (the
HAT's charge current is not published: measure); the bq24074 at 1.5 A ≈ 10 h. Peak:
Pi boot ~1 A + stick 0.7 A + amp 0.8 A can exceed the UPS HAT's 1.8 A if software
plays audio while uploading right after boot; sequence it, or take the 3 A modular
path.

**Dev loop.** Raspberry Pi Imager → SSH → `rsync` + `systemctl restart` +
`journalctl`; Tailscale over the stick in the field; `ip a`, `curl` and the stick's
web UI for link state; `arecord`/`aplay` for audio; INA219 over I2C for the budget.

**Risks.** Zero 2 W lead time (weeks to months); stick mode-switch flakiness on
ARM (E3372-325 more than MF79U); marketplace stock at Galaxus; NeoPixel ring
only 2 in stock at each Swiss shop (order first).

### Option B — ESP32-S3 with an integrated LTE Cat-1 module (lowest power)

**Thesis.** One board carries the MCU, the SIM7670G Cat-1 modem, an 18650 holder,
a charger, a MAX17048 gauge and a TF slot. It sleeps between events, so a single
cell lasts the weekend several times over. The price is the dev loop: no SSH, no
shell, `idf.py flash/monitor` over USB on the bench, and whatever log upload the
firmware implements in the field. Opus on the S3 is proven but takes 1–3.5 min
per 5-minute message after the lid closes.

| Group | Part | Vendor / link | CHF | Stock |
| --- | --- | --- | --- | --- |
| Board | Waveshare ESP32-S3-SIM7670G-4G (18650 holder, ETA6098 charger, MAX17048, TF slot, DIP-switchable modem supply) | [Pi-Shop.ch](https://www.pi-shop.ch/esp32-s3-sim7670g-4g-development-board) | 58.90 | ab Lager, verified |
| Board alt | LILYGO T-A7670E R2 (ESP32-WROVER, GPIO12 modem switch) | [ShopOfThings](https://shopofthings.ch/shop/prototyping/iot-module/lilygo-ttgo-t-sim-a7670e-esp32-lte-gps-dev-board/) | ~69 | 3 in stock |
| DIY alt | ESP32-S3-DEV-KIT-N16R8 + Pimoroni Clipper A7683E Cat-1bis breakout (SMA, runs from the cell, 0.12–1.6 mA sleep) | [Bastelgarage](https://www.bastelgarage.ch/esp32-s3-dev-kit-n16r8-entwicklungsboard) · [Pi-Shop](https://www.pi-shop.ch/clipper-lte-4g-breakout-sp-ce-board-only) | 18.90 + 21.90 | both verified |
| Cell | 1× NCR18650GA 3300 mAh protected (fits the on-board holder; check length 69.5 mm) | Bastelgarage (link above) | 13.90 | Lagernd |
| Audio | INMP441 + MAX98357A + Ø40 speaker (same as A) | as above | 20.90 | in stock |
| Ring | NeoPixel 16 + SN74AHCT125 + Pololu 2811 gate | as above | ~19 | in stock |
| Lid / button / LEDs / magnets | same as A | as above | ~37 | in stock |
| Storage | SanDisk Extreme A1 32 GB (TF slot) | [BerryBase CH](https://www.berrybase.ch/en/sandisk-extreme-micro-sdhc-a1-uhs-i-u3-memory-card-adapter-32gb) | 18.90 | 100+ |
| PSU | Official Pi 15 W USB-C ×2 | [Pi-Shop](https://www.pi-shop.ch/raspberry-pi-15w-power-supply-eu-schwarz) | 19.80 | ab Lager |
| Port | USB-C panel-mount extension | BerryBase (above) | 1.75 | 20 pcs |
| Enclosure | Hammond 1591USBK ABS 120 × 120 × 59 (antenna inside) — or 1590DD + Delock 88747 IPEX→SMA pigtail + 12635 antenna | [Distrelec](https://www.distrelec.ch/en/search?q=hammond%201591) · [pigtail](https://www.reichelt.com/ch/de/shop/produkt/wlan_kabel_sma_einbaubuchse_mhf_u_fl-179772) | 9.25 (or 27.90 + 31.44) | 31 in stock *browser* |
| Mechanical | acrylic, hinge, feet | Hornbach (above) | 17.05 | in stock |
| SIM | Digital Republic Flat 1 | as above | 6 / month | — |

**Total ≈ CHF 215 in ABS, ≈ CHF 265 in aluminium.**

**Compatibility.** Two I2S controllers on the S3 (mic and amp on one full-duplex
port), RMT drives the ring, GPIO wake from the lid switch (EXT1) and the button.
SIM7670G supply is DIP/GPIO switchable on the board (real power gate). Mic VDD
through the reed as in A. MAX17048 on I2C (V1/V2 pin revisions differ). **Caveat:**
Pi-Shop's text says S3R2 (2 MB PSRAM) while Waveshare's page says S3R8: ask which
ships; 2 MB still fits micro-opus (~150 KB) plus the PCM ring buffer.

**Fit.** Board 110 × 30 with the cell holder under it (~22 mm tall) fits either box.
In the 1591USBK (inside ≈ 114 × 114 × 55) with the ring and speaker under the lid,
there is room to spare; in the 1590DD the 110 mm board runs the long way.

**Power.** Light-sleep MCU ~3 mA, modem off 0.1 mA, poll bursts ~8 mA, ring resting
2 mA → ~15 mA at 3.7 V → 0.9 Ah per weekend; one 3.3 Ah cell = ~200 h. Charge from
USB-C in ~4–7 h at 0.5–1 A. Peak: SIM7670G bursts ~2 A from the cell — keep the cell
fitted even on USB.

**Dev loop.** ESP-IDF v6.1 on the Mac; `idf.py flash` and scripted `tio` serial
capture are what Claude sees; light/deep sleep kills the USB-Serial-JTAG console,
so field debugging is log-upload only. Unit tests via the IDF Linux target or a
portable C core. OTA over cellular with `esp_https_ota`.

**Risks.** Never-lost rule is weaker (FAT on SD is not journaled; needs an
append-only record with CRC and a recovery scan); PSRAM revision ambiguity;
Claude cannot poke a sleeping device; every hardware observation goes through you.

### Option C — Linux + LTE Cat-1 HAT + UPS HAT (most integrated Linux build)

**Thesis.** Same Linux dev loop as A, but the modem is a Raspberry Pi HAT with a
documented PWRKEY and an AT port (Claude reads signal quality over SSH), the power
section stacks under the Pi, and there is no hand-modified USB cable. Everything
except the Zero 2 W is on a Swiss shelf today. Cat-1 draws less than a Cat-4 stick.

| Group | Part | Vendor / link | CHF | Stock |
| --- | --- | --- | --- | --- |
| Compute (now / target) | Pi 3 Model A+ now; Pi Zero 2 W on backorder | as in A | 26.90 / EUR 19.90 | verified |
| Modem | Waveshare A7670E LTE Cat-1 HAT (pHAT 65 × 30.5, USB-C to the Pi, UART + PWRKEY on the header, SMA stub antenna included) | [Pi-Shop.ch](https://www.pi-shop.ch/a7670e-lte-cat-1-hat-for-raspberry-pi-multi-band-2g-gsm-gprs-lbs-for-europe-southeast-asia-west-asia-africa-china-south-korea) | 34.90 | ab Lager, verified |
| Modem alt | Waveshare SIM7600G-H 4G HAT (B): pogo-pins onto a Zero's USB pads, on-board hub, Cat-4, GNSS | [BerryBase CH](https://www.berrybase.ch/sim7600g-h-4g-hat-b-fuer-raspberry-pi-mobilfunk-und-gnss) | 63.50 | 7 pcs, verified |
| Power | Waveshare UPS HAT (C) + 4× NCR18650GA + 4-slot holder | as in A | 86.40 | in stock |
| Power alt | bq24074 + S13V30F5 + MAX17048 (3 A path) | as in A | ~46 | in stock |
| Audio, ring, shifter, gate, lid, button, LEDs, magnets | same as A | as above | ~73 | in stock |
| Storage, PSUs, port | same as A | as above | ~76 | in stock |
| Enclosure | Hammond 1590DD + Delock 88747 IPEX→SMA + 12635 antenna — or Hammond 1591USBK ABS with the stub antenna inside | as above | 59.34 or 9.25 | in stock *browser* |
| Mechanical | acrylic, hinge, feet | Hornbach | 17.05 | in stock |
| SIM | Digital Republic Flat 1 | as above | 6 / month | — |

**Total ≈ CHF 375 in aluminium, ≈ CHF 325 in ABS** (4 cells, two cards, two PSUs).
Trimmed (3 cells, one card, one PSU) ≈ CHF 275 in ABS.

**Compatibility.** Identical pin map to A. The HAT takes 5 V from the 40-pin header
and data over USB-C ↔ the Pi's USB (OTG on the Zero 2 W, USB-A on the 3A+); Linux
sees it as ECM/RNDIS Ethernet (`AT+CUSBPIDSWITCH=9018` for ECM) plus `/dev/ttyUSB2`
for AT diagnostics. Gating: PWRKEY power-down (documented; a few mA standby), or
lift the HAT's 5 V pin and feed it through the Pololu switch for a true zero. The
HAT's UART pins (GPIO14/15) do not collide with I2S, SPI0 or I2C. Peak: A7670E
bursts ~2 A at its 3.8 V rail (~1.6 A at 5 V for milliseconds; the HAT has bulk
capacitance) — same 1.8 A caution as A on the UPS HAT.

**Fit.** In the 1590DD do **not** stack the modem HAT on the Pi (three boards ≈
33 mm, the full inner height); lay it flat beside the Pi on its USB-C cable
(65 × 30.5 × ~12). Then: cells 78 × 79 × 22, Pi + UPS HAT 65 × 30 × 17, modem HAT
65 × 31 × 12, ring and speaker under the lid over the modem side (12 + 17 = 29 <
33). Fits. In the 1591USBK (≈ 114 × 114 × 55 inside) the three boards may stack
and the stub antenna stays inside; the 4-cell holder sits beside the stack
(79 + 30 = 109 < 114).

**Power.** Zero 2 W 100 mA + modem ~10 mA average (Cat-1 bursts, PWRKEY off between
polls) + ring 2 + misc 5 ≈ 117 mA → 13.3 Ah with margin → **4 cells ≈ 60 h**, 3 cells
≈ 45–50 h, 30-minute polls stretch 4 cells past 65 h. Charging as in A.

**Dev loop.** As A, plus `AT+CSQ` / `AT+CREG?` on `/dev/ttyUSB2` so Claude can
place the box by signal quality without your phone.

**Risks.** Zero 2 W lead time (same); ECM/RNDIS mode must be set once and must
survive reboots (test); UPS HAT (C) charge current unpublished (measure); if the
HAT is stacked on a 3A+ its 65 × 56 footprint changes the layout.

## 5. Judgement

| Criterion | A: Linux + stick | B: ESP32-S3 + Cat-1 | C: Linux + HAT + UPS |
| --- | --- | --- | --- |
| Claude Code can work on it alone | ●●●● SSH, Ethernet-class modem, web UI | ●● serial flash/monitor, no field shell | ●●●● SSH plus an AT port |
| Nothing-lost storage | ●●●● ext4 + fsync | ●● FAT on SD, needs own log | ●●●● ext4 + fsync |
| Weekend on battery | ●● 4–5 cells, poll-rate sensitive | ●●●●● one cell | ●●● 4 cells |
| Buy this week in CH | ●● stick via Reichelt/Galaxus marketplace; Pi 3A+ only | ●●●● all on shelf | ●●● all on shelf except Zero 2 W |
| Hand-wiring and hacks | ●● cut-VBUS cable, two FET gates | ●●● breakouts only | ●●● breakouts, PWRKEY in software |
| Fit in a 33 mm-deep aluminium box | ●●● marginal over the Pi stack | ●●●● | ●●● if the HAT lies flat |
| Cost (full, 4 cells, spares) | ~385 | ~215–265 | ~325–375 |
| Expensive-surprise risk | stick mode-switch; 1.8 A peak | PSRAM revision; log format | ECM mode persistence; 1.8 A peak |

**Recommendation: Option C**, built on the Pi 3 Model A+ now and swapped to a Zero
2 W when one arrives (identical image, overlays and GPIO map). It is the option
where Claude Code does the most work unattended, it keeps the nothing-lost rule
on a journaled filesystem, every part but the Zero 2 W ships from a Swiss shop
today, and it has no hand-made cable in the modem path. Graft from A: keep the
3 A modular power path as the fallback if the UPS HAT's 1.8 A proves tight. Graft
from B: nothing in hardware, but its power figures are the reminder that on Linux
the whole budget is what you gate.

Choose **B** instead only if a 60 h weekend turns out to be non-negotiable *and*
measurement shows the Pi cannot get there with 4 cells, or if you decide Claude
working through a serial console is acceptable.

**Order in two phases.** Phase 1 (bench, ~CHF 130): Pi 3A+, A7670E HAT, INMP441,
MAX98357A, speaker, reed contact, NeoPixel ring (order first, 2 in stock), AHCT125,
one High Endurance card, one PSU, CP2102 or Debug Probe, the free Digital Republic
SIM (Flat 10 while developing). Phase 2 after measuring current with a USB meter
(Waveshare USB-C meter CHF 10.90 at Pi-Shop; UM25C for logging from Reichelt DE):
UPS HAT (C) or the bq24074 path, cells and holder, button, enclosure and antenna
parts, second card and PSU. Set stock alerts for the Zero 2 W at Pi-Shop.ch and
BerryBase CH and place the Welectron backorder now.

## 6. Verify with parts in hand

1. Real idle current of the tuned Pi (Wi-Fi/BT/HDMI off, `maxcpus=1`) and of the
   A7670E HAT registered, transmitting, and PWRKEY-off — before choosing 3 vs 4 vs 5 cells.
2. UPS HAT (C) charge current and whether its 1.8 A holds Pi boot + modem burst + amp.
3. ECM mode on the A7670E survives a reboot and a PWRKEY cycle.
4. Sunrise indoor coverage in both bedrooms (the free Flat 0.4 SIM is the test).
5. Reed contact registers through the lid gap with the magnet ≤ 8 mm away; keep
   catch magnets ≥ 30 mm from it.
6. Inner dimensions of the chosen box against the Hammond drawing before drilling.
7. Read-only overlay + `/data` survives a power pull mid-write.

## 7. Questions only you can answer

1. **Enclosure:** aluminium 1590DD (rugged, 33 mm inside, antenna outside) or ABS
   1591USBK (CHF 9, 55 mm inside, antenna inside, less "armoured")? A wooden hinged
   box is a third look. This changes ~CHF 50 and the antenna plumbing.
2. **Wait or not for the Zero 2 W:** develop on the 3A+ (weekend impossible on
   battery) and swap later, or pay CHF 50.70 at Digitec for a January delivery?
3. **Budget:** the Linux builds land at CHF 275–385 all-in versus the CHF 150–250
   brief. Trim (3 cells, one card, one PSU) or accept?
4. **Poll interval:** 10 minutes (as designed) or 30 (saves a cell)?
5. **Do you own a 3D printer?** A printed bezel for the ring window and a collar
   around the button make the child-facing side much nicer than bare aluminium.
6. **SIM tier:** Flat 10 while developing over Tailscale, then Flat 1 in the field?

## 8. Decisions — 2026-09-21

**Option C**, with the user's answers to §7:

1. **Enclosure: aluminium 1590DD**, with a small rigid SMA stub outside instead
   of the hinged 12635. Closest match on a Swiss shelf: **Delock 90694**
   (52 × 10 mm, 1.82 dBi, [Reichelt CH](https://www.reichelt.com/ch/de/shop/produkt/lte_antenne_sma_stecker_omnidirektional_starr-426541)
   CHF 8.24, ab Lager). Caveat: its datasheet range is 824–960 / 1710–2170 MHz,
   which misses the band 20 downlink (791–821 MHz) — Sunrise's indoor band —
   and band 7. Band 3 is covered. Buy the **Delock 90682** (115 × 10 mm,
   700–2700 MHz, [Reichelt CH](https://www.reichelt.com/ch/de/shop/produkt/lte_antenne_sma_stecker_omnidirektional_starr-426542)
   CHF 9.16) alongside and let `AT+CSQ` / `AT+CPSI?` in both bedrooms decide.
2. **Start on the Pi 3A+**; Zero 2 W on backorder. Mains-only until it lands.
3. Budget: not answered; the BOM is the full build (~CHF 415 with meter,
   spares and the Zero 2 W). Phases 1 + 2 (~CHF 200) give a working online box.
4. **Polling: adaptive, no SMS wake** — [ADR 0015](../docs/decisions/0015-adaptive-polling.md).
   1 min on mains or for 90 min after the child uses the box; 30 min idle on
   battery with the modem off in between.
5. **No 3D printer — off-the-shelf products only.** The 16 mm stainless button
   carries its own bezel; the ring window is a round hole with a square of
   opal acrylic behind it.
6. **Flat 1 always**, also during development.

Carried into [ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md)
(revised), [bom/bom.csv](bom/bom.csv) and [SHOPPING-LIST.md](SHOPPING-LIST.md).

## Sources checked

Shop pages fetched 2026-09-20 by the research pass (Pi-Shop.ch, BerryBase CH,
Bastelgarage, Play-Zone, Reichelt CH, Botland, Welectron, Hornbach, supermagnete,
Adafruit, Waveshare wiki, Raspberry Pi docs, rpi_ws281x README, raspberrypi/linux
overlays, Espressif docs, Digital Republic, Mucho, Swisscom, Sunrise, BAKOM). Pages
that block automated fetches (Digitec, Galaxus, Distrelec, Brack) were checked by
hand in a browser the same evening; those figures are marked *browser*.
