# Enclosure

**Role.** Be a thing a child wants on their bedside table, survive a school
bag, and make a 40 mm speaker sound like something.

## Current design

> **Platform change 2026-09-20 — [ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md):** inside the 1590DD: a Pi 3A+ (65 × 56) now or a Zero 2 W (65 × 30) later, the USB stick beside it (~90 × 30 × 12), three to six 18650s along the back wall (3 × = 56 × 65 × 19; 6 × = 112 × 65 × 19 — still fits), PowerBoost, amp, mic, level shifter. ~0.9–1.1 kg.

> **Decided 2026-09-20:** there is a lid ([ADR 0007](../decisions/0007-lid-gesture.md)) and a cell sized for a weekend. Mechanism (Q3) still open: pin hinge + microswitch vs magnet + hall sensor. The lid switch is the mic gate; reliability beats cleverness.

**Hammond 1590DD** die-cast aluminium ([ADR 0011](../decisions/0011-aluminium-1590dd-enclosure.md)):
188 × 120 × 37 mm outside, **183 × 113 × 32 mm inside**, 4 mm lid plate.
The plate is the hinged lid: piano hinge on the back edge, magnet catch
front, reed contact for lid state and mic power. Ring window (45 mm hole saw
+ acrylic disc) and speaker grille in the lid; 33 mm play button, two status
LEDs and USB-C through the front wall; SMA bulkhead through the back wall.
Layout sketch in [hardware/DOUBLE-CHECK.md](../../hardware/DOUBLE-CHECK.md).

Superseded: 3D-printed shell, TPU bumper, heat-set inserts.

## Checked

- The enclosure is the acoustic system. A 40-50 mm driver in a sealed 300 ml
  volume with a small port will sound like a decent smart speaker; the same
  driver in a leaky shell with a grille cut too fine will sound like a toy.
  Prototype the cavity in cardboard during phase 1, before any CAD.
- A lid (see [controls-ui.md](controls-ui.md)) is a hinge, a switch, and a
  seam — three things that fail on a printed part. A living hinge won't last;
  a pin hinge with a printed detent, or a magnetic lid with a hall sensor,
  will.
- Drop survival is the aluminium's strong suit. What breaks in a drop now is
  the antenna stub (hinged, so it folds rather than snaps) and the hinge
  screws (use M3 through the 4 mm plate with nyloc nuts, not self-tappers).
- Cellular antenna inside a plastic box is fine; inside a box with a big LiPo
  and a copper ground plane right behind it is not. Antenna placement is a
  layout constraint, not an afterthought.
- Heat: cell + modem + amp in a sealed box. See [power.md](power.md).

## Questions

1. ~~Form~~ — decided: 1590DD. It is lunchbox-shaped, which was the right
   answer anyway. A handle is still worth thinking about: a strap through two
   holes in the end walls costs nothing.
2. **Which way up?** The sketch puts the hinged plate on top (ring, speaker
   visible; mic under the lid). The alternative — plate as the base, a
   separate small hatch for the mic — avoids wires across the hinge but means
   cutting a rectangle in die-cast. Round holes only is the stronger argument.
2a. **Hinge side** — back edge (lid opens away from the child, ring faces the
   room when open) or front edge (lid opens toward the child, ring hidden)?
   Back edge keeps the *listening* light visible to the room, which is what
   it's for.
3. **Lid mechanism** if a lid: pin hinge + detent, or magnetic with a hall
   sensor? The hall sensor is the mic gate — it needs to be *reliable* rather
   than clever.
4. **Grille** — printed slots, fabric, or a metal mesh insert? Fabric sounds
   best and is child-pickable.
5. **Colour / personalisation** — does the child choose? A sticker area? A
   name? (Never a photo — it's in the other house.)
6. **Feet** — four rubber feet, so the box doesn't slide when the side
   button is pressed or walk off a table when the speaker is loud.
