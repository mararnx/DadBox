# ADR 0014 — Raspberry Pi Zero 2 W, not an ESP32

**Date:** 2026-09-20
**Status:** accepted; **revised 2026-09-21** (modem and power section, see
[Revision](#revision-2026-09-21--cat-1-hat-not-a-usb-stick)) — supersedes the compute board in [ADR 0013](0013-cat1-not-catm.md);
cellular (Cat-1/Cat-4, Digital Republic) and [ADR 0006](0006-bare-modem-not-notecard.md)'s
principle (our own server, HTTPS, nobody in between) stand

## Context

The box lives in another house for years and is built by one person with
Claude doing the debugging. On the ESP32 that meant a serial console to be
written first, no JTAG (the TF card sits on the JTAG pins), a 4 MB flash
budget, a pin budget that fit exactly, an `esp_modem` profile that doesn't
list the A7670, and remote debugging only through a channel we'd build into
our own server. All solvable; all friction; none of it the point of the box.

On a Pi Zero 2 W the same box is a Linux machine: Python, ALSA, `ffmpeg`,
`systemd`, `journalctl`, `gdb`, and — via Tailscale over the cellular link,
which the user already runs — **SSH into the box wherever it is**. Updates
are `git pull`. Claude debugs a box in the other house live.

The cost is power: a Zero 2 W idles at ~100–115 mA with Wi-Fi, Bluetooth and
HDMI off and cannot sleep. The user chose to keep the weekend-unplugged
target and pay for it in cells.

## Decision

- **Raspberry Pi Zero 2 W**, Raspberry Pi OS Lite 64-bit, **read-only root
  overlay** plus a writable `/data` partition for the outbox, inbox and logs.
- **Tailscale** on the box; SSH from the Mac; the service is a Python package
  under `systemd`. A `dadboxctl` CLI over a Unix socket replaces the serial
  console (`state`, `lid open`, `play`, `checkin`, …).
- **Modem: a Waveshare A7670E LTE Cat-1 HAT** (revised 2026-09-21; was a
  HiLink USB stick). USB to the Pi, where it appears as an ECM/RNDIS Ethernet
  interface — still no PPP — plus an AT port on `/dev/ttyUSB2` for signal
  diagnostics. PWRKEY on a GPIO. Digital Republic Flat 1 SIM as decided.
  External antenna: IPEX → SMA bulkhead pigtail through the aluminium wall
  (ADR 0011) and a short rigid SMA stub outside.
- **Audio:** ICS-43434 mic + MAX98357A amp on the Pi's I2S via the
  `googlevoicehat-soundcard` overlay (that overlay *is* this pair — Google's
  AIY Voice HAT). Capture streams straight to `/data` as it happens; on lid
  close it is trimmed and encoded to **Opus** with `ffmpeg`. Opus from day
  one; ADPCM is no longer needed.
- **Power** (revised 2026-09-21): a 1S4P pack of four protected 18650s
  (~13 Ah) on a Waveshare UPS HAT (C) — load-sharing charger, 5 V boost,
  INA219 gauge on I²C. The modem is **off between check-ins on battery**
  (PWRKEY; a high-side switch on the HAT's 5 V feed if the measured standby
  says so) and stays on while on mains ([ADR 0015](0015-adaptive-polling.md)).
  Fallback if the UPS HAT's 1.8 A proves tight: bq24074 + Pololu S13V30F5 +
  MAX17048. Buy cells only after measuring.

## Alternatives considered

- **ESP32 (ADR 0013)** — one cell for a weekend, instant-on, in stock. The
  right product; the harder build. Kept as the documented fallback.
- **Pi with a one-day battery** — lighter; rejected by the user.
- **A USB 4G stick in HiLink mode** (the original decision here) — plug-and-play
  Ethernet, but a consumer product with mode-switch quirks on ARM, a hand-cut
  USB cable to gate its VBUS, ~350 mA when on, and no way for Claude to read
  signal quality except a web UI. Rejected 2026-09-21; see the revision.

## Consequences

- **Power budget** (rough, to be measured): Zero 2 W tuned to ~100 mA, Cat-1
  modem ~10 mA averaged on battery, ring/amp/mic gated → ~117 mA → four
  cells (~13 Ah) ≈ 60 h. The modem's off-time and the cell count are the
  levers. Charging 13 Ah at ~1 A is overnight and then some.
- **Weight** ~0.9 kg with the aluminium box. Heat ~0.7 W — fine in aluminium.
- **Boot** ~25 s; irrelevant when always on, visible after a flat battery.
- **The SD card is the whole machine.** Read-only overlay root makes it
  power-loss safe; `/data` is ext4 with `fsync`-then-rename for every message.
  Name-brand card. Keep a second imaged card in a drawer.
- **The Zero's single OTG port is the modem's** (the HAT's USB cable). Bench access is UART on
  GPIO 14/15 (a USB-serial adapter and `tools/serial_capture.py`) or Wi-Fi
  at home; in the field, Tailscale.
- **Ring at 5 V** now (the Pi rail): WS2812 data wants ≥3.5 V from 3.3 V
  logic — a 74AHCT125 level shifter, or feed the ring ~4.3 V through a diode.
- **Availability:** the Zero 2 W is in a **Europe-wide shortage** (no Swiss
  or German shop has stock; Digitec quotes January 2027; Raspberry Pi expects
  improvement over the autumn). **Development starts on a Raspberry Pi 3
  Model A+** — in stock at Pi-Shop (CHF 26.90), same BCM2837B0 silicon, same
  OS image, USB-A for the modem's cable — and the Zero 2 W is swapped into the box
  when one lands. If it never does, the 3A+ stays and the pack grows to
  ~5–6 cells. See `hardware/SOURCING.md` and `hardware/DOUBLE-CHECK.md`.
- **Never-lost gets better:** the recording is on disk while the child is
  still talking. A power loss mid-story loses nothing but the last buffer.
- The `firmware/` directory becomes `box/` — it is software now.
- The modem is Cat-1 again, as ADR 0013 decided; its SIM and network
  reasoning is unchanged.

## Revision 2026-09-21 — Cat-1 HAT, not a USB stick

[hardware/EVALUATION.md](../../hardware/EVALUATION.md) re-derived the hardware
from the brief against what Swiss shops actually stock. The platform decision
(Linux on a Pi, SSH over Tailscale, read-only root, `/data`) stands. What
changed:

- **Modem → Waveshare A7670E Cat-1 HAT** (Pi-Shop, CHF 34.90, in stock). The
  original objection to a HAT was price, stock and "AT/PPP". None holds: it is
  cheaper than the sticks that were in stock, it is on the shelf, and it
  enumerates as USB Ethernet (`AT+CUSBPIDSWITCH=9018` for ECM) exactly like
  the stick did. It adds a documented PWRKEY instead of a hand-cut VBUS cable,
  Cat-1 current (~150 mA on, vs ~350 mA), and an AT port so Claude can read
  `AT+CSQ` / `AT+CPSI?` over SSH and place the box by signal without the user.
- **Power → UPS HAT (C) + four cells.** The PowerBoost 1000C's 1 A boost was
  marginal for Pi + modem + amp. Four cells ≈ 60 h on a Zero 2 W at ~117 mA.
- **Antenna → short rigid SMA stub**, user's choice (Delock 90694, 52 mm).
  Its datasheet range (824–960 / 1710–2170 MHz) misses the LTE band 20
  downlink (791–821 MHz), Sunrise's indoor band. Band 3 (1800) is covered. The
  longer Delock 90682 (115 mm, 700–2700 MHz) is bought alongside for CHF 9 and
  the two are compared by `AT+CSQ` in both bedrooms; the short one stays if
  it holds.
- **Development starts on the Pi 3 Model A+** (confirmed by the user). On a
  3A+ the box is a mains device; the weekend target waits for the Zero 2 W.
- **No 3D printing, no custom parts** — off-the-shelf only (user).
- **SIM: Flat 1 always**, including during development. Tailscale SSH at
  1 / 0.5 Mbit/s is slow but workable; bulk deploys go over home Wi-Fi.

The modem lies flat beside the Pi in the 1590DD on its USB cable — three
stacked boards would use the full 33 mm. To verify with parts in hand: ECM
mode survives reboot and a PWRKEY cycle; PWRKEY-off standby current; UPS HAT
charge current and its 1.8 A limit under Pi boot + modem burst + amp.
