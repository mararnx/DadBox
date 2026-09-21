# ADR 0014 — Raspberry Pi Zero 2 W, not an ESP32

**Date:** 2026-09-20 · **rewritten 2026-09-21** to state the decision as it
stands after the day's revisions (history at the end)
**Status:** accepted — supersedes the compute board in [ADR 0013](0013-cat1-not-catm.md);
cellular (LTE Cat-1, Digital Republic) and [ADR 0006](0006-bare-modem-not-notecard.md)'s
principle (our own server, HTTPS) stand. Power is further narrowed by
[ADR 0019](0019-mains-first-battery-deferred.md).

## Context

The box lives in another house for years and is built by one person with
Claude doing the debugging. On the ESP32 that meant a serial console to be
written first, no JTAG, a 4 MB flash budget, a pin budget that fit exactly, an
`esp_modem` profile that doesn't list the modem, and remote debugging only
through a channel we'd build into our own server. All solvable; all friction;
none of it the point of the box.

On a Pi Zero 2 W the same box is a Linux machine: Python, ALSA, `ffmpeg`,
`systemd`, `journalctl`, `gdb`, and — via Tailscale over the cellular link,
which the user already runs — **SSH into the box wherever it is**. Claude
debugs a box in the other house live.

The cost is power: a Zero 2 W idles at ~100 mA at 5 V with Wi-Fi, Bluetooth
and HDMI off, and cannot sleep.

## Decision

- **Raspberry Pi Zero 2 W**, Raspberry Pi OS Lite 64-bit, **read-only root
  overlay** plus a writable `/data` partition for the outbox, inbox and logs.
  Bought as Pi-Shop's starter kit (board, 16 GB card, OTG cable, header to
  solder) because bare boards are out of stock across Europe.
- **Tailscale** on the box; SSH from the Mac; the service is a Python package
  under `systemd`. A `dadboxctl` CLI over a Unix socket replaces a serial
  console (`state`, `record start|stop`, `play`, `checkin`, `led test`, …).
- **Modem: Waveshare SIM7670G 4G LTE/GPS HAT** — LTE Cat-1, including bands 20
  and 28. It hangs off the Zero's single USB port (OTG cable), where it appears
  as a USB Ethernet interface — no PPP — with an AT port for diagnostics
  (`AT+CSQ`, `AT+CPSI?`) so Claude can read signal quality over SSH. It lies
  flat beside the Pi, **not stacked on the 40-pin header**, which the mic, amp
  and buttons need. Digital Republic Flat 1 SIM, always. External antenna:
  SMA bulkhead pigtail through the aluminium wall ([ADR 0011](0011-aluminium-1590dd-enclosure.md))
  and a short rigid stub outside.
- **Audio:** an I2S MEMS mic (DFRobot, MSM261S4030H0) and a MAX98357A amp on
  the Pi's one I2S bus via the `googlevoicehat-soundcard` overlay. Capture
  streams straight to `/data` as it happens; when recording stops it is
  trimmed and encoded to **Opus** with `ffmpeg`.
- **Controls:** two RGB-lit buttons on GPIO ([ADR 0016](0016-two-buttons-no-lid.md)).
- **Power:** 5 V from a micro-USB supply. The battery — a Waveshare UPS Module
  3S with three 18650s — is designed in but deferred
  ([ADR 0019](0019-mains-first-battery-deferred.md)).

## Alternatives considered

- **ESP32 (ADR 0013)** — one cell for a weekend, instant-on. The right
  product; the harder build for one person and Claude.
- **A USB 4G stick in HiLink mode** (this ADR's first version) — a consumer
  product with mode-switch quirks on ARM, a hand-cut USB cable to gate its
  power, ~350 mA when on, and signal quality only through a web UI.
- **Waveshare A7670E Cat-1 HAT** (Pi-Shop, CHF 34.90) — equivalent for our
  purposes and cheaper; the SIM7670G was bought because it came from a shop
  already being ordered from, and adds band 28.
- **Raspberry Pi 3 Model A+** as a stop-gap, **Pi 5** because it was in stock
  — twice and five times the Zero's power; both dropped when the Zero 2 W kit
  turned up.
- **5G** — no coverage benefit (coverage is the band, not the generation),
  several times the power and cost, and Flat 1 caps the speed anyway.

## Consequences

- **Boot** ~25 s. The box is mains-powered for now, so a power cut means a
  reboot; the read-only root makes that safe.
- **The SD card is the whole machine.** `/data` is ext4 with
  `fsync`-then-rename for every message. The kit's card on the bench; an
  endurance-grade card before the box leaves home; the bench card becomes the
  spare image.
- **The Zero's single USB port is the modem's.** Bench access is UART on
  GPIO 14/15 (Raspberry Pi Debug Probe and `tools/serial_capture.py`) or Wi-Fi
  at home — with the plate off, because aluminium blocks it; in the field,
  Tailscale over LTE.
- **Never-lost gets better:** the recording is on disk while the child is
  still talking. A power loss mid-story loses nothing but the last buffer.
- Heat ~0.6 W — nothing in aluminium.

## To verify with parts in hand

- The HAT enumerates as USB Ethernet on the Zero's OTG port and stays in that
  mode across reboots (mode-setting command: from the Waveshare wiki).
- Whether the HAT runs from USB power alone, how its power key is wired, and
  which antenna connector it has.
- The short Delock 90694 stub against the 115 mm 90682 by `AT+CSQ` in both
  bedrooms (the short one's datasheet range misses the band 20 downlink).
- The mic, amp and both buttons on one header with the overlay loaded.

## History

- 2026-09-20 — first version: Zero 2 W, HiLink USB 4G stick with gated VBUS,
  PowerBoost 1000C and three cells; development to start on a Pi 3A+.
- 2026-09-21 — [hardware/EVALUATION.md](../../hardware/EVALUATION.md)
  re-derived the hardware against Swiss stock: Cat-1 HAT instead of the stick.
  Its proposed UPS HAT (C) was withdrawn the same day (built around its own
  1000 mAh LiPo, Pi-Zero pogo pins only) in favour of the UPS Module 3S.
- 2026-09-21 — the user bought the SIM7670G HAT and the Zero 2 W starter kit;
  the 3A+ and a Pi 5 were dropped; lid and ring went
  ([ADR 0016](0016-two-buttons-no-lid.md)); the battery was deferred
  ([ADR 0019](0019-mains-first-battery-deferred.md)).
