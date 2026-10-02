# Wiring — every pin and every wire

The one place that says what connects to what. The firmware's pin numbers
live in `box/dadbox/hw/pi.py` and must match this file; change both
together. Numbers are **physical header pins** (1–40) unless written
"GPIO n" (BCM numbering, what the software uses).

**Status (2026-09-30):** proposed, nothing wired yet. There are no status
LEDs; the box's only lights are the two buttons
([ADR 0024](../../docs/decisions/0024-no-status-leds-record-says-ready.md)). The I2S pins and
GPIO 16 are fixed by the `googlevoicehat-soundcard` overlay; everything else
is our choice and can move if a wire is awkward — change `pi.py` too.

## Orientation

The Pi Zero 2 W's header runs along one long edge. **Pin 1 is at the
SD-card end.** Odd pins (1, 3, 5, …) are the row nearer the middle of the
board; even pins (2, 4, 6, …) are the row on the board's edge.

## One wire per header pin

Every header pin carries exactly one wire. Three signals still reach two
parts; they are **chained at the parts**, never doubled at the header:

| Header pin | First part | Chained on to | Why this order |
| --- | --- | --- | --- |
| 11 · GPIO 17 | Record button, **R tab** | the mic's **VDD**, by a short wire soldered to the same R tab | **The LED comes first.** Any broken wire can then only leave the mic *unpowered* — never powered with the red light dark. Two wires on the pin, or a Y-splice, would allow exactly that. |
| 12 · GPIO 18 (BCLK) | Amp **BCLK** | the mic's **SCK** | the Zero has one audio interface, fixed on these pins; either order works electrically — amp first matches the bench jumpers as they are |
| 35 · GPIO 19 (LRCLK) | Amp **LRC** | the mic's **WS** | as above |

