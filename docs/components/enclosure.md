# Enclosure

**Role.** Be a thing a child wants on their bedside table, survive a school
bag, and make a small speaker sound like something.

## Current design

A **1590DD-size die-cast aluminium box** ([ADR 0011](../decisions/0011-aluminium-1590dd-enclosure.md)),
with the plate **screwed down — nothing moves** ([ADR 0016](../decisions/0016-two-buttons-no-lid.md)).
The one on order is a Temu clone, 188 × 119 × 37.5 mm outside; Hammond's
original is ~183 × 113–115 × 32–33 mm inside. **The clone's inside is to be
measured before any layout or drilling.**

- **Round holes only**, all with a 5–23 mm step drill: 2 × 16 mm buttons
  (flange Ø21.8, ~20 mm behind the panel), the DC charge jack, a 6.5 mm SMA
  bulkhead, a drilled speaker grille pattern. No status LEDs
  ([ADR 0024](../decisions/0024-no-status-leds-record-says-ready.md)).
- **Off-the-shelf parts only** — no hole saw, no acrylic, no 3D printing, no
  custom PCB.
- **Antenna outside**, because the box is a Faraday cage: SMA bulkhead
  through a wall, short rigid stub on it ([connectivity.md](connectivity.md)).
- **Layout** ([hardware/LAYOUT.md](../../hardware/LAYOUT.md),
  [ADR 0023](../decisions/0023-enclosure-layout.md), proposed, revised
  2026-09-29): the tub the right way up with the Pi on the modem HAT
  (85 × 56.7, the Pi on its standoffs) and the amp on its floor; the flat lid
  is the top face with the buttons, grille and mic hole; antenna and 5 V socket
  in the back wall. Leads soldered into the Pi.
- **Inside:** Pi Zero 2 W on the SIM7670G HAT; the Seeed speaker in its own
  plastic enclosure (50 × 45 × 22); mic, amp; and from phase 3 the UPS
  Module 3S (93 × 86, height to measure) with a panel-mount DC jack in the
  wall ([power.md](power.md)). Until then a 5 V micro-USB supply.
- Rubber feet, so the box doesn't slide when a wall button is pressed or walk
  off a table when the speaker is loud. ~0.9 kg assembled.
- Wiring is jumper wires on the bench; something sturdier before the box
  travels in a bag (Q6).

History: the hinged lid and ring window are in
[ADR 0007](../decisions/0007-lid-gesture.md) (superseded); how the parts were
chosen is in [hardware/EVALUATION.md](../../hardware/EVALUATION.md).

## Checked

- **Faraday cage.** LTE goes out through the bulkhead; GPS, Wi-Fi and BLE are
  dead inside the closed box. Deploys over home Wi-Fi are a plate-off job; in
  the field it is Tailscale over LTE.
- The depth is the constraint: ~32–33 mm inside the Hammond. Three stacked
  boards would use all of it; the Pi-on-HAT stack is ~23 mm with soldered
  leads, and nothing hangs above it. The speaker is
  22 mm, the buttons ~20 mm behind the panel.
- The enclosure is still the acoustic system. The speaker brings its own back
  volume, so what is left to get wrong is the grille — holes too few or too
  fine and it sounds like a toy — and how the speaker seals against the
  metal. Listen in a cardboard mock-up before drilling aluminium.
- Drop survival is the aluminium's strong suit. What suffers in a bag is
  whatever sticks out: the rigid antenna stub and the raised button heads —
  an argument for the 52 mm stub if it holds signal.
- Heat: ~0.7 W in die-cast aluminium is a non-issue; charging is the case to
  watch ([power.md](power.md)).

## Questions

1. **Measure the clone** — inside length, width and depth, wall and plate
   thickness, and how far the screw bosses reach into the corners. Then
   `python3 hardware/cad/layout.py L W H` and print the templates. Nothing is
   drilled before this.
2. ~~Buttons in a wall or in the top plate?~~ — the lid, at the left end near
   the front edge (ADR 0023, proposed).
3. ~~Layout~~ — [hardware/LAYOUT.md](../../hardware/LAYOUT.md). It leaves no
   room for the deferred UPS Module 3S: a battery later means a slim flat pack
   or a taller box.
4. **Speaker grille and cavity** — hole size, pitch and pattern; speaker
   against the plate or a wall; a gasket between its housing and the metal?
   By ear, cardboard first.
5. **Mic port** — where, and how big a hole? Away from the speaker and not
   under the hand that presses Record.
6. **Sturdier internal wiring** than jumper wires on pin headers — soldered
   leads with heat-shrink, JST pairs, screw terminals? And how the boards are
   held: standoffs through the base (more holes) or adhesive ones?
   Off-the-shelf only.
7. **A handle?** A strap through two holes in the end walls costs nothing.
8. **Colour / personalisation** — does the child choose? A sticker area? A
   name? (Never a photo — it's in the other house.)
