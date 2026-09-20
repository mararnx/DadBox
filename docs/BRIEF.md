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

1. **A four-year-old can use it alone.** One obvious action. No menus, no
   pairing dance, no "are you sure".
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

## Hardware (proposed — not yet decided)

- **Compute:** ESP32-S3 — Wi-Fi + BLE, PSRAM for audio buffers, hardware I2S,
  well-trodden audio path, a few dollars.
- **Input:** one large arcade button (record, hold-to-talk), one play button.
  Buttons big enough for small hands and hard to break.
- **Mic:** I2S MEMS, e.g. ICS-43434 or INMP441.
- **Output:** MAX98357A I2S amp + 3W speaker.
- **Indicator:** WS2812 LED ring — slow breathing glow means "a message is
  waiting". This is the whole notification system.
- **Power:** always-on USB-C, with a LiPo so it survives being unplugged and
  carried around. Not a device anyone should have to remember to charge.
- **Enclosure:** 3D printed, chunky, drop-survivable, no visible screws.

## Connectivity — the key decision

| Option | Upside | Downside |
| --- | --- | --- |
| **Wi-Fi** | Free, simple, fast | Needs the other household's password; dies when their router changes |
| **Cellular** (LTE-M/NB-IoT — SIM7080G, Blues Notecard) | Plug in and it works, anywhere, forever | ~$5-10/month, more power, more parts |

Voice is tiny: Opus at 16 kHz mono is ~2-3 KB/s, so a 30-second message is
roughly 70 KB. Cellular data cost is a rounding error. **Recommendation:
cellular.** It converts setup from a negotiation into plugging in a box.

## Software

- **Firmware:** ESP-IDF (Arduino core if speed matters more than control).
  Record → Opus encode → queue to flash → upload when there's a link.
- **Parent end:** start with a phone web app (PWA) — record, send, listen.
  A second identical box later would make it symmetric, and symmetric is better.
- **Transport:** MQTT over TLS for push to the device, HTTPS for audio blobs.
- **Backend:** as small as possible. Object storage plus a thin API. Messages
  deleted a short, fixed time after they're played.

## Constraints

- **Budget:** _TBD_
- **Deadline:** _TBD — is there a birthday or handover date?_
- **Skills / tools on hand:** _soldering, 3D printer, scope?_

## Milestones

- [ ] **M0** Breadboard: button records audio, button plays it back, locally.
- [ ] **M1** One-way: box → parent's phone.
- [ ] **M2** Two-way: parent → box, with the glow-and-chime waiting state.
- [ ] **M3** Robustness: offline queue, reconnect, battery, never a visible error.
- [ ] **M4** Custom PCB and enclosure.
- [ ] **M5** In the other house, working unattended for a month.

## Open questions

- One box or two? (Child only, or a matching one for the parent.)
- Child's age — decides one button vs two, and whether "who is this from" needs
  to be expressed at all.
- Wi-Fi or cellular. See above; this changes the BOM, the power budget and the
  enclosure.
- Message length cap? A hard stop at 60s keeps costs and attention spans sane.
- What happens to messages after they're heard — vanish, or keep a few?
- Is this a one-off for one family, or a thing other people might have?
