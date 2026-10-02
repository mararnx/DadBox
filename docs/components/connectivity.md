# Connectivity

**Role.** Move audio in both directions over cellular, from a box that changes
houses every few days, without anyone in either house doing anything.

## Current design (ADR 0002, 0006, 0014, 0015)

- **Modem:** Waveshare **SIM7670G 4G LTE/GPS HAT** — LTE Cat-1, bands
  including 20 and 28 ([ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md)).
  On USB through the Zero's OTG cable, where it appears as a **USB Ethernet
  interface** (RNDIS/ECM): DHCP, no PPP. Its AT port is for diagnostics —
  `AT+CSQ`, `AT+CPSI?` — so signal can be read over SSH.
- **Transport:** plain HTTPS to our server, resumable 32 KB chunks
  ([PROTOCOL.md](../PROTOCOL.md)). The audio is end-to-end encrypted, so
  nobody in the path can hear it ([ADR 0017](../decisions/0017-managed-hosting-e2ee.md)).
  Tailscale SSH rides the same link.
- **SIM:** Digital Republic **Flat 1** — unlimited, 1 Mbit/s down / 0.5 up,
  Sunrise network, CHF 6/month, no contract — always, also during
  development. Swiss consumer SIMs are plain LTE: no LTE-M or NB-IoT
  ([ADR 0013](../decisions/0013-cat1-not-catm.md)). No 5G: no coverage
  benefit, more power and cost.
- **Adaptive polling, no SMS wake** ([ADR 0015](../decisions/0015-adaptive-polling.md)):

  | State | Modem | Check-in |
  | --- | --- | --- |
  | On mains | stays on | every `active_minutes` (1) |
  | On battery, conversation window open | stays on | every `active_minutes` (1) |
  | On battery, idle | off between check-ins | every `idle_minutes` (30, app-set 5–60) |

  The window opens when an upload completes or the child plays a message and
  lasts `active_window_minutes` (90). Telemetry carries `mains` and
  `next_checkin_s`; Record's blue blink and the app call the box late after 2 × the
  current interval.
- **Antenna:** the box is aluminium ([ADR 0011](../decisions/0011-aluminium-1590dd-enclosure.md)),
  so the antenna is outside: SMA bulkhead pigtail (Delock 88747, MHF/U.FL —
  connector to confirm) through a 6.5 mm hole, short rigid stub on it. Two
  stubs are bought and compared (Q3). Not ordered until the HAT is in hand.
- `dadboxctl modem on|off`, `checkin` and `sim link down` exercise all of it
  from the Mac.

## Checked

- Audio is the product; it does not route through a third party's pipe shaped
  for telemetry ([ADR 0006](../decisions/0006-bare-modem-not-notecard.md),
  [review §3](../REVIEW.md)). Our server, HTTPS, resumable uploads.
- Everything is sized to Flat 1's cap: ~10 s to upload a 5-minute message,
  ~5 s to download one. Tailscale SSH at 0.5 Mbit/s up is slow but workable;
  bulk deploys go over home Wi-Fi.
- At one check-in a minute, a check-in must stay small: one TLS session kept
  alive, a body of a few hundred bytes.
- SMS wake saves nothing — the modem must stay registered to hear the SMS —
  and puts a gateway in the path. Polling needs no one else.
- Coverage: ordinary Sunrise 4G, ~99 % of the population; band 20 is the
  indoor band. Check the two bedrooms, not the street.
- The HAT's GNSS is not used: no antenna connected, and dead inside the
  aluminium anyway.
- **A dead modem shows only as silence.** The box can show `fault: modem` as
  Record's blue blink, but it cannot report it — over the modem. This is why the
  app's "no check-in" alert is the most important notification in the system.

## Questions

1. **How is the SIM7670G's power key wired?** *Pin 7 (P4) via DIP 3, from the
   HAT schematic; the stacked header joins it to GPIO 4 (WIRING.md).* Does the
   modem start by itself when 5 V appears, and what does it draw when off? A
   high-side switch on its 5 V feed if the standby is too high
   ([power.md](power.md)).
2. **Does the Ethernet mode persist** across a reboot and a power-key cycle —
   and is it RNDIS or ECM on this module? How long from power-on to a usable
   interface? That time is the cost of every idle check-in.
3. **Which antenna wins?** Delock 90694 (52 mm; datasheet 824–960 /
   1710–2170 MHz, which misses the band 20 downlink at 791–821) against
   Delock 90682 (115 mm, 700–2700 MHz). `AT+CSQ` / `AT+CPSI?` in both
   bedrooms decides; the short one stays if it holds. First confirm the
   HAT's antenna connector.
4. **Coverage fallback** — if one bedroom is weak: the longer antenna, moving
   the box, or Wi-Fi as a secondary link now that the co-parent is on board?
   Suggest: don't build it until it's needed.
5. **Roaming** — does Flat 1 work outside Switzerland? Holidays happen.
6. **Long-poll on mains** — seconds instead of a minute. Only if a minute
   feels slow in use; carrier NAT timeouts make it the fussier option.
