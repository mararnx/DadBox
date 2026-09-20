# DadBox — Project Brief

## What is it?

A voice messaging device for a parent and child who live apart. The child has a
physical box: press the button, talk, let go — the parent hears it. When the
parent sends one back, the box glows and chimes, and the child presses to
listen. No screen, no reading, no phone, no account, no scrolling.

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
   message queues and sends later. The child sees the same thing either way.
4. **It is always on and always ready.** No boot time, no charging ritual, no
   app that logged itself out.
5. **A child's recorded voice is the most sensitive data here.** Minimal
   retention, no third-party analytics, no cloud transcription.
6. **The mic is powered only while the button is physically held**, with the
   ring unmistakably lit. A box that lives in two homes will be in rooms with
   other people in them; it must be obvious to everyone when it is listening,
   and incapable of listening otherwise.
7. **Both households can mute it, and both can see the mute.** A known-off beats
   a mystery silence — and a box nobody can silence is a box that gets unplugged.

## Hardware (decided — see [bom.csv](../hardware/bom/bom.csv))

- **Compute:** ESP32-S3 (N16R8) — PSRAM for audio buffers, hardware I2S,
  well-trodden audio path, a few dollars.
- **Input:** two large arcade buttons — hold-to-talk record, and play.
  Sized for a 6-9 year old and hard to break.
- **Mic:** I2S MEMS, e.g. ICS-43434 or INMP441.
- **Output:** MAX98357A I2S amp + 3W speaker.
- **Indicator:** WS2812 LED ring — slow breathing glow means "a message is
  waiting", one lit segment per message. This is the whole notification system.
- **Power:** internal protected LiPo + USB-C with power-path charging. The box
  travels with the child, so the battery is mandatory rather than a nicety
  ([ADR 0005](decisions/0005-battery-required.md)).
- **Enclosure:** 3D printed, chunky, drop-survivable, no visible screws. It
  lives in a bag between two houses — treat drops as the normal case.

## Connectivity — decided: cellular

The box travels between two homes, and that is what settles it. A device that
changes network every few days would need credentials for both, re-provisioning
after any router change in either house, and would fail silently in whichever
home nobody is checking. It carries its own network instead.

Using a Blues Notecard, whose data plan is bundled with the hardware: no
monthly bill, no carrier account, no SIM to activate. Voice is tiny, so data
volume is not a constraint.

Full reasoning in [ADR 0002](decisions/0002-cellular-not-wifi.md).

## Software

- **Firmware:** ESP-IDF (Arduino core if speed matters more than control).
  Record → Opus encode → queue to flash → upload when there's a link.
- **Parent end:** a native iOS app (SwiftUI + APNs). Notification reliability
  is the product — a message you notice six hours late defeats the device
  ([ADR 0004](decisions/0004-native-ios-app.md)). A second box would later join
  as another client of the same protocol.
- **Transport:** Notecard → Notehub → backend. HTTPS for the app.
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
- **Skills / tools on hand:** _soldering, 3D printer, scope?_

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
- Battery required, with protection at the cell — [ADR 0005](decisions/0005-battery-required.md)
- The box travels with the child between both homes
- The co-parent is on board: placement is flexible, consent is a conversation,
  and they get a mute that is visible in the app
- Ages 6-9: two buttons, message count, no text anywhere
- **5 minutes** per message, not 60 seconds. Data is effectively free and
  cutting a child off mid-story is not
- Building rather than buying — the making is part of the point

## Still open

- Does a message vanish after it's heard, or can a few be kept?
- Quiet hours: what window? (Glow yes, chime no, until morning.)
- Where the server runs — a Pi at home keeps a child's voice off other people's
  computers, at the cost of your uptime
- Is there a date this needs to exist by?
- **Cellular coverage at both addresses — verify before ordering phase 2.**