Grounds were already one per pin, with the joins at the part (a button's
C− and a gold switch tab, the mic's L/R to its GND).

The leads go onto the Zero's top face: with the stacked header in the holes,
each lead is soldered to the top of its header pin, one lead per pin.

A chain is soldered at the part: both wires into the same tab or pad (or the
second wire soldered to the pin on top of the header), heat-shrink over it.
No two Dupont housings on one pin, anywhere.

## The header, all 40 pins

| Pin | Function | Goes to | | Pin | Function | Goes to |
| --: | --- | --- | --- | --: | --- | --- |
| 1 | 3.3 V | — spare | | 2 | 5 V | Amp VIN |
| 3 | GPIO 2 · SDA | — later: INA219 (battery gauge) | | 4 | 5 V | Modem HAT 5 V — stacked header |
| 5 | GPIO 3 · SCL | — later: INA219 | | 6 | GND | Modem HAT GND — stacked header |
| 7 | **GPIO 4** | **Modem PWRKEY (HAT P4) — stacked header** | | 8 | GPIO 14 · TXD | Debug probe RX (yellow) |
| 9 | GND | Mic GND and mic L/R | | 10 | GPIO 15 · RXD | Debug probe TX (orange) |
| 11 | **GPIO 17** | **Record LED red** (mic VDD chained from its tab) | | 12 | GPIO 18 · I2S BCLK | Amp BCLK (mic SCK chained from the amp) |
| 13 | GPIO 27 | Record LED green | | 14 | GND | Debug probe GND (black) |
| 15 | GPIO 22 | Record LED blue | | 16 | GPIO 23 | Play LED red |
| 17 | 3.3 V | — spare | | 18 | GPIO 24 | Play LED green |
| 19 | GPIO 10 | — spare | | 20 | GND | Play button: gold switch tab and C− |
| 21 | GPIO 9 | — spare | | 22 | GPIO 25 | Play LED blue |
| 23 | GPIO 11 | — spare | | 24 | GPIO 8 | — spare |
| 25 | GND | — spare | | 26 | GPIO 7 | — spare |
| 27 | ID_SD | — leave free (HAT EEPROM) | | 28 | ID_SC | — leave free |
| 29 | GPIO 5 | Record button, gold switch tab | | 30 | GND | Record button: other gold tab and C− |
| 31 | GPIO 6 | Play button, gold switch tab | | 32 | GPIO 12 | — spare |
| 33 | GPIO 13 | — spare | | 34 | GND | — spare |
| 35 | GPIO 19 · I2S LRCLK | Amp LRC (mic WS chained from the amp) | | 36 | GPIO 16 | Amp SD (driven by the sound driver) |
| 37 | GPIO 26 | — spare | | 38 | GPIO 20 · I2S DIN | Mic SD (data out of the mic) |
| 39 | GND | Amp GND | | 40 | GPIO 21 · I2S DOUT | Amp DIN (data into the amp) |

Used: 16 signal pins, both 5 V pins, 6 of 8 grounds. Spare: GPIO 7, 8, 9,
10, 11, 12, 13, 26, both 3.3 V pins, two grounds (25, 34). The stacked modem
HAT joins every pin; it uses only 5 V, ground, pin 7 and (switched off) pins
8 and 10.

## Wire colours

From the ten-colour ribbon cable in hand (photo, 2026-09-30). Red is 5 V and
black is ground everywhere; both buttons are wired alike; each I²S clock keeps
its colour from the header through the amp to the mic. The wiring map
(`wiring-diagram.html`) draws every wire in these colours.

| Colour | Cut | Pins → part |
| --- | --: | --- |
| black | 4 + jumpers | 9 mic GND · 30 record gold/C− · 20 play gold/C− · 39 amp GND; short offcuts for C− ↔ gold and mic L/R ↔ GND |
| red | 1 | 2 amp Vin (the modem gets 5 V through the stacked header) |
| orange | 3 | 11 record R · 16 play R · record R tab → mic VDD |
| green | 3 | 13 record G · 18 play G · 40 amp DIN |
| blue | 2 | 15 record B · 22 play B |
| white | 2 | 29 record switch · 31 play switch |
| yellow | 2 | 12 amp BCLK · amp BCLK → mic SCK |
| purple | 2 | 35 amp LRC · amp LRC → mic WS |
| brown | 1 | 38 mic SD |
| grey | 1 | 36 amp SD |

The debug probe (pins 8, 10, 14) uses its own orange / yellow / black cable.

## Per part

### The buttons, seen from the back

Six tabs (photo, 2026-09-30). Four silver tabs for the LED, labelled on the
body; two gold tabs, unlabelled, for the switch:

```
          C−   [ ]   [ ]   R          silver: C− top-left, R top-right
    gold [ ]                 [ ] gold  gold: the switch, left and right
          B    [ ]   [ ]   G          silver: B bottom-left, G bottom-right
```

- **C−** is the LED's common cathode, not the switch. It goes to ground.
- The two **gold tabs** are a plain normally-open contact: no polarity,
  either one to the GPIO and the other to ground. Check with a meter's
  continuity beep: silent at rest, beeps while pressed.
- One ground wire per button: solder a short link from C− to one gold tab
  and run the ground from there.
- Confirm the colours once before soldering: 3.3 V (pin 1) on R, G or B,
  ground on C−. The resistors are built in, so no series resistor is needed.

### Record button — 16 mm, RGB ring, common cathode, resistors built in

| Button tab | Pi pin | GPIO |
| --- | --- | --- |
| gold (switch) | 29 | GPIO 5 — input, internal pull-up; pressed = low |
| other gold (switch) | 30 | GND |
| R | 11 | **GPIO 17.** A second wire from this same tab goes to the mic's VDD |
| G | 13 | GPIO 27 |
| B | 15 | GPIO 22 |
| C− (LED common cathode) | 30 | GND — linked to the other gold tab at the button |

### Play button — same part

| Button tab | Pi pin | GPIO |
| --- | --- | --- |
| gold (switch) | 31 | GPIO 6 |
| other gold (switch) | 20 | GND |
| R | 16 | GPIO 23 |
| G | 18 | GPIO 24 |
| B | 22 | GPIO 25 |
| C− | 20 | GND — linked to the other gold tab at the button |

### Microphone — DFRobot I2S MEMS (MSM261S4030H0)

Pin labels vary between modules: SCK/BCLK, WS/LRCL, SD/DOUT/DATA,
L/R/SEL.

| Mic pin | Pi pin | Note |
| --- | --- | --- |
| VDD (3.3 V) | Record button's R tab | **GPIO 17 through the red LED's tab** — no red light, no mic ([ADR 0016](../../docs/decisions/0016-two-buttons-no-lid.md)). Never to the 3.3 V pin, never straight to pin 11. |
| GND | 9 | |
| SCK / BCLK | the amp's BCLK | chained, not to the header |
| WS / LRCL | the amp's LRC | chained, not to the header |
| SD / DATA | 38 · GPIO 20 | |
| L/R / SEL | 9 (GND) | left channel |

### Amplifier — Adafruit MAX98357A, and the speaker

| Amp pin | Pi pin | Note |
| --- | --- | --- |
| Vin | 2 · 5 V | |
| GND | 39 | |
| BCLK | 12 · GPIO 18 | and on to the mic's SCK |
| LRC | 35 · GPIO 19 | and on to the mic's WS |
| DIN | 40 · GPIO 21 | |
| SD | 36 · GPIO 16 | the sound driver raises it only while audio plays; the firmware never touches it |
| GAIN | — | unconnected: 9 dB |
| Speaker + / − | — | the Seeed 4 Ω speaker on the screw terminal |

### Modem — Waveshare SIM7670G HAT, under the Zero, pin for pin

The HAT sits under the Zero ([ADR 0023](../../docs/decisions/0023-enclosure-layout.md)),
its 40-pin header exactly under the Zero's: a straight 2×20 header soldered in
from below joins **pin N of the Zero to pin N of the HAT**, all 40. No modem
wires.

From the [HAT schematic](https://files.waveshare.com/wiki/SIM7670G-LTE-Cat-1-GNSS-HAT/SIM7670G_LTE_Cat-1-GNSS_HAT.pdf)
the HAT uses only: **5 V** (pins 2, 4), **GND** (every ground pin), **P4**
(pin 7 → DIP 3 → power key) and **TXD / RXD** (pins 8, 10 → DIP 1 / 2, kept
off). Every other pin, 3.3 V and I²C included, ends at the header on the HAT,
so the buttons, I²S and the debug probe are unaffected by the join.

| Connection | Zero | HAT | Note |
| --- | --- | --- | --- |
| 5 V | pins 2, 4 | pins 2, 4 | through the header; the amp's red lead goes on pin 2's top |
| GND | all ground pins | same | through the header |
| PWRKEY | pin 7 · **GPIO 4** | pin 7 (P4), DIP switch 3 (PWR) **on** | high on P4 turns a transistor on that pulls PWRKEY low. GPIO 4 has a pull-up at boot: `gpio=4=op,dl` in `config.txt` holds it low from the first second, since a key held ≥ 2.5 s turns the modem off. The HAT pulses PWRKEY itself at power-up, so the modem starts without it |
| Data | Zero's inner micro-USB, "USB" | HAT Type-C | the short micro-USB → USB-C lead (BOM C2); appears as a network interface |
| DIP switches | — | 1 TXD, 2 RXD **off**; 3 PWR **on**; 4 BOOT **off** | TXD/RXD would put the modem's UART on GPIO 14/15, the console; BOOT is for firmware flashing |
| Antenna | HAT "LTE" IPEX1 | pigtail → SMA through the wall → stub | never transmit without it |
| SIM | HAT slot | — | insert before power; no hot-swap |

### Debug probe — bench only

Its UART cable: orange = TX (out of the probe), yellow = RX (into the
probe), black = GND. Receive meets transmit:

| Probe wire | Pi pin |
| --- | --- |
| Orange (probe TX) | 10 · GPIO 15 · RXD |
| Yellow (probe RX) | 8 · GPIO 14 · TXD |
| Black (GND) | 14 |

115 200 baud; `enable_uart=1` and `dtoverlay=disable-bt` are set, so this
is the full UART and the kernel console.

### Power

5 V 2.5 A supply → the Zero's **outer** micro-USB, "PWR IN". The 5 V rail
then feeds the amp (pin 2) and the modem HAT (pin 4). Later, the UPS module
replaces the supply, and its INA219 goes on pins 3 and 5 (I²C), with its
own ground ([ADR 0019](../../docs/decisions/0019-mains-first-battery-deferred.md)).

## Limits to respect

- **GPIO current:** at most ~16 mA per pin, ~50 mA for all of them
  together. GPIO 17 carries the red LED *and* the mic (~1 mA). The ring
  LEDs have their resistors built in for 5 V, so at 3.3 V they draw less —
  measure one channel before trusting the total; buffers (74AHCT125) only if
  they are too dim (ADR 0016).
- **3.3 V logic only** on every GPIO. The modem HAT's logic is 3.3 V.
- **GPIO 16 belongs to the sound driver.** Do not reuse it.
- **GPIO 0/1 (pins 27, 28)** are for HAT EEPROMs; leave them free.
- One wire per header pin; the shared signals are chained at the parts
  (see *One wire per header pin*).
