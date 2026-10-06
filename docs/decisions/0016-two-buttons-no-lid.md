# ADR 0016 — Two lit buttons; no lid, no ring

**Date:** 2026-09-21
**Status:** accepted (user decision) — light colours revised by [ADR 0020](0020-no-mute-replay-green-link.md) (Play green); the status LEDs go, Record shows ready in blue and the lock blink moves to Play in [ADR 0024](0024-no-status-leds-record-says-ready.md); supersedes [ADR 0007](0007-lid-gesture.md);
revises [ADR 0009](0009-two-led-vocabularies.md) (the child's channel is the
two button lights, not a ring) and [ADR 0011](0011-aluminium-1590dd-enclosure.md)
(the plate is screwed down, not hinged)

## Context

The lid design needed a piano hinge on a die-cast plate, a magnet catch, a
reed contact, five wires across the hinge, a 45 mm window or sixteen aligned
holes for a NeoPixel ring, a level shifter and a gated 5 V rail. With
off-the-shelf parts only and no 3D printing, every one of those is a place
for a hand-built box to look and feel home-made, and the ring in an aluminium
lid was the part the user liked least.

Two 16 mm stainless momentary buttons with a raised head and RGB ring lights
(5 V, also 3.3 V; common cathode, resistors built in, NO contact, IP65;
flange Ø21.8, 23.1 mm long, head 2.3 mm proud) are ordered. They are a finished-looking
control and a light in one part and one round hole each.

## Decision

The box has **two buttons and nothing that moves**.

- **Record** — press to start, press again to stop. Auto-stop at the
  five-minute cap. On stop: trim, encode, queue, send, exactly as lid-close
  did.
- **Play** — unchanged: plays the oldest unheard message.
- The buttons' lights are the child's whole display:

  | State | Record button | Play button |
  | --- | --- | --- |
  | Recording (was *listening*) | **steady red** | dark |
  | Got it — message is fsynced | one green pulse | — |
  | Message(s) waiting | — | slow warm breathing; *resting* dim after 2 h |
  | Playing | dark | steady warm |
  | Idle | dark | dark |

  No link, battery or fault state ever appears on them. LINK and POWER status
  LEDs remain the adults' channel (ADR 0009 otherwise unchanged). The count of
  waiting messages is no longer shown on the box; the app has it.
- **The mic's supply pin and the record button's red LED are driven by the
  same GPIO.** The microphone draws ~1 mA at 3.3 V, which a Pi pin supplies
  directly. If the red light is off, the mic has no power — a wiring fact, not
  a firmware promise. This is what remains of ADR 0007's physical guarantee.
- The lid plate is fixed with its six screws. No hinge, catch, reed contact,
  magnets, ribbon across a hinge, ring, ring window, level shifter or ring
  power switch.

## Alternatives considered

- **Keep the lid (ADR 0007)** — still the better answer to the two problems
  below; rejected by the user for build complexity and looks.
- **Hold-to-talk** — self-limiting and the simplest mic gate, but no child
  holds a button for a three-minute story (ADR 0007's original objection).
- **One button + lid sensor only** — keeps the gesture, drops the ring; still
  needs the hinge.

## Consequences

What this gives up, stated plainly, because ADR 0007 existed for these:

- **The bag problem is back.** Buttons on the outside of a box in a school bag
  can start a recording or play a message aloud in a classroom. Mitigations,
  in the order they will be built:
  1. The ordered buttons have a **raised** head (2.3 mm proud), which a bag
     presses more easily than a flush one — so mitigations 2–4 are not
     optional. At ~20 mm behind the panel they fit either in a wall or in the
     top plate; the plate is nicer for a child at a bedside and more exposed
     in a bag. Decide with the box in hand.
  2. A press must last ≥ 0.5 s to count.
  3. A recording with under 1 s of speech is discarded (already the rule).
  4. **Travel lock:** hold both buttons for 3 s → both blink twice (Play blinks white twice since ADR 0024) and the
     buttons are dead until the same gesture again. Survives reboot. While locked the
     box checks in on the slow cadence with the modem off between check-ins
     ([ADR 0015](0015-adaptive-polling.md), revised 2026-10-06).
  5. Mute and quiet hours from the app still apply to playback.
- **"Obvious to the room" is weaker.** An open lid is unmistakable; a red ring
  on a button is a small light. The hardware tie between the light and the
  mic's power keeps the promise honest, but it is less visible than a lid.
  Worth saying to the co-parent.
- A child can forget to press stop. The five-minute cap, plus a stop after
  ~20 s of continuous silence, bounds it; the trim removes the tail.
- The got-it pulse still comes only after fsync (ADR 0010 unchanged).
- Simpler electrically: six LED pins (two × RGB) and two switch inputs. The
  buttons' LEDs are driven at 3.3 V straight from GPIO if bright enough
  (blue will be dim — it is barely used), otherwise through two 74AHCT125s.
  The red LED shares the mic pin and therefore stays at 3.3 V.
- Simpler mechanically: round holes only, all with the step drill (16 mm ×2,
  charge port, SMA, LEDs) plus a drilled speaker grille. No hole saw.
- `dadboxctl lid open|close` becomes `dadboxctl record start|stop`; `ring
  test` becomes `led test`. Telemetry `lid_open` becomes `recording`;
  `ring_brightness` becomes `led_brightness` (PROTOCOL.md).
