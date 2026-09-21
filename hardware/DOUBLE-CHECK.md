# Hardware double-check — 2026-09-20 (Pi platform)

> **Superseded in part, 2026-09-21.** [EVALUATION.md](EVALUATION.md) (Option C) and the revised
> [ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md) replace the USB stick with a Waveshare A7670E
> Cat-1 HAT and the PowerBoost with a UPS HAT (C) + four cells. Current parts and links:
> [bom/bom.csv](bom/bom.csv) and [SHOPPING-LIST.md](SHOPPING-LIST.md). The stick and PowerBoost sections
> below are history; the Pi 3A+ / Zero 2 W availability notes still hold.

Every component checked against the others and against the **Hammond 1590DD**
(inside 183 × 113 × 32 mm, aluminium). Sources in [SOURCING.md](SOURCING.md).
Platform: Raspberry Pi + USB 4G stick ([ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md)).

## The enclosure still changes three things

1. **Faraday cage.** The stick's internal antenna is dead inside; its TS-9
   port goes to an SMA bulkhead and a hinged stub outside. Wi-Fi/BT dead too —
   fine, both are off in the field.
2. **32 mm inside.** No arcade button through the top (33–52 mm deep) → 33 mm
   button through the side wall. 40 mm speaker (17 mm), not 50 mm (30 mm).
   A Pi 3A+ (65 × 56 × ~12 mm with header) and a Zero 2 W (65 × 30 × 5) both fit
   flat on the base; the stick lies beside them.
3. **Drill, don't mill.** Round holes only.

## Layout in the 1590DD

```
 top (hinged 4 mm plate)             front wall (120 × 37)        back wall
 ┌───────────────────────────┐       ┌──────────────────────┐    ┌─────────┐
 │   ◯ ring window (45 mm)   │       │ [●] play  · ·  [USB] │    │  SMA ⊙  │
 │   ⋮⋮⋮ speaker grille       │       │        LINK POWER    │    └─────────┘
 └───────────────────────────┘       └──────────────────────┘
 base: Pi · stick (on the Pi's USB-A, or a 10 cm OTG cable on a Zero) · PowerBoost
       · 3–6 × 18650 along the back wall · amp · mic (faces up, under the lid)
 lid: piano hinge on the back edge · magnet catch front · reed contact = lid state = mic power
```

## Component by component

