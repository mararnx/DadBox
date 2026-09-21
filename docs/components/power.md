# Power

**Role.** Be on when a child reaches for it, and never be a lithium hazard in a
child's bedroom or bag.

## Current design (ADR 0005, ADR 0014, ADR 0019)

**The first box has no battery** ([ADR 0019](../decisions/0019-mains-first-battery-deferred.md)):
5 V micro-USB, on only while plugged in, `mains: true` / `battery_pct: null`,
POWER LED off. Pulling the plug is how it turns off, so every write path must
survive that. What follows is the battery as designed, for when it is fitted;
the left half of the enclosure floor (93 × 86 mm) stays free for it.

The box is plugged in most of the time; the battery is for weekends and car
rides. Target: **operate unplugged for a weekend**
([ADR 0005](../decisions/0005-battery-required.md)). The power section is
**phase 3 — not ordered, bought after measuring.** Until then the box runs
from a 5 V micro-USB supply.

- **Waveshare UPS Module 3S** ([ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md)):
  three protected 18650s in series (~36 Wh), 5 V 5 A out, charges while
  powering, protection on board, 93 × 86 mm.
- **INA219 over I²C** gives battery %, current, and **mains vs battery from
  the sign of the battery current** — the signal
  [ADR 0015](../decisions/0015-adaptive-polling.md)'s cadence needs
  (telemetry `mains`, distinct from `charging`).
- Charged from its own **12.6 V 2 A barrel-jack supply — not USB** — through a
  panel-mount DC jack in the wall. A second charger lives in house B. A full
  charge is ~5 h.
- **Budget:** Zero 2 W ~100 mA at 5 V + modem ~3–10 mA averaged on battery
  ≈ 0.6 W → **≈ 50–55 h**, ~45 h with a 20 % margin. About two days; the
  60 h weekend is not quite met.
- **Every consumer is power-gated:** button LEDs, amp (SD pin), mic (the pin
  it shares with the red light), and on battery the modem between check-ins.
  A Pi can't sleep, so gating is the whole budget.
- **Low battery is the adults' business.** Nothing on the buttons. POWER LED
  blinks below 20 % and the app nags; below 5 % the box shuts down cleanly
  and the app says so.

USB-charged fallback, if the module disappoints: bq24074 + Pololu S13V30F5 +
MAX17048, in ADR 0014 only.

## Checked

- Idle budget on battery, rough, to be measured:

  | Consumer | Idle | Note |
  | --- | --- | --- |
  | Pi Zero 2 W, tuned | ~100 mA at 5 V | Wi-Fi/BT/HDMI off; it never sleeps |
  | Modem, averaged | ~3–10 mA | off between 30-minute check-ins; ~20–30 mA while registered during a conversation window |
  | Button LEDs | small | *waiting* drops to *resting* after 2 h; idle is dark |
  | MAX98357A in shutdown | µA | via SD pin |
  | Mic, unpowered | 0 | its supply pin is low |
  | Status LEDs (LINK, POWER) | ~0 | ~10 ms blinks every 3 s |
  | UPS module itself | to measure | buck losses and quiescent draw |

  Playing a message: a few hundred mA for its duration, negligible overall.
  **The modem's off-time is the lever**; nothing else moves the total.
- LTE transmit bursts reach amps for milliseconds. A supply that sags there
  is the #1 cause of "my LTE project resets randomly" — the reason a 1 A
  boost was dropped for a module with 5 A of headroom.
- **Not a power bank.** Most drop their output for a moment on plug/unplug (a
  Pi reboot each time), many switch off at low current, and none reports
  charge level or mains-present — so no battery % in the app, no low-battery
  LED, no clean shutdown, nothing for the polling cadence to go on. Fine for
  carrying a bench prototype around; not the box.
- Cells: three protected NCR18650GA, same batch and charge state, in the
  module's holders — 69.5 mm long with their protection, which the holders
  must take (Q2).

## Questions

1. **Measure first — with what?** Real idle current of the tuned Pi, and of
   the modem registered, transmitting and off, decides whether three cells
   are right. Before the module exists there is no INA219: a USB meter on
   the micro-USB supply, or buy the module first and the cells after?
2. **UPS module height and holder length** — its height against the clone's
   inner depth ([enclosure.md](enclosure.md) Q1, Q3), and whether the holders
   take 69.5 mm protected cells.
3. **Does its output blip** when the charger is plugged or pulled? And its
   own quiescent draw?
4. **Charging beside a sleeping child** — what charge current does the module
   actually apply from its 2 A supply, against the cells' rated charge
   current? Does it sense cell temperature? How warm does the closed
   aluminium box get while charging?
5. **Two days, not 60 h** — accept, or stretch `idle_minutes` on battery?
   Decide after measuring.
6. **DC panel jack** — match the charger's plug; buy with the module in hand.
7. **Which house?** Telemetry `house` is reserved for a dock ID resistor;
   with a barrel jack there is no dock. Drop it, or find another signal?
