# Hardware double-check — 2026-09-20

Every component checked against the others and against the enclosure the
user chose: a **Hammond 1590DD** die-cast aluminium box. Numbers from
datasheets and shop listings, not memory; sources in [SOURCING.md](SOURCING.md).

## The enclosure changes three things

**1590DD**: outside 187.5 × 119.5 × 37 mm, **inside 183 × 112.9 × 32 mm**,
4 mm lid on six screws, IP54, ~0.5 kg empty
([datasheet](https://www.hammfg.com/part/1590DD)).

1. **It is a Faraday cage.** LTE, GPS, Wi-Fi and BLE are all dead inside it.
   The LTE antenna goes *outside* through an SMA bulkhead; GPS/Wi-Fi/BLE we
   don't need (and no Wi-Fi means no provisioning, which is a feature).
2. **32 mm inside.** A 60 mm arcade button is 52.4 mm deep with its
   microswitch; the 30/33 mm ones are ~33 mm. Nothing arcade-shaped fits
   *through the top*. The play button mounts **through a side wall** — 24 mm
   hole in a 37 mm wall — with its body running inward across the 113 mm
   width. The 50 mm speaker (30 mm tall) is out; the 40 mm (17 mm) is in.
3. **Drill, don't mill.** Round holes are easy in die-cast: step drill for
   the button, hole saw for the ring window, hole pattern for the speaker,
   a 6.5 mm for the SMA. Slots and rectangles are a jigsaw and an afternoon.
   The design below uses only round holes.

Weight: ~0.5 kg box + ~0.2 kg parts ≈ 0.7 kg. Heavy for a school bag; very
much a thing that survives one. Heat: aluminium is the best case. Drops:
the box will outlive the child's interest in it.

## Layout in the 1590DD (proposal — see enclosure.md)

```
 top (the hinged 4 mm plate)         front wall (120 × 37)          back wall
 ┌───────────────────────────┐       ┌──────────────────────┐       ┌─────────┐
 │   ◯ ring window (45 mm)   │       │ [●] play  · ·  [USB-C]│       │  SMA ⊙  │
 │   ⋮⋮⋮ speaker grille       │       │        LINK POWER    │       └─────────┘
 └───────────────────────────┘       └──────────────────────┘
 inside, on the base: LILYGO (110 × 32 × 19.5) · 18650 · amp · mic (faces up, under the lid)
 lid: piano hinge on the back edge · magnet catch front · reed contact = lid state = mic power
```

Ring and speaker live on the lid plate; five wires cross the hinge (a short
ribbon — guitar pedals do this for decades). Mic on the base, exposed when
the lid is open — which is the gesture.

## Component by component

| # | Component | Verdict | What was checked |
| --- | --- | --- | --- |
| 1 | **LILYGO T-A7670G R2** (Cat-1) replaces the T-SIM7080G-S3 (Cat-M) | **Switch** — [ADR 0013](../docs/decisions/0013-cat1-not-catm.md) | The user's SIM provider, Digital Republic, [does not support Cat-M1/NB-IoT](https://support.digitalrepublic.ch/en/support/solutions/articles/33000225329-do-digital-republic-sim-cards-support-lte-cat-m1-and-nb-iot-); the SIM7080G has no ordinary 4G. The R2: ESP32 **WROVER (classic LX6), 4 MB flash, 8 MB PSRAM**, A7670G **LTE Cat-1 (10/5 Mbps)** + GNSS, JST LiPo with charging, USB-C, micro/nano-SIM, u.FL for LTE and GPS, both antennas in the box. 111 × 35 × 22 mm — fits. `esp_modem` PPP works the same. CHF 37.90, in stock. |
| 1a | — flash | **the real cost** | 4 MB. OTA wants two ~1.5 MB slots → <1 MB left. The never-lost outbox moves to the **TF card**; internal flash keeps only the latest message as fallback. SD becomes a dependency — name-brand card, sync-on-write, missing card = fault LED. **Confirm the R2 has the TF slot** (LILYGO says yes; Bastelgarage's listing is silent). |
| 1b | — pins | **exactly enough** | Fixed on the R2: modem TX 26 / RX 27 / PWRKEY 4 / DTR 25 / RI 33 / RESET 5 / POWER_ON 12; TF 14/2/15/13; VBAT ADC 35. That leaves **six native outputs** (18 19 21 22 23 32) and three input-only pins (34 36 39). It fits: mic and amp **share one I2S port in full-duplex** (BCLK 18, WS 19, DOUT 23, DIN 34), I²C 21/22 to a **PCF8574** for LEDs, ring gate, amp shutdown and button LED, ring data on 32, lid on 36 and play on 39 (input-only → external 10 kΩ pull-ups). Pin map in `firmware/main/dadbox_config.h`. |
| 1c | — battery | ✔ | The R2 has **both** an 18650 holder with charging and a JST LiPo connector (LILYGO/RandomNerd; Bastelgarage's listing shows only the connector). Same rule as before: protected 18650 with JST leads, strapped down; don't trust the spring holder in a bag. Charge rate unverified — assume ≤500 mA. |
| 1d | — power | fine | A7670 sleeps at ~2 mA (vs µA for Cat-M). 60 h × 2 mA = 120 mAh = 4 % of the cell. Wake via DTR; no need to power-cycle the modem between check-ins, so the poll interval can be tighter for free. |
| 1e | — GNSS | free bonus | Not needed, but the modem's cell ID (`AT+CPSI`) or a GNSS fix at check-in answers "which house" for ADR 0008 without a dock resistor. |
| 1f | — alternative | if 1a/1b bite | **T-SIM7670G-S3**: ESP32-S3, 16 MB flash, SIM7670G Cat-1. Not stocked in CH, no TF slot, ~0.5 mA deep-sleep floor (harmless). 2–3 weeks by import. |
| 2 | I2S mic MSM261S4030H0 (Bastelgarage) | ✔ | 3.3 V, 1 mA, 24-bit I2S. No enable pin — the reed contact switches its VDD directly (1 mA ≪ 3 W contact rating). That is the physical mic gate. INMP441 from Temu is the equivalent. |
| 3 | MAX98357A amp | ✔ | 2.7–5.5 V. Feed from VBAT (3.7–4.2 V) → ~1.5 W into 4 Ω. Plenty for a bedroom; 3 W needs 5 V and a boost we don't want. SD pin for gating. Gain set by pin, volume in firmware. |
| 4 | Speaker 40 mm 4 Ω 3 W, 17 mm tall | ✔ fits | Mounted under the lid plate, cone up through a hole pattern. The 50 mm (30 mm tall) does not fit. Visaton BF 45 is 61 × 45 mm rectangular and 4–6 weeks — skipped. |
| 5 | NeoPixel ring 16, 44.5 mm OD | ✔ | "5 V, 4–7 V works": VBAT at 3.7–4.2 V is fine, and 3.3 V data clears the 0.7 × VDD threshold. Gate it (draws ~16 mA dark). 45 mm hole saw in the lid + 3 mm acrylic disc as diffuser. Only 2 in stock at Galaxus — order first. |
| 6 | Play button: 33 mm illuminated (24 mm hole) | ✔ side wall | Depth ~33 mm runs inward along the width. Illuminated is a bonus: light it during *waiting* so the child knows which thing to press. 60 mm: **no** (52.4 mm deep). |
| 7 | Lid sensor: magnetic door contact (reed + magnet) | ✔ | NO contact, 3 W, 330 mm lead. Doubles as the mic power switch. The 5 V hall module is the wrong voltage — skipped. |
| 8 | Status LEDs: 2 × 3 mm | ✔ | Any. Through 3 mm holes in the front wall beside the button. |
| 9 | LTE antenna | **changes** | The included IPEX antenna is useless inside aluminium. Pigtail U.FL → **bulkhead** SMA through the back wall, stub SMA antenna outside. Delock hinged LTE/GSM stub, or the 3 m-cable indoor antenna if the box's spot has bad signal. Confirm the LILYGO's connector is u.FL/IPEX-1 (2.0 mm), not MHF4. |
| 10 | Battery: protected 18650 ~3000 mAh, JST-PH 2.0 | ✔ phase 3 | Protection at the cell ([ADR 0005](../docs/decisions/0005-battery-required.md)). 60 h target at ~40 mA average = 2.4 Ah — realistic if the ring, amp, mic and modem are gated. Measure first. |
| 11 | USB-C PSU, one per house | ✔ | Any 5 V / 2 A. |
| 12 | SIM: Digital Republic Flat 1 | ✔ | CHF 6/month, unlimited, Sunrise 4G, no contract. Flat 0.4 (CHF 4) works but a 5-min ADPCM message takes ~100 s at 0.2 Mbps up; Flat 1 halves it. Coverage question is now "Sunrise 4G in both bedrooms" — near-certain. |
| 13 | ESP32-S3-DevKitC-1 N16R8 | dropped | Redundant with the LILYGO. Buy one (18.90) only if you want a second bench board. |
| 14 | BQ24074 charger, level shifter, SIM7080G breakout | dropped | All on the LILYGO. |
| 15 | 1000 µF at the modem | keep in the drawer | The LILYGO has its own decoupling. Add it only if uploads reset the board. |

## What this does to the phases

- **Phase 1 now includes the LILYGO** (it *is* the audio board), the box, the
  mic, speaker, amp, ring, reed contact, button, LEDs, a microSD and the
  expander. ~CHF 165. You prove audio *and* fit in the real enclosure at once.
- **Phase 2** is the Digital Republic SIM, the pigtail and the stub antenna.
  ~CHF 31 + CHF 6/month.
- **Phase 3** is the cell and two PSUs. ~CHF 35.
- **Phase 4** is hinge, acrylic, mesh, screws. Hardware store.

## Still to verify with parts in hand

1. ~~That the R2 has its TF slot~~ — confirmed (SPI on 14/2/15/13). Still: that
   the SD survives a power pull mid-write.
2. Free GPIOs on the R2 headers after modem and TF. Expect to need the
   PCF8574; confirm how many native pins remain for I2S ×2 + ring data.
3. That the reed contact + magnet register reliably through the 4 mm lid
   gap you end up with. Reed range is ~10–15 mm; should be fine.
4. Idle current of every gated rail, before ordering the cell.
