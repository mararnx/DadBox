# DadBox — Project Brief

## What is it?

A voice messaging device for a parent and child who live apart. The child has a
physical box with two lit buttons: press **Record**, talk, press it again — the
parent hears it. When the parent sends one back, the **Play** button glows and
the box chimes, and the child presses play. No screen, no reading, no phone, no
account, no scrolling.

The point is asynchronous presence. A phone call demands both people be free at
the same moment, and a kid on a video call with a parent they miss often just
goes quiet. A box that holds a voice until someone is ready to hear it fits how
a child actually stays close to someone who isn't there.

## Design principles

1. **A six-year-old can use it alone.** Two buttons, both obvious. No menus,
   no pairing dance, no "are you sure".
2. **It works without the other household's ongoing cooperation.** Setup that
   depends on someone else's Wi-Fi password, router, or goodwill is setup that
   breaks. This is the single most important constraint and it drives the
   connectivity choice below.
3. **It never shows an error a child has to interpret.** Offline means the
   message queues and sends later — and is never lost. Recording works the
   same either way; Record glows dim blue when the box is ready and blinks
   blue when it is not, and the app says why
   ([ADR 0024](decisions/0024-no-status-leds-record-says-ready.md)).
4. **It is always on and always ready.** No boot time, no charging ritual, no
   app that logged itself out.
5. **A child's recorded voice is the most sensitive data here.** End-to-end
   encrypted, no third-party analytics, no cloud transcription.
6. **The mic is powered only while recording, with the Record button lit
   red.** The mic's supply and the red light are the same GPIO pin — no light,
   no mic, by wiring rather than by promise. A box that lives in two homes
   will be in rooms with other people in them; it must be obvious to everyone
   when it is listening, and incapable of listening otherwise.
7. **There is no mute** ([ADR 0020](decisions/0020-no-mute-replay-green-link.md)).
   Quiet hours, enforced on the device and set from the app, keep it silent
   at night; the volume setting and the plug are the rest.

## Hardware (decided — see [bom.csv](../hardware/bom/bom.csv))

Off-the-shelf parts only: no custom PCB, no 3D printing.

- **Compute:** Raspberry Pi Zero 2 W running Raspberry Pi OS Lite, with a
  read-only root and a writable `/data` partition
  ([ADR 0014](decisions/0014-raspberry-pi-zero-2w.md)). Reachable over
  Tailscale from anywhere — the box in the other house is one `ssh` away.
- **Input and display:** two 16 mm stainless buttons with RGB ring lights —
  **Record** (press to start, press again to stop) and **Play** (oldest
  unheard message). Their lights are the box's whole display: steady red
  while recording, one green pulse for *got it*, steady dim blue on Record
  when ready and a slow blue blink when not, a pulsing green on Play when a message waits,
  steady green while playing
  ([ADR 0016](decisions/0016-two-buttons-no-lid.md),
  [ADR 0020](decisions/0020-no-mute-replay-green-link.md),
  [ADR 0024](decisions/0024-no-status-leds-record-says-ready.md)). Nothing moves.
- **No status LEDs.** A dark box is unplugged (ADR 0024).
- **Mic:** DFRobot I2S MEMS module (MSM261S4030H0), powered from the same pin
  that lights the Record button red.
- **Output:** MAX98357A I2S amp + Seeed 5 W 4 Ω speaker in its own plastic
  enclosure.
- **Modem:** Waveshare SIM7670G LTE Cat-1 HAT on the Pi's USB port — it is
  just a USB Ethernet interface, plus an AT port for diagnostics — off between
  check-ins when on battery. Digital Republic Flat 1 data SIM, CHF 6/month
  ([ADR 0013](decisions/0013-cat1-not-catm.md)). External SMA stub antenna,
  because aluminium.
