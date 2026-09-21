# ADR 0011 — Hammond 1590DD die-cast aluminium enclosure

**Date:** 2026-09-20
**Status:** accepted — revised by [ADR 0016](0016-two-buttons-no-lid.md): the plate is screwed down, not hinged; no ring window; two 16 mm buttons through a wall or the plate. Earlier note: — layout revised for the Pi Zero 2 W, USB stick and three-cell pack ([ADR 0014](0014-raspberry-pi-zero-2w.md)); the Faraday-cage and 32 mm consequences are unchanged

## Context

The box travels between two homes in a child's bag for years. A printed
shell would need a bumper, a second revision, and would still crack. The
user chose a die-cast aluminium 1590DD: 188 × 120 × 37 mm outside,
**183 × 113 × 32 mm inside**, 4 mm lid on six screws, IP54, ~0.5 kg.

## Decision

The 1590DD, with its flat plate as the hinged lid of [ADR 0007](0007-lid-gesture.md):
piano hinge on the back edge, magnet catch at the front, reed contact for
lid state and mic power. Ring window and speaker grille in the lid plate;
play button, status LEDs and USB-C through the front wall; SMA antenna
bulkhead through the back wall. Everything is a round hole.

## Consequences

- **Faraday cage.** The LTE antenna is external via an SMA bulkhead and a
  u.FL pigtail. GPS, Wi-Fi and BLE are dead inside and none are needed.
- **32 mm inside** rules out any top-mounted arcade button (33–52 mm deep)
  and the 50 mm speaker (30 mm). Button goes through the side wall; speaker
  is the 40 mm / 17 mm one.
- Five wires cross the hinge (ring ×3, speaker ×2) on a short ribbon.
- ~0.7 kg assembled. Sturdy beyond argument; not light. Feet so it doesn't
  slide when the side button is pressed.
- Heat is a non-issue. Machining is drilling only.
- The enclosure is no longer the last phase's problem: it is bought in
  phase 1 so fit is proven with the audio.
