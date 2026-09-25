# Wiring — every pin and every wire

The one place that says what connects to what. The firmware's pin numbers
live in `box/dadbox/hw/pi.py` and must match this file; change both
together. Numbers are **physical header pins** (1–40) unless written
"GPIO n" (BCM numbering, what the software uses).

**Status (2026-09-24):** proposed, nothing wired yet. The I2S pins and
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
C and −, the mic's L/R to its GND).

A chain is soldered at the part: both wires into the same tab or pad (or the
second wire soldered to the pin on top of the header), heat-shrink over it.
No two Dupont housings on one pin, anywhere.

## The header, all 40 pins

| Pin | Function | Goes to | | Pin | Function | Goes to |
| --: | --- | --- | --- | --: | --- | --- |
| 1 | 3.3 V | — spare | | 2 | 5 V | Amp VIN |
| 3 | GPIO 2 · SDA | — later: INA219 (battery gauge) | | 4 | 5 V | Modem HAT 5 V (its pin 2) |
| 5 | GPIO 3 · SCL | — later: INA219 | | 6 | GND | Modem HAT GND (its pin 6) |
| 7 | GPIO 4 | — spare | | 8 | GPIO 14 · TXD | Debug probe RX (yellow) |
| 9 | GND | Mic GND and mic L/R | | 10 | GPIO 15 · RXD | Debug probe TX (orange) |
| 11 | **GPIO 17** | **Record LED red** (mic VDD chained from its tab) | | 12 | GPIO 18 · I2S BCLK | Amp BCLK (mic SCK chained from the amp) |
| 13 | GPIO 27 | Record LED green | | 14 | GND | Debug probe GND (black) |
| 15 | GPIO 22 | Record LED blue | | 16 | GPIO 23 | Play LED red |
| 17 | 3.3 V | — spare | | 18 | GPIO 24 | Play LED green |
| 19 | GPIO 10 | — spare | | 20 | GND | Play button: switch C and LED − |
| 21 | GPIO 9 | — spare | | 22 | GPIO 25 | Play LED blue |
| 23 | GPIO 11 | — spare | | 24 | GPIO 8 | — spare |
| 25 | GND | — spare | | 26 | GPIO 7 | — spare |
| 27 | ID_SD | — leave free (HAT EEPROM) | | 28 | ID_SC | — leave free |
| 29 | GPIO 5 | Record button switch NO | | 30 | GND | Record button: switch C and LED − |
| 31 | GPIO 6 | Play button switch NO | | 32 | GPIO 12 | LINK LED, via resistor |
| 33 | GPIO 13 | POWER LED, via resistor | | 34 | GND | Both status LED cathodes |
| 35 | GPIO 19 · I2S LRCLK | Amp LRC (mic WS chained from the amp) | | 36 | GPIO 16 | Amp SD (driven by the sound driver) |
| 37 | GPIO 26 | Modem PWRKEY — later | | 38 | GPIO 20 · I2S DIN | Mic SD (data out of the mic) |
| 39 | GND | Amp GND | | 40 | GPIO 21 · I2S DOUT | Amp DIN (data into the amp) |

Used: 18 signal pins, both 5 V pins, 7 of 8 grounds. Spare: GPIO 4, 7, 8,
9, 10, 11, both 3.3 V pins, one ground (25).

## Per part

### Record button — 16 mm, RGB ring, common cathode, resistors built in

| Button terminal | Pi pin | GPIO |
| --- | --- | --- |
| NO (switch) | 29 | GPIO 5 — input, internal pull-up; pressed = low |
| C (switch common) | 30 | GND |
| R (red) | 11 | **GPIO 17.** A second wire from this same tab goes to the mic's VDD |
| G (green) | 13 | GPIO 27 |
| B (blue) | 15 | GPIO 22 |
| − (LED common cathode) | 30 | GND (with C) |

C and − can be joined at the button and run as one ground wire.

### Play button — same part

| Button terminal | Pi pin | GPIO |
| --- | --- | --- |
| NO | 31 | GPIO 6 |
| C | 20 | GND |
| R | 16 | GPIO 23 |
| G | 18 | GPIO 24 |
| B | 22 | GPIO 25 |
| − | 20 | GND (with C) |

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

### Status LEDs — two 3 mm green LEDs

| From | Through | To | Note |
| --- | --- | --- | --- |
| Pin 32 · GPIO 12 | 220 Ω | LINK LED anode (long leg) | on the panel: right |
| Pin 33 · GPIO 13 | 220 Ω | POWER LED anode (long leg) | on the panel: left ([ADR 0020](../../docs/decisions/0020-no-mute-replay-green-link.md)) |
| Both cathodes (short leg, flat side) | — | Pin 34 · GND | |

They are on most of the time ("steady means fine"). If 220 Ω is too bright
in a bedroom, raise it to 1–2.2 kΩ.

### Modem — Waveshare SIM7670G HAT, beside the Zero, not stacked

| Connection | From | To | Note |
| --- | --- | --- | --- |
| Data | Zero's inner micro-USB, "USB" | HAT Type-C | OTG adapter + USB-A-to-C cable; appears as a network interface |
| 5 V | Zero pin 4 | HAT header pin 2 | stiffer supply for transmit bursts |
| GND | Zero pin 6 | HAT header pin 6 | |
| PWRKEY | Zero pin 37 · GPIO 26 | HAT's PWR line (via its DIP switch) | **later** — which HAT pin carries it is still to be found |
| DIP switches | — | TXD and RXD **off** | keeps GPIO 14/15 free for the console |
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