- **Power:** the first box is **mains only** — a 5 V micro-USB supply, on
  while plugged in ([ADR 0019](decisions/0019-mains-first-battery-deferred.md)). The battery is designed in but
  deferred: Waveshare UPS Module 3S — three protected 18650s in series
  (~36 Wh), 5 V out, charges while powering, battery gauge over I²C — charged
  from its own 12.6 V barrel-jack supply, one per house. Sized for **about two
  days unplugged** on a Pi that cannot sleep; the 60 h weekend of
  [ADR 0005](decisions/0005-battery-required.md) is not quite met. Everything
  that can be gated is: button lights, amp, mic, and on battery the modem.
  Bought after measuring; until then the box runs from a 5 V micro-USB supply.
- **Enclosure:** 1590DD-size die-cast aluminium box, 188 × 119 × 37.5 mm
  outside, plate screwed down, round holes only
  ([ADR 0011](decisions/0011-aluminium-1590dd-enclosure.md)). It lives in a
  bag between two houses — aluminium treats drops as weather.
- **The bag:** a press must last 0.5 s to count, a recording with under a
  second of speech is discarded, and holding both buttons for 3 s sets a
  **travel lock** that survives a reboot.

## Connectivity — decided: cellular

The box travels between two homes, and that is what settles it. A device that
changes network every few days would need credentials for both, re-provisioning
after any router change in either house, and would fail silently in whichever
home nobody is checking. It carries its own network instead.

An LTE Cat-1 modem HAT on the Pi, appearing as an ordinary Ethernet interface,
so the box speaks HTTPS straight to our server on a Digital Republic Flat 1 SIM
(unlimited at 1/0.5 Mbit/s, CHF 6/month, no contract, Sunrise network). The
audio is end-to-end encrypted, so nobody in the path can hear it. Plugged in,
the box checks in every minute; on battery the modem is powered off between
half-hourly check-ins, except for 90 minutes after the child uses the box
([ADR 0015](decisions/0015-adaptive-polling.md)).

[ADR 0002](decisions/0002-cellular-not-wifi.md) for cellular,
[ADR 0006](decisions/0006-bare-modem-not-notecard.md) for "our own server,
nobody in between", [ADR 0013](decisions/0013-cat1-not-catm.md) for the SIM,
[ADR 0014](decisions/0014-raspberry-pi-zero-2w.md) for the modem.

## Software

- **Box software:** a Python service under `systemd`, driven on the bench and
  in the field by `dadboxctl`. Record pressed → capture to disk as it happens
  → Record pressed again → trim, Opus, encrypt, queue → resumable HTTPS upload
  when there's a link.
- **Parent end:** a native iOS app (SwiftUI + APNs), the only human-facing
  client. Notification reliability is the product — a message you notice six
  hours late defeats the device ([ADR 0004](decisions/0004-native-ios-app.md)).
  A second box would later join as another client of the same protocol.
- **Transport:** HTTPS from the box and from the app, directly to our server.
- **Backend:** as small as possible. One managed host: a thin API plus object
  storage that holds ciphertext it cannot play
  ([ADR 0017](decisions/0017-managed-hosting-e2ee.md)). Messages are archived
  forever, on the server and in the app; deleting one is a deliberate act in
  the app ([ADR 0018](decisions/0018-archive-forever.md)).

See [ARCHITECTURE.md](ARCHITECTURE.md) for the audio path and state machine,
[PROTOCOL.md](PROTOCOL.md) for the wire contract, and [ROADMAP.md](ROADMAP.md)
for how the four streams fit together.

## Scope

A one-off for one family, built deliberately rather than bought. Hand-assembled,
config baked in, no onboarding flow, no support burden, no compliance work.

Tonies and Yoto already do parent → child voice into a box. Neither does the
reply direction well, and the reply is the point: a child pressing a button and
being heard. Everything else in the design serves that.

## Constraints

- **Budget:** ~CHF 330 in parts across the four phases, tools aside, plus
  CHF 6/month for the SIM (see [bom.csv](../hardware/bom/bom.csv))
- **Deadline:** _TBD — is there a birthday or handover date?_
- **Skills / tools on hand:** soldering iron and a 5–23 mm step drill (covers
  every hole in the box), a Raspberry Pi Debug Probe for the bench console.
  _A scope?_

