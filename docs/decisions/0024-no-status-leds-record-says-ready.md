# ADR 0024 — No status LEDs; Record says "ready" in blue

**Date:** 2026-09-30
**Status:** accepted (user decision) — revises [ADR 0009](0009-two-led-vocabularies.md)
(two vocabularies become one), [ADR 0016](0016-two-buttons-no-lid.md) §4
(the lock blink) and [ADR 0020](0020-no-mute-replay-green-link.md) §3–5
and §7

## Context

The box had two light channels: the buttons for the child, and two small
green status LEDs, LINK and POWER, for the adults. The user wants one:
the two RGB buttons and nothing else.

- **Power off → nothing lit.** Pulling the plug is how the box turns off
  ([ADR 0019](0019-mains-first-battery-deferred.md)), so a dark box is an
  unplugged box. A POWER LED adds nothing.
- **Ready vs not ready** — the box can reach the server, or it cannot — has
  to show on the buttons.

Record's red LED and the microphone's supply are one pin, GPIO 17 (ADR 0016):
the red can only be fully on (mic on) or off. So the status cannot use red on
Record. A first version of this ADR (same day) kept a dim red by adding a
second, diode-isolated feed to the red LED; the user rejected the diodes.

## Decision

1. **No status LEDs.** LINK and POWER, their resistors, their GPIOs (12, 13)
   and their holes in the back wall are removed. Power, link and faults stay
   in telemetry and the app.
2. **Record, when it is not recording, says ready or not ready in blue:**

   | Box | Record |
   | --- | --- |
   | unplugged | dark |
   | ready: the server answered within 2 × the check-in interval, and no fault | **steady dim blue** (30 % of the brightness setting) |
   | not ready: no network, no server, or a fault (storage, capture, modem) | **slow dim blue blink**, 1 s on, 2 s off |
   | playing a message (a Record press is ignored then) | dark |
   | travel lock on | dark |
   | recording | steady red: the mic is on |

   Steady vs blinking carries the meaning, so colour is redundant for anyone
   colour-blind. The green got-it pulse overlays it as before. Quiet hours
   cap it like every other glow. Recording still works while not ready: the
   message waits on disk and goes when the link returns.
3. **Red keeps its one meaning.** Record's red is still the mic pin, on or
   off, never dimmed or animated. No new wiring, no extra parts.
4. **The lock blink moves to Play: two quick white blinks.** It was cyan on
   both buttons, too close to the new blue on Record. Play has a free red
   channel, so white is allowed there.
5. **Play is unchanged** and stays about messages: pulsing green when one
   waits, steady green while playing.
6. **The buttons now carry one "not ready" state.** CLAUDE.md's "the buttons'
   lights have no error state" is revised: Record's blink says only "not
   ready". The child is not asked to interpret it; the app says why.

## Alternatives considered

- **Dim red for ready, yellow blink for not ready** (this ADR's first
  version) — needs two Schottky diodes on Record's R tab so the dim red never
  reaches the mic. Rejected by the user: extra parts at the button and a new
  failure mode (a broken diode lead could leave the mic on with the red dark).
- **Mic on its own GPIO**, so the red can dim freely — "no red light, no mic"
  would become a software promise. Rejected.
- **Yellow on Play for not ready** — Play's red is free, and yellow reads as
  "caution"; but Play would carry two meanings and clash with its green
  message pulse.
- **Keep LINK for the adults** — the user chose a single channel.

## Consequences

- **Wiring:** pins 32, 33 and 34 become spare; the two LEDs and resistors
  leave the BOM. Nothing else changes: see
  [WIRING.md](../../hardware/schematics/WIRING.md).
- **Firmware:** `lights.py` renders ready / not ready on Record's blue and
  the lock blink on Play; `StatusPlan`, the status LED drivers and
  `SetStatus` are gone. `Core.ready()` = link OK and no fault. The renderer
  still asserts that Record's red is 0 or 1, and 1 only while recording.
- **Brightness:** blue at 3.3 V through resistors sized for 5 V may be dim.
  Judge `READY_LEVEL` on the bench, in daylight and in a dark bedroom.
- **The enclosure** loses the two 3 mm holes in the back wall
  ([ADR 0023](0023-enclosure-layout.md), `hardware/cad/layout.json`).
- **The app** stops explaining LINK and POWER blink patterns; it explains
  "Record blinks blue" instead, with the reason.
- A not-ready box blinks all night if the network is down. Quiet hours cap
  the brightness; whether it should stop blinking at night is open.