| # | Component | Verdict | What was checked |
| --- | --- | --- | --- |
| 1 | **Raspberry Pi Zero 2 W** (deployment board) | right board, **not buyable this week** | Europe-wide shortage; all Swiss shops out or January 2027; supply expected to improve over the autumn. ~100 mA idle tuned. 65 × 30 mm. One micro-USB OTG port → the stick needs a short OTG cable; bench access is UART or Wi-Fi. |
| 1a | **Raspberry Pi 3 Model A+** (development board, in stock) | **buy now** | Same BCM2837B0, 512 MB, 1.4 GHz, 65 × 56 mm, **USB-A** (stick plugs straight in), micro-USB power, dual-band Wi-Fi. Boots the *same* 64-bit Lite image; the overlay, the service, `dadboxctl` all carry over unchanged. Idle ~200 mA tuned (no USB hub chip, unlike the 3B+) — roughly **2× the Zero 2 W**. |
| 1b | — power consequence | decide at M3 | With a 3A+ in the box the weekend needs ~5–6 × 18650 (~15 Ah, +0.3 kg); with a Zero 2 W ~3. Plan the pack around the Zero 2 W and treat the 3A+ as the bench board unless the Zero never arrives. |
| 1c | — 3B+ / 4 / 5 | no | Distrelec has 3B+ (431) and Pi 5 in stock, but idle 400 mA–3 W. Wrong for a battery. |
| 1d | — Radxa Zero 3W/3E | no | Only the Ethernet 3E at Digitec; Rockchip I2S/device-tree support is a rabbit hole versus the Pi's one-line overlay. |
| 2 | **USB 4G stick, HiLink** | ✔ | `cdc_ether` USB Ethernet, DHCP from 192.168.8.1, no AT, no PPP. **Huawei E8372** in stock (Galaxus, 89.90): TS-9 ports, Wi-Fi hotspot disableable. E3372h-320 unavailable. Brovi E3372-325 / ZTE MF79U at Brack/Digitec unverified (pages didn't render for automated reading) — worth a manual look, Brack ships next day. |
| 2a | — VBUS gating | ✔ design | A high-side P-FET on the stick's 5 V, GPIO-driven: off between check-ins. Boot ~20 s. Saves ~2.7 Ah per weekend versus always-on. On the 3A+ the USB port's power is switchable in software too (`uhubctl` works on 3B+; on 3A+ verify). |
| 2b | — antenna | ✔ | TS-9 → SMA adapter (Delock, Digitec) → SMA bulkhead coupler through the back wall → hinged LTE stub (Delock, 20.90). |
| 3 | I2S mic + MAX98357A | ✔ | The `googlevoicehat-soundcard` overlay is exactly this pair (Google AIY Voice HAT). BCLK 18, LRCLK 19, mic data 20, amp data 21, **amp SD-mode on GPIO 16** — wire it or the amp stays silent. Mic VDD through the reed contact = hardware gating. |
| 4 | Speaker 40 mm / 17 mm | ✔ | Under the lid plate, cone up. |
| 5 | NeoPixel ring 16 | ✔ with shifter | Now at the Pi's 5 V: WS2812 wants ≥3.5 V data from 3.3 V logic → **74AHCT125**. Driven over SPI MOSI (GPIO 10) with `rpi_ws281x`. Gate its 5 V. Only 2 in stock — order first. |
| 6 | Play button 33 mm | ✔ side wall | `gpiozero.Button` with an external 10 kΩ; illuminated — light it during *waiting*. |
| 7 | Reed contact + magnet | ✔ | Lid state on a GPIO (interrupt) and the mic's power switch (1 mA ≪ 3 W). |
| 8 | Status LEDs | ✔ | Two GPIOs, two 3 mm LEDs. |
| 9 | **PowerBoost 1000C** | ✔ phase 3 | 1 A charge (9 Ah ≈ 9–10 h — overnight), 1 A 5.2 V boost, load-sharing, low-battery cutoff. **Enough for a Zero 2 W + stick; marginal for a 3A+ + stick at peak** (a 3A+ can pull ~0.7 A on boot plus the stick's bursts). If the 3A+ stays in the box, use the 1000C for charging and a separate 5 V / 2 A boost, or a 2 A-class charger board. BerryBase CH: 15 in stock. The **500C at Distrelec (2-hour pickup) is too small**. |
| 10 | Cells: protected 18650, 1S parallel | ✔ phase 3 | 3 for a Zero 2 W, 5–6 for a 3A+. Parallel *protected* cells are fine (each PCM trips independently). Strap them; no spring holders. Buy after measuring. |
| 11 | Fuel gauge | ✔ | MAX17043 (SparkFun) or ADS1115 on I²C. The Pi has no ADC. |
| 12 | microSD | ✔ | Name-brand A1, 32 GB. Read-only overlay root + `/data`. Second card imaged as the spare. |
| 13 | SIM: Digital Republic Flat 1 | ✔ | CHF 6/month, unlimited, Sunrise 4G. Cat-M irrelevant now. |
| 14 | PiJuice Zero | dropped | Discontinued at Distrelec. |
| 15 | LILYGO boards, PCF8574, level-shifted modem breakouts | dropped | ESP32 era. See ADR 0013/0014. |

## What this does to the phases

- **Phase 1 orders today**: 3A+, 1590DD, mic, speaker, reed, button, SD, PSUs
  (all in stock) + amp and ring from Galaxus (~1 week). ~CHF 150.
- **Phase 2**: the stick (E8372 now, or a cheaper one from Brack), adapter,
  coupler, antenna, SIM. ~CHF 65–125 + 6/month.
- **Phase 3**: PowerBoost + cells + gauge after measuring. ~CHF 90–130.
- **Zero 2 W**: when it lands, swap it in. Nothing else changes.

## Still to verify with parts in hand

1. Real idle current of the tuned 3A+ and, later, the Zero 2 W — and the
   stick on/off — before choosing the cell count.
2. That the stick stays in HiLink mode across reboots (some need
   `usb_modeswitch` once).
3. That the read-only overlay + `/data` survives a power pull mid-write.
4. Whether the PowerBoost 1000C's 1 A holds the 3A+ + stick at peak; if not,
   a separate boost.
5. The reed contact registers reliably through the lid gap.
