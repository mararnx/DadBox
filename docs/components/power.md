# Power

**Role.** Be on when a child reaches for it, and never be a lithium hazard in a
child's bedroom or bag.

## Current design (ADR 0005)

> **Platform change 2026-09-20 — [ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md):** a Pi cannot sleep: ~75–100 mA tuned, plus the stick averaged ~60 mA with VBUS gating → ~140–180 mA → **three protected 18650s (~9 Ah) for 50–65 h; a fourth if measured**. PowerBoost-1000C-class charger/boost (1 A charge, overnight) and a MAX17048 gauge. Measure before buying cells.

> **Decided 2026-09-20:** **operate unplugged for a weekend** (~60 h) — [ADR 0005](../decisions/0005-battery-required.md). Every rail gated: mic (lid), ring (FET), amp (SD), modem (PSM). Q3: nothing on the box below 20 %, sleep below 5 %, the app nags. Cell sized after measuring.

Internal protected LiPo, 3000 mAh, USB-C charging with power path, bulk
capacitance for modem bursts.

## Checked

- **The premise is unexamined** — see [review §4](../REVIEW.md). ADR 0005
  answers "how do we put a battery in safely" but nobody asked "does it need to
  run on one". Two very different products:

  | Mode | Battery | What it must do unplugged |
  | --- | --- | --- |
  | **Survive transit** | small (500 mAh) or none | hold state, maybe finish an upload |
  | **Operate unplugged** | large (3000+ mAh) | a day? a weekend? with cellular |

- Idle budget, rough, for the "operate" case on 3000 mAh:

  | Consumer | Idle | Note |
  | --- | --- | --- |
  | (the ESP32 row is history — see ADR 0013/0014) | | |
  | WS2812B ×16, dark | ~16 mA | **power-gate with a FET** → ~0 |
  | MAX98357A in shutdown | µA | via SD pin |
  | Mic, unpowered | 0 | load switch |
  | Pi Zero 2 W, tuned | ~75–100 mA | Wi-Fi/BT/HDMI off, one core at idle; it never sleeps |
  | USB stick, VBUS-gated | ~60 mA averaged | ~100–150 mA on; ~30 s per 10-min check-in incl. boot; always-on would be ~2.7 Ah more per weekend |
  | Boost converter | ~10 % | 3.7 V → 5 V for the Pi |
  | Ring breathing (message waiting) | ~15 mA | brightness-dependent; **drops to *resting* (~1.5 mA) after 2 h** — a message waiting all weekend would otherwise cost ~30 % of the cell |
  | Status LEDs (LINK, POWER) | ~0 | 10 ms blinks every 3 s, low brightness |

  Gated properly: ~5 mA average → ~3 weeks. Ungated ring: ~20 mA → ~6 days.
  Playing a message: ~300-500 mA for its duration, negligible overall.

- **Charging** ([ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md)): a
  PowerBoost 1000C — 1 A charge (9 Ah ≈ 9–10 h, overnight), 1 A 5.2 V boost
  with load-sharing. Marginal for a 3A+ + stick at peak; if the 3A+ stays in
  the box, add a separate 2 A boost. Cells: protected 18650s in parallel,
  strapped, no spring holders. Battery % from a MAX17043 or ADS1115 on I²C —
  the Pi has no ADC.
- Transmit bursts to ~2 A for tens of ms: the cell, the protection PCM, the
  power-path regulator and the trace to the modem all need to be rated for it,
  or the box brown-outs mid-upload. This is the #1 cause of "my LTE project
  resets randomly".
- Charging while a child sleeps next to it: keep charge current ≤ 0.5 C, use a
  charger IC with a thermistor input, and put the thermistor on the cell.
- USB-C: a proper 5.1 kΩ CC pull-down pair so any USB-C supply works, not
  just A-to-C cables.

## Questions

1. **Operate or survive?** — the biggest swing in the BOM and the enclosure.
2. If operate: **for how long?** A school day (8 h), a night (14 h), a weekend
   away (60 h)? Each is a different cell and a different sleep strategy.
3. **What does low battery look like to the child?** Rule: nothing alarming.
   Suggest: nothing on the box at all below 20%; the app nags the adults.
   Below 5%: box goes fully to sleep, ring off, and the app says so.
4. **Charging dock or cable?** A dock with pogo pins is charming and
   travel-proof; a USB-C port is a hole in the enclosure that collects crumbs.
   Dock also enables the per-house ID resistor trick in
   [server.md](server.md).
5. **Does the box know which house it's in from the charger?** If a dock is
   chosen, a resistor in each dock tells the box where it is. Cheap and decides
   routing without a button.
6. **Thermal** — the cell, the modem and the amp all make heat in a sealed
   plastic box. Vent, or derate?
