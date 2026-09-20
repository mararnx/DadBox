# Enclosure

**Role.** Be a thing a child wants on their bedside table, survive a school
bag, and make a 40 mm speaker sound like something.

## Current design

> **Decided 2026-09-20:** there is a lid ([ADR 0007](../decisions/0007-lid-gesture.md)) and a cell sized for a weekend. Mechanism (Q3) still open: pin hinge + microswitch vs magnet + hall sensor. The lid switch is the mic gate; reliability beats cleverness.

3D-printed, chunky, drop-survivable, no visible screws, heat-set inserts.

## Checked

- The enclosure is the acoustic system. A 40-50 mm driver in a sealed 300 ml
  volume with a small port will sound like a decent smart speaker; the same
  driver in a leaky shell with a grille cut too fine will sound like a toy.
  Prototype the cavity in cardboard during phase 1, before any CAD.
- A lid (see [controls-ui.md](controls-ui.md)) is a hinge, a switch, and a
  seam — three things that fail on a printed part. A living hinge won't last;
  a pin hinge with a printed detent, or a magnetic lid with a hall sensor,
  will.
- Drop survival for PLA is poor. PETG or ASA for the shell; TPU for a bumper
  or feet.
- Cellular antenna inside a plastic box is fine; inside a box with a big LiPo
  and a copper ground plane right behind it is not. Antenna placement is a
  layout constraint, not an afterthought.
- Heat: cell + modem + amp in a sealed box. See [power.md](power.md).

## Questions

1. **Form** — cube, puck, lunchbox, something with a handle? A handle is not a
   joke: a thing with a handle gets carried, a thing without gets thrown in.
2. **Size** — governed by the cell and the speaker. Lunchbox-ish (~150 × 100 ×
   70 mm) fits everything; a 100 mm cube is tighter but more object-like.
3. **Lid mechanism** if a lid: pin hinge + detent, or magnetic with a hall
   sensor? The hall sensor is the mic gate — it needs to be *reliable* rather
   than clever.
4. **Grille** — printed slots, fabric, or a metal mesh insert? Fabric sounds
   best and is child-pickable.
5. **Colour / personalisation** — does the child choose? A sticker area? A
   name? (Never a photo — it's in the other house.)
6. **Feet / bumper** — TPU ring? Also stops it walking off a table when the
   speaker is loud.
