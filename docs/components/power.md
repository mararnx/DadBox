# Power

**Role.** Be on when a child reaches for it, and never be a lithium hazard in a
child's bedroom or bag.

## Current design (ADR 0005)

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
  | ESP32-S3 light sleep | ~1-2 mA | deep sleep is µA but loses the I2S/timer state; fine between polls |
  | WS2812B ×16, dark | ~16 mA | **power-gate with a FET** → ~0 |
  | MAX98357A in shutdown | µA | via SD pin |
  | Mic, unpowered | 0 | load switch |
  | Modem in PSM | ~µA–1 mA | eDRX/PSM config dependent |
  | Modem poll every 15 min | ~2-3 mA average | 10-20 s at ~200 mA, bursts to 2 A |
  | Ring breathing (message waiting) | 20-60 mA | brightness-dependent, only when waiting |

  Gated properly: ~5 mA average → ~3 weeks. Ungated ring: ~20 mA → ~6 days.
  Playing a message: ~300-500 mA for its duration, negligible overall.

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
