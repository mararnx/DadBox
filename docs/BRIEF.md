# DadBox — Project Brief

## What is it?

A voice messaging device for a parent and child who live apart. The child has a
physical box: open the lid, talk, close it — the parent hears it. When the
parent sends one back, the box glows and chimes, and the child presses play.
No screen, no reading, no phone, no account, no scrolling.

The point is asynchronous presence. A phone call demands both people be free at
the same moment, and a kid on a video call with a parent they miss often just
goes quiet. A box that holds a voice until someone is ready to hear it fits how
a child actually stays close to someone who isn't there.

## Design principles

1. **A six-year-old can use it alone.** A lid and one button, both obvious.
   No menus, no pairing dance, no "are you sure".
2. **It works without the other household's ongoing cooperation.** Setup that
   depends on someone else's Wi-Fi password, router, or goodwill is setup that
   breaks. This is the single most important constraint and it drives the
   connectivity choice below.
3. **It never shows an error a child has to interpret.** Offline means the
   message queues and sends later — and is never lost. The child sees the same
   thing either way; two small status LEDs tell the adults.
4. **It is always on and always ready.** No boot time, no charging ritual, no
   app that logged itself out.
5. **A child's recorded voice is the most sensitive data here.** Minimal
   retention, no third-party analytics, no cloud transcription.
6. **The mic is powered only while the lid is open**, by a switch, with the
   ring unmistakably lit. A box that lives in two homes will be in rooms with
   other people in them; it must be obvious to everyone when it is listening,
   and incapable of listening otherwise.
7. **Both households can mute it, and both can see the mute.** A known-off beats
   a mystery silence — and a box nobody can silence is a box that gets unplugged.

## Hardware (decided — see [bom.csv](../hardware/bom/bom.csv))

- **Compute:** Raspberry Pi Zero 2 W running Linux, with a read-only root and
  a writable data partition ([ADR 0014](decisions/0014-raspberry-pi-zero-2w.md)).
  Reachable over Tailscale from anywhere — the box in the other house is one
  `ssh` away.
- **Input:** a lid (open to talk, close to send —
  [ADR 0007](decisions/0007-lid-gesture.md)) and one recessed play button.
  A closed box has nothing a school bag can press.
- **Mic:** I2S MEMS, e.g. ICS-43434 or INMP441.
- **Output:** MAX98357A I2S amp + 3W speaker.
- **Indicator:** WS2812 LED ring, power-gated — slow breathing glow means "a
  message is waiting", one lit segment per message. This is the whole
  notification system.
