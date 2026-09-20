# ADR 0006 — Bare LTE-M modem with PPP, not a Notecard

**Date:** 2026-09-20
**Status:** accepted — supersedes the module choice in [ADR 0002](0002-cellular-not-wifi.md); the specific module moved from Cat-M (SIM7080G) to Cat-1 (A7670G) in [ADR 0013](0013-cat1-not-catm.md), the principle unchanged

## Context

The Notecard was picked for "it just connects" and its bundled data plan, both
of which are real. It was never checked against the actual workload. This
device moves 100 KB–2.4 MB audio blobs in both directions; the Notecard moves
small JSON notes, with a large-binary path that is awkward, synchronous, and
size-limited, and that routes the child's voice through Notehub.

## Decision

A bare LTE-M module from the SIM7080G family, driven by ESP-IDF's `esp_modem`
component over PPP. The ESP32 gets a real IP stack and speaks plain HTTPS to
our own server. A flat-rate IoT SIM (1NCE-type: one payment, 500 MB, ten
years, EU-wide roaming) instead of a carrier account.

NB-IoT is explicitly *not* acceptable — too slow for audio. The module must
register on LTE-M (Cat-M1), and coverage must be checked for LTE-M
specifically at both addresses.

## Alternatives considered

- **Notecard via `card.binary` + proxy routes** — works in principle, chunk
  size unverified, needs the modem held up per transfer, and a third party
  handles the bytes. Kept as the fallback: it can sit on the same header if
  the modem bring-up fails, and the protocol doesn't care.
- **SIM7600 (Cat-1)** — faster, more power, more money, needs a full LTE plan.
  Overkill for 64 kbps audio.
- **ESP32 with Wi-Fi as a secondary link** — cheap to leave a hook for; not
  built until needed.

## Consequences

- Modem bring-up is now an M1 task: PWRKEY sequencing, band selection, APN,
  antenna placement, PSM/eDRX. Budget a weekend or two and expect the second
  to be about power, not connectivity.
- The SIM7080G's UART is **1.8 V logic**. The breakout must level-shift, or
  the ESP32 will not be talking to a modem for long.
- Upload/download become ordinary HTTP with `Content-Range` — resumable for
  free. The server loses its Notehub route handler and gets simpler.
- Nobody but our server sees the audio. On-device encryption remains worth
  doing (see `docs/components/security-privacy.md`) but is no longer
  load-bearing.
- OTA is a plain HTTPS fetch. It should be in scope for M3.
- Half the hardware cost of the Notecard route.
