# ADR 0014 — Raspberry Pi Zero 2 W, not an ESP32

**Date:** 2026-09-20
**Status:** accepted — supersedes the compute board in [ADR 0013](0013-cat1-not-catm.md);
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
- **Modem: a USB 4G stick** in HiLink mode (Huawei E3372h-320 class) on the
  Zero's OTG port — it appears as a USB Ethernet interface; no AT commands,
  no PPP. Digital Republic Flat 1 SIM as decided. External antenna via the
  stick's TS-9 ports → SMA bulkhead (aluminium box, ADR 0011).
- **Audio:** ICS-43434 mic + MAX98357A amp on the Pi's I2S via the
  `googlevoicehat-soundcard` overlay (that overlay *is* this pair — Google's
  AIY Voice HAT). Capture streams straight to `/data` as it happens; on lid
  close it is trimmed and encoded to **Opus** with `ffmpeg`. Opus from day
  one; ADPCM is no longer needed.
- **Power:** a 1S3P pack of three protected 18650s (~9 Ah), a charger with
  load-sharing and a 5 V boost (PowerBoost 1000C class; 1 A charge → ~9 h
  from flat), a MAX17048 fuel gauge on I²C, and a **GPIO-controlled high-side
  switch on the stick's USB VBUS** so the modem is off between check-ins.
  A fourth cell if the measured budget says so.

## Alternatives considered

- **ESP32 (ADR 0013)** — one cell for a weekend, instant-on, in stock. The
  right product; the harder build. Kept as the documented fallback.
- **Pi with a one-day battery** — lighter; rejected by the user.
- **A Cat-1 HAT** (Waveshare SIM7670G) instead of a USB stick — same modem
  family, more money (CHF 56–70), out of stock at the cheaper source, and an
  AT/PPP path where the stick is plug-and-play Ethernet.

## Consequences

- **Power budget** (rough, to be measured): Pi tuned to ~75–100 mA, stick
  ~60 mA averaged with gating, ring/amp/mic gated → ~140–180 mA → 9 Ah is
  50–65 h. Tight against 60 h; the stick gate and a fourth cell are the
  levers. Charging 9 Ah at 1 A is overnight, not lunch.
- **Weight** ~0.9 kg with the aluminium box. Heat ~0.7 W — fine in aluminium.
- **Boot** ~25 s; irrelevant when always on, visible after a flat battery.
- **The SD card is the whole machine.** Read-only overlay root makes it
  power-loss safe; `/data` is ext4 with `fsync`-then-rename for every message.
  Name-brand card. Keep a second imaged card in a drawer.
- **The Zero's single OTG port is the modem's.** Bench access is UART on
  GPIO 14/15 (a USB-serial adapter and `tools/serial_capture.py`) or Wi-Fi
  at home; in the field, Tailscale.
- **Ring at 5 V** now (the Pi rail): WS2812 data wants ≥3.5 V from 3.3 V
  logic — a 74AHCT125 level shifter, or feed the ring ~4.3 V through a diode.
- **Availability:** the Zero 2 W is in a **Europe-wide shortage** (no Swiss
  or German shop has stock; Digitec quotes January 2027; Raspberry Pi expects
  improvement over the autumn). **Development starts on a Raspberry Pi 3
  Model A+** — in stock at Pi-Shop (CHF 26.90), same BCM2837B0 silicon, same
  OS image, USB-A for the stick — and the Zero 2 W is swapped into the box
  when one lands. If it never does, the 3A+ stays and the pack grows to
  ~5–6 cells. See `hardware/SOURCING.md` and `hardware/DOUBLE-CHECK.md`.
- **Never-lost gets better:** the recording is on disk while the child is
  still talking. A power loss mid-story loses nothing but the last buffer.
- The `firmware/` directory becomes `box/` — it is software now.
- Cat-4 stick on a Cat-1 decision: a superset; the Flat 1 plan caps speed
  anyway. ADR 0013's SIM and network reasoning is unchanged.