- **Modem:** a USB 4G stick (HiLink — it's just an Ethernet interface), off
  between check-ins; Digital Republic unlimited data SIM, CHF 6/month
  ([ADR 0013](decisions/0013-cat1-not-catm.md)); external SMA antenna because
  aluminium.
- **Power:** three protected 18650s (~9 Ah) with a load-sharing charger and
  5 V boost, sized for **a weekend unplugged** on a Pi that cannot sleep.
  Everything that can be gated is, including the modem's USB power
  ([ADR 0005](decisions/0005-battery-required.md), [ADR 0014](decisions/0014-raspberry-pi-zero-2w.md)).
- **Enclosure:** Hammond 1590DD die-cast aluminium, 188 × 120 × 37 mm, with
  its plate hinged as the lid ([ADR 0011](decisions/0011-aluminium-1590dd-enclosure.md)).
  It lives in a bag between two houses — aluminium treats drops as weather.

## Connectivity — decided: cellular

The box travels between two homes, and that is what settles it. A device that
changes network every few days would need credentials for both, re-provisioning
after any router change in either house, and would fail silently in whichever
home nobody is checking. It carries its own network instead.

A USB 4G stick on the Pi, appearing as an ordinary Ethernet interface, so the
box speaks HTTPS straight to our server — nobody else in the path — on a
Digital Republic unlimited data SIM (CHF 6/month, no contract). Powered off
between check-ins.

[ADR 0002](decisions/0002-cellular-not-wifi.md) for cellular,
[ADR 0006](decisions/0006-bare-modem-not-notecard.md) for "our own server,
nobody in between", [ADR 0013](decisions/0013-cat1-not-catm.md) for the SIM,
[ADR 0014](decisions/0014-raspberry-pi-zero-2w.md) for the stick.

## Software

- **Box software:** a Python service under `systemd`. Lid open → capture to
  disk as it happens → lid closed → trim, Opus, queue → resumable HTTPS
  upload when there's a link.
- **Parent end:** a native iOS app (SwiftUI + APNs). Notification reliability
  is the product — a message you notice six hours late defeats the device
  ([ADR 0004](decisions/0004-native-ios-app.md)). A second box would later join
  as another client of the same protocol.
- **Transport:** HTTPS from the box and from the app, directly to our server.
- **Backend:** as small as possible. Object storage plus a thin API. Messages
  deleted a short, fixed time after they're played.

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

- **Budget:** ~$150-180 in parts for the prototype (see BOM)
- **Deadline:** _TBD — is there a birthday or handover date?_
- **Skills / tools on hand:** _soldering, step drill + 45 mm hole saw for the aluminium, scope?_

## Milestones

- [ ] **M0** Breadboard: button records audio, button plays it back, locally.
- [ ] **M1** One-way: box → parent's phone.
- [ ] **M2** Two-way: parent → box, with the glow-and-chime waiting state.
- [ ] **M3** Robustness: offline queue, reconnect, battery, never a visible error.
- [ ] **M4** Custom PCB and enclosure.
- [ ] **M5** In the other house, working unattended for a month.

## Decided

- One box for the child; parent uses a native iOS app — [ADR 0003](decisions/0003-one-box-plus-app.md), [ADR 0004](decisions/0004-native-ios-app.md)
- Cellular, not Wi-Fi, because the box travels — [ADR 0002](decisions/0002-cellular-not-wifi.md)
- Bare LTE modem over PPP, not a Notecard — [ADR 0006](decisions/0006-bare-modem-not-notecard.md)
- Lid: open to talk, close to send; one play button outside — [ADR 0007](decisions/0007-lid-gesture.md)
- Battery for a weekend unplugged, everything gated — [ADR 0005](decisions/0005-battery-required.md)
- Two parents in the protocol, one in the build — [ADR 0008](decisions/0008-two-parents-later.md)
- The ring is the child's; LINK and POWER LEDs are the adults' — [ADR 0009](decisions/0009-two-led-vocabularies.md)
- Nothing recorded is ever lost; the outbox is never evicted — [ADR 0010](decisions/0010-nothing-is-lost.md)
- Hammond 1590DD aluminium enclosure, plate hinged as the lid — [ADR 0011](decisions/0011-aluminium-1590dd-enclosure.md)
- LTE Cat-1/Cat-4 on a Digital Republic SIM — [ADR 0013](decisions/0013-cat1-not-catm.md)
- Raspberry Pi Zero 2 W + USB 4G stick, three-cell pack, Tailscale — [ADR 0014](decisions/0014-raspberry-pi-zero-2w.md) (supersedes the boards in 0012/0013)
- The box travels with the child between both homes
- The co-parent is on board: placement is flexible, consent is a conversation,
  and they get a mute that is visible in the app
- Ages 6-9: lid + one button, message count, no text anywhere
- **5 minutes** per message. Opus on the wire from day one
- Building rather than buying — the making is part of the point

## Still open

Per-component questions live in [components/](components/README.md). The
ones that matter most:

- On-device encryption in v1 (recommended)
- Where the server runs
- Replay / favourites / inbox grace after play
- Lid mechanism: pin hinge + switch, or magnet + hall sensor
- Is there a date this needs to exist by?
- **Sunrise 4G in both bedrooms — check before ordering phase 2.**