## Milestones

- [ ] **M0** Bench: Record records audio, Play plays it back, locally.
- [ ] **M1** One-way: box → parent's phone.
- [ ] **M2** Two-way: parent → box, with the glow-and-chime waiting state.
- [ ] **M3** Robustness: offline queue, reconnect, battery, never a visible error.
- [ ] **M4** The real box: drilled enclosure, wiring that survives a bag.
- [ ] **M5** In the other house, working unattended for a month.

## Decided

- One box for the child; parent uses a native iOS app — [ADR 0003](decisions/0003-one-box-plus-app.md), [ADR 0004](decisions/0004-native-ios-app.md)
- Cellular, not Wi-Fi, because the box travels — [ADR 0002](decisions/0002-cellular-not-wifi.md)
- A bare LTE modem and our own server, not a Notecard — [ADR 0006](decisions/0006-bare-modem-not-notecard.md)
- Two lit buttons, Record and Play; nothing that moves; mic power tied to the red light; travel lock for the bag — [ADR 0016](decisions/0016-two-buttons-no-lid.md) (supersedes the lid of [ADR 0007](decisions/0007-lid-gesture.md))
- A battery, everything gated; the target is a weekend unplugged — [ADR 0005](decisions/0005-battery-required.md)
- Two parents in the protocol, one in the build — [ADR 0008](decisions/0008-two-parents-later.md)
- ~~The button lights are the child's; LINK and POWER LEDs are the adults'~~ — [ADR 0009](decisions/0009-two-led-vocabularies.md), superseded
- No status LEDs; Record steady blue when ready, blinking blue when not; the lock blink is white on Play — [ADR 0024](decisions/0024-no-status-leds-record-says-ready.md)
- Nothing recorded is ever lost; the outbox is never evicted — [ADR 0010](decisions/0010-nothing-is-lost.md)
- 1590DD-size aluminium enclosure, plate screwed down, antenna outside — [ADR 0011](decisions/0011-aluminium-1590dd-enclosure.md)
- SIM **fixed**: Digital Republic Flat 1, 1 Mbit/s, CHF 6/month, also during development — [ADR 0013](decisions/0013-cat1-not-catm.md)
- Raspberry Pi Zero 2 W + SIM7670G Cat-1 HAT, UPS Module 3S + three 18650s, Tailscale — [ADR 0014](decisions/0014-raspberry-pi-zero-2w.md) (supersedes the boards in 0012/0013)
- Adaptive polling: every minute on mains or for 90 min after use, every 30 min idle on battery; no SMS wake — [ADR 0015](decisions/0015-adaptive-polling.md)
- One managed host, audio end-to-end encrypted, iOS the only client, no server-side transcode — [ADR 0017](decisions/0017-managed-hosting-e2ee.md)
- Messages are archived forever — [ADR 0018](decisions/0018-archive-forever.md)
- The box travels with the child between both homes
- The co-parent is on board: placement is flexible, consent is a conversation
- No mute; Play with nothing new repeats the last message; (its LINK and POWER LEDs are gone, ADR 0024) — [ADR 0020](decisions/0020-no-mute-replay-green-link.md)
- Ages 6-9: two buttons, no text anywhere; the message count lives in the app
- **5 minutes** per message. Opus on the wire from day one
- Building rather than buying — the making is part of the point

## Still open

Per-component questions live in [components/](components/README.md). The
ones that matter most:

- Which managed host — Cloudflare Workers + R2 + D1 is proposed
  ([ADR 0017](decisions/0017-managed-hosting-e2ee.md))
- The key ceremony: iCloud Keychain sync and a paper copy — lose the key, lose
  the archive
- Replay / favourites / inbox grace after play
- Buttons in a wall or in the top plate — decide with the box in hand
- Sturdier internal wiring than jumper wires before the box travels in a bag
- Is there a date this needs to exist by?
- **Sunrise 4G in both bedrooms** — `AT+CSQ` with the HAT in hand; it also
  picks the antenna (52 mm stub or 115 mm).
