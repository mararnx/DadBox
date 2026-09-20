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
| 1 | **LILYGO T-SIM7080G-S3** replaces DevKitC + modem breakout + level shifter + charger | **Switch to it** — [ADR 0012](../docs/decisions/0012-lilygo-t-sim7080g-s3.md) | ESP32-S3 with **16 MB / 8 MB**, SIM7080G on UART (TX 4, RX 5, PWRKEY 46, DTR 7, RI 6), USB-C charging, **18650 holder + JST 2.0**, **TF slot** (GPIO 10-13), nano-SIM, I2C on 2/3. 110 × 32 × 19.5 mm, 66 g — fits along the 183 mm with room. Modem VBAT 2.7–4.8 V and up-to-2 A bursts handled on-board. Includes an IPEX LTE antenna. `esp_modem` PPP works the same over its UART, so ADR 0006 stands. |
| 1a | — charge current | note | **500 mA max** → a 3000 mAh cell charges from flat in ~7 h. Overnight, fine. Not a "top up at lunch" device. |
| 1b | — variant | **verify before ordering** | Two variants exist: with a PMU (AXP2101 — software control of rails, real fuel gauge) and "Standard" without. Bastelgarage's listing doesn't say. Prefer the PMU one; the Standard one works with an ADC divider for battery %. Ask Bastelgarage or check the board photo for the AXP chip. |
| 1c | — 18650 holder | **don't rely on it** | Spring holders bounce in a bag → brownout → reset mid-upload. Use a **protected 18650 with JST-PH 2.0 leads** on the JST connector, strapped down. Holder stays empty (or holds the same cell with tape, as a fallback). |
| 1d | — TF slot | bonus | Answers storage-queue.md Q2: the outbox can overflow to SD if it ever needs to. Keep internal flash primary; SD is optional headroom, not a dependency. |
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
| 12 | SIM | **risk** | 1NCE €12 / 10 yr covers CH, but sells B2B — confirm private ordering. Hologram is the fallback. And check **LTE-M** coverage specifically at both addresses. |
| 13 | ESP32-S3-DevKitC-1 N16R8 | dropped | Redundant with the LILYGO. Buy one (18.90) only if you want a second bench board. |
| 14 | BQ24074 charger, level shifter, SIM7080G breakout | dropped | All on the LILYGO. |
| 15 | 1000 µF at the modem | keep in the drawer | The LILYGO has its own decoupling. Add it only if uploads reset the board. |

## What this does to the phases

- **Phase 1 now includes the LILYGO** (it *is* the audio board), the box, the
  mic, speaker, amp, ring, reed contact, button, LEDs. ~CHF 160. You prove
  audio *and* fit in the real enclosure at once.
- **Phase 2** is just the SIM, the pigtail and the stub antenna. ~CHF 35.
- **Phase 3** is the cell and two PSUs. ~CHF 35.
- **Phase 4** is hinge, acrylic, mesh, screws. Hardware store.

## Still to verify with parts in hand

1. Which LILYGO variant arrived (PMU or Standard) — decides battery sensing.
2. Free GPIOs on the LILYGO headers for I2S ×2, ring, gates, lid, button,
   LEDs (13 pins). The docs list what's *taken*; confirm the rest on the
   pinout image.
3. That the reed contact + magnet register reliably through the 4 mm lid
   gap you end up with. Reed range is ~10–15 mm; should be fine.
4. Idle current of every gated rail, before ordering the cell.
