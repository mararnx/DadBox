# ADR 0023 — Lid on top, electronics on the tub floor, soldered leads

**Date:** 2026-09-24, **revised 2026-09-29** (lid on top instead of the tub
upside down)
**Status:** proposed — confirm with the clone measured and the parts laid in
the tub ([ADR 0011](0011-aluminium-1590dd-enclosure.md), [ADR 0016](0016-two-buttons-no-lid.md))

## Context

The parts are in hand. Facts from the bench:

- The Waveshare SIM7670G HAT is **85 × 56.7 mm**, not the 65 × 30 mm the shop
  listed, and the Pi Zero 2 W sits **on top of it** on standoffs. The earlier
  plan of two boards side by side is moot.
- The box is ~31 mm deep inside (planning value; to measure). The Pi-on-HAT
  stack is ~19 mm to the top of the Pi. A straight 2×20 header with dupont
  plugs adds ~22 mm and does not fit.
- The first version of this ADR turned the tub upside down, pedal style. With
  the parts laid in the real box (photo, 2026-09-29), the user chose the other
  way up: the tub stands, the flat lid is the top face.

## Decision

- **The tub stands the right way up; the lid is the top face.** The lid
  carries the two buttons, the speaker grille and the mic hole. The back wall
  carries the antenna and the 5 V socket (the two status LEDs it also had
  are gone: [ADR 0024](0024-no-status-leds-record-says-ready.md)). The lid's six
  screw heads are on show.
- **Electronics sit on the tub floor:** the Pi-on-HAT stack on four M2.5
  nylon standoffs at the right end, the HAT's USB-A ports toward the front;
  the amp on foam tape at the back-left. The speaker (cone up) and the mic sit
  on foam columns that press them against the lid, sealed by foam rings; the
  buttons hang from the lid on their own nuts.
- **Buttons in the lid at the left end, near the front edge**, 30 mm apart —
  the one patch with 26 mm clear below. Mic beside the speaker, at the front.
- **Antenna through the back wall**, back-left; the hinged stub folds upright.
- **The HAT and the Pi are joined by three pins** (revised 2026-10-02,
  [ADR 0026](0026-power-and-modem-on-three-pins.md)): 4 (5 V), 6 (GND) and 7
  (its power key, GPIO 4), soldered in from below. 5 V comes in on pins 4
  and 6 as well, so the modem needs no wires of its own.
- **Leads are soldered onto the Pi's pins from above** — no dupont. It is the
  only way to fit under the lid, and it is the sturdier wiring the bag needed
  anyway. What each pin carries is
  [hardware/schematics/WIRING.md](../../hardware/schematics/WIRING.md).
- Positions, holes and clearances live in `hardware/cad/layout.json`;
  `hardware/cad/layout.py` checks them and writes 1:1 drill templates.

## Alternatives considered

- **Tub upside down, lid as a base plate** (this ADR's first version) — no
  screw heads on the top face, but the holes go into the cast tub floor, the
  electronics hang on a removable plate, and it is not how the parts ended up
  arranged in the box.
- **Stack glued upside down under the top face** — an 85 g board hanging on
  adhesive in a school bag.
- **Right-angle header with dupont** — fits the height, but plugs shaken loose
  in a bag are the failure the build is trying to avoid.
- **Buttons in the front wall** — safer in a bag, but the box slides when
  pressed and the lights face the child's knees rather than their eyes.

## Consequences

- The lid is a flat 3 mm plate: easy to clamp and drill, and a spare lid is a
  cheap second try. The tub floor gets only the four standoff holes.
- With the lid off, everything but the buttons stays in the tub; the lid folds
  back on ~10–15 cm of button and mic leads. Nothing needs unplugging.
- Screw heads on the top face: use matching stainless button-head screws.
  Rubber feet go on the tub's underside, clear of the standoff screw heads.
- The Pi's micro-USB ports face the speaker; power no longer uses them
  (ADR 0026), only the short OTG lead to the HAT does.
- No 93 × 86 mm patch is left for the deferred UPS Module 3S
  ([ADR 0019](0019-mains-first-battery-deferred.md)). A battery later means a
  slim flat pack or a taller box.
- The Pi's GPIO is committed once soldered: the pin map in `box/DESIGN.md` is
  confirmed on the bench with temporary leads before the final harness.
- The step drill goes in 2 mm steps: the 16 mm button holes are drilled at 15
  and filed to size.
