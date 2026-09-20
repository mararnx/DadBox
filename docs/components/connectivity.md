# Connectivity

**Role.** Move audio in both directions over cellular, from a box that changes
houses every few days, without anyone in either house doing anything.

## Current design (ADR 0002, ADR 0006)

> **Decided 2026-09-20:** **bare LTE-M modem** (SIM7080G-class) over `esp_modem` PPP, flat-rate IoT SIM ([ADR 0006](../decisions/0006-bare-modem-not-notecard.md)). Poll, not push (Q3): check-in every `poll_minutes` (default 10, app-set) and after any upload. Q2: inbound latency = poll interval. Notecard remains the fallback.

Cellular via a SIM7080G-class LTE-M module on UART, `esp_modem` PPP giving the
ESP32 an IP stack, plain HTTPS to our server. Resumable 32 KB chunks; check-in
poll on an app-set interval. Flat-rate IoT SIM.

## Checked — this is the weakest part of the architecture

See [review §3](../REVIEW.md). The Notecard was chosen for "it just connects",
which is true, and for its bundled data, which is real. It was **not** checked
against the actual workload, which is moving ~100-600 KB blobs, not telemetry.

| | Notecard (via `card.binary` + proxy routes) | Bare LTE-M modem + `esp_modem` PPP |
| --- | --- | --- |
| Getting online | trivial — the whole point of the product | modem bring-up, bands, APN, antenna: a weekend, maybe two |
| Moving audio | awkward: ~100 KB binary buffer (unverified), synchronous `web.post`, Notehub proxy | plain HTTPS to our server; resumable uploads are just `Content-Range` |
| Inbound to box | inbound notefile, or `web.get` binary | HTTP poll, or hold an MQTT session |
| Who sees the audio | Notehub, unless encrypted on-device | nobody but our server |
| Data plan | bundled 500 MB / 10 yr, no account | flat-rate IoT SIM (1NCE-type: ~€10 one-off, 500 MB, 10 yr, EU) or Hologram-type pay-as-you-go |
| Hardware cost | ~$64 | ~$30 (SIM7080G breakout + SIM) |
| Power management | handled for you | PSM/eDRX yours to configure; well documented, fiddly |
| OTA path | via Notehub, works | via our server, works |
| Risk shape | low risk it connects; **unverified** it moves audio well | real risk in bring-up; no risk in the payload path |

Recommendation: **bare modem**. Audio is the product, and it should not route
through a pipe shaped for something else — nor through a third party. The
integration cost is real, but it is the sort of work this project exists for,
and it falls in M1 where nothing else is blocked by it. The Notecard remains the
fallback if the modem fights back — it can be swapped in later on the same
I2C/UART header without touching the protocol.

Coverage: LTE-M is broadly deployed in Germany, Switzerland and Austria; NB-IoT
too, but NB-IoT is too slow for audio. Check LTE-M specifically, at both
addresses, on the carrier the SIM roams onto.

## Questions

1. **Notecard or bare modem?** — gates phase 2 of the shopping list.
2. **Acceptable latency, each direction.** Parent → box: does "within 15
   minutes" satisfy, or does the glow need to appear within a minute? Box →
   parent: seconds, presumably. This decides poll interval vs. held session,
   and therefore the power budget.
3. **Poll or push?** With PPP, an MQTT session with a long keepalive gives
   near-instant inbound at modest power *if* the modem's PSM cooperates. A
   simple HTTP poll every N minutes is dumber and more robust. Suggest: poll,
   at an interval set by the app (the answer to question 2), with the box
   also polling immediately after any upload.
4. **Coverage fallback** — if LTE-M is weak in one bedroom, what then? An
   external antenna, moving the charger, or Wi-Fi as a *secondary* link now
   that the co-parent is on board? Suggest: leave the header for a Wi-Fi
   fallback in firmware, don't build it until it's needed.
5. **Roaming** — does the SIM need to work outside the home country? Holidays
   happen. Flat-rate IoT SIMs generally roam across the EU; confirm.
6. **What happens when the modem is dead** — hardware-dead, not offline. The
   box should notice its own modem is unresponsive and report it… over the
   modem. So it can't. This is the one failure that only shows as silence, and
   it is why the app's "no check-in for N hours" alert is the most important
   notification in the system.
