# ADR 0013 — LTE Cat-1, not Cat-M; Digital Republic, not 1NCE; T-A7670G R2

**Date:** 2026-09-20
**Status:** accepted for Cat-1 and Digital Republic; the T-A7670G R2 board is superseded by [ADR 0014](0014-raspberry-pi-zero-2w.md) (Pi Zero 2 W + USB 4G stick)

## Context

The user asked whether Cat-M works with Digital Republic, whether its
bandwidth is enough, and whether the LILYGO T-A7670G R2 would be better.

- Digital Republic's support page says plainly: *"LTE CAT M1 and NB-IoT are
  not directly supported by our flat-rate SIM cards."* The T-SIM7080G-S3 is
  Cat-M/NB-IoT only — no ordinary 4G — so with that SIM it would never
  connect.
- Digital Republic sells unlimited-data SIMs on Sunrise 4G/5G with no
  contract: Flat 0.4 (0.4/0.2 Mbps) CHF 4/month, Flat 1 (1/0.5) CHF 6,
  Flat 10 (10/5) CHF 10. Sold at Digitec/Brack as 365-day cards too.
- Cat-M1 on the SIM7080G is 589 kbps down / 1.1 Mbps up on paper, ~100–300
  kbps in practice; a 5-minute ADPCM message (2.4 MB) is 1–3 minutes of
  upload. Cat-1 is 10/5 Mbps: seconds.
- Cat-1 idles at ~2 mA in sleep versus µA for Cat-M in PSM. Over a 60-hour
  weekend that is ~150 mAh — 5 % of the cell. Not a design driver.

## Decision

**LTE Cat-1**, on a **Digital Republic Flat 1** data SIM (CHF 6/month; Flat
0.4 works too), on the **LILYGO T-A7670G R2** — ESP32 (WROVER, 4 MB flash,
8 MB PSRAM), A7670G Cat-1 + GNSS, JST LiPo with charging, LTE and GPS
antennas included, CHF 37.90 and in stock at bastelgarage.ch.

Everything in ADR 0006 still holds: a bare SIMCom modem driven by
`esp_modem` over PPP, plain HTTPS to our own server, nobody in between.

## Alternatives considered

- **Stay Cat-M with 1NCE** — cheaper over ten years (€12 once) and lower
  idle power, but: B2B ordering unconfirmed for a private person, LTE-M
  coverage at both addresses unverified, and the user's actual SIM provider
  doesn't support it. Three risks removed for CHF 6/month.
- **T-SIM7670G-S3** — the same modem class on an ESP32-S3 with 16 MB flash.
  Better chip; not stocked in Switzerland, no TF slot, and a reported
  ~0.5 mA deep-sleep floor (harmless here). The fallback if the R2's 4 MB
  flash or pin count proves too tight: ~2–3 weeks by import.
- **Digital Republic Flat 0.4** — CHF 4. 0.2 Mbps up makes a 5-minute ADPCM
  message ~100 s. Works; Flat 1 halves it for CHF 2 more.

## Consequences

- **Data is unlimited.** The codec is now about latency and sound, not
  budget. ADPCM on the wire is fine indefinitely; Opus stays an optional
  M3 nicety.
- **Coverage risk collapses** from "LTE-M at both addresses" to "Sunrise 4G
  at both addresses" — ~99 % of the population.
- **Classic ESP32, not S3**: ESP-IDF target `esp32`, quad PSRAM, no native
  USB (a UART bridge — fine). I2S ×2 and the ADPCM path are unaffected.
  Opus post-hoc encoding is slower on the LX6 but still off the critical
  path.
- **4 MB flash.** OTA needs two ~1.5 MB app slots, which leaves under 1 MB.
  The never-lost outbox therefore lives on the **TF card**, with internal
  flash keeping only the most recent message as a fallback. This makes the
  SD card a dependency, contrary to what ADR 0010 hoped; the alternatives
  are dropping OTA (a box in another house you can't update) or importing
  the S3 board. Use a name-brand card, mount with sync-on-write, and treat
  a missing card as a fault on the status LEDs.
- **Pins are tight** on a WROVER after the modem and TF take theirs. Budget
  for a PCF8574 I²C expander (CHF ~3) for the slow signals — status LEDs,
  ring gate, amp shutdown, lid, button — leaving native GPIOs for I2S and
  the ring's data line.
- **GNSS is on the board.** Not needed, but it (or better, the modem's cell
  ID via `AT+CPSI`) can answer "which house is the box in" for the second
  parent — no dock resistor needed. Parked in ADR 0008's `house` field.
- Monthly cost: CHF 6, cancellable any month, upgradable to Flat 10 for
  the day you want it faster.
