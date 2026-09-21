# Connectivity

**Role.** Move audio in both directions over cellular, from a box that changes
houses every few days, without anyone in either house doing anything.

## Current design (ADR 0002, ADR 0006)

> **Revised 2026-09-21 — [ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md) rev., [ADR 0015](../decisions/0015-adaptive-polling.md):** the modem is a **Waveshare A7670E LTE Cat-1 HAT**, not a USB stick — still a USB Ethernet interface (ECM), plus an AT port for `AT+CSQ`, gated by PWRKEY. Antenna: IPEX → SMA bulkhead, short rigid Delock 90694 stub outside (90682 as the comparison). Polling is adaptive: 1 min on mains or for 90 min after the child uses the box, 30 min idle on battery with the modem off in between. No SMS wake. Flat 1 always. Where the text below says "stick", read "modem HAT".

> **Platform change 2026-09-20 — [ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md):** the modem is a **USB 4G stick in HiLink mode** on the Zero's OTG port — a `cdc_ether` Ethernet interface, no AT, no PPP. Its VBUS is switched by a GPIO so it is off between check-ins. Cat-4, on the same Digital Republic Flat 1 SIM. External antenna via the stick's TS-9 ports → SMA bulkhead. Tailscale rides the same link.

> **Decided 2026-09-20:** **bare LTE-M modem** (SIM7080G-class) over `esp_modem` PPP, flat-rate IoT SIM ([ADR 0006](../decisions/0006-bare-modem-not-notecard.md)). Poll, not push (Q3): check-in every `poll_minutes` (default 10, app-set) and after any upload. Q2: inbound latency = poll interval. Notecard remains the fallback.

Cellular via a **USB 4G stick in HiLink mode** on the Pi
([ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md)) — a `cdc_ether`
Ethernet interface, DHCP from the stick, no AT, no PPP — plain HTTPS to our
server. Resumable 32 KB chunks; check-in poll on an app-set interval; the
stick's 5 V is GPIO-gated between check-ins. **Digital Republic Flat 1** data
SIM — **fixed by the user**: unlimited, 1 Mbit/s down / 0.5 up, Sunrise 4G,
CHF 6/month, no contract. Everything upstream of the stick is sized to that
cap: ~10 s to upload a 5-minute message, ~5 s to download one, and Tailscale
SSH is comfortable at 0.5 Mbit/s up.

Why not Cat-M: Digital Republic does not support Cat-M1/NB-IoT, Cat-M is
~100-300 kbps real-world (minutes per long message), and its power advantage
(µA vs ~2 mA asleep) is worth ~120 mAh over a weekend — 4 % of the cell.

**Antenna:** the box is aluminium ([ADR 0011](../decisions/0011-aluminium-1590dd-enclosure.md)),
so the board's IPEX antenna is useless inside it. u.FL pigtail → bulkhead SMA
through the back wall → hinged stub antenna outside.

## Checked — this is the weakest part of the architecture

See [review §3](../REVIEW.md). The Notecard was chosen for "it just connects",
which is true, and for its bundled data, which is real. It was **not** checked
against the actual workload, which is moving ~100-600 KB blobs, not telemetry.

| | Notecard (via `card.binary` + proxy routes) | Bare LTE modem + `esp_modem` PPP (historical comparison; module is now Cat-1) |
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

Coverage: ordinary Sunrise 4G — ~99 % of the population. Check the two
bedrooms, not the street; a hinged external antenna helps.

## Questions

1. ~~Notecard or bare modem?~~ — resolved: neither; a USB stick on a Linux box.
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
