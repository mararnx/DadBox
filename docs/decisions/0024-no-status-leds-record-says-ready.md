# ADR 0024 — No status LEDs; Record says "ready" in blue

**Date:** 2026-09-30
**Status:** accepted (user decision) — revises [ADR 0009](0009-two-led-vocabularies.md)
(two vocabularies become one), [ADR 0016](0016-two-buttons-no-lid.md) §4
(the lock blink) and [ADR 0020](0020-no-mute-replay-green-link.md) §3–5
and §7
— revised 2026-10-06 (user decision): powering on is shown on Play, see §7; ready drifts blue–green, see §8; the lock flashes both buttons with a tone, see §9

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
   | powering on, not yet ready (§7) | dark; Play runs through the colours |
   | ready: the server answered within 2 × the check-in interval, and no fault | **blue–cyan flow**, Play dark; Record dark while a message waits (§8) |
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
7. **Powering on (2026-10-06).** The box was dark for ~36 s after the plug
   went in, which looked like a dead box. Now Play runs through the colours,
   mixed ones included, from about a second after power-on until the box is
   first ready; then Play goes dark and Record shows its ready glow. In
   three layers, because nothing of ours runs at first:
   - `gpio=25=op,dh` in `config.txt`: Play blue from the firmware on.
   - `dadbox-bootlight.service` (early boot, `pinctrl`): steps Play through
     red, green, blue, 0.5 s each, from when systemd starts (~10.6 s) until
     the light driver takes the pins (it creates `/run/dadbox/bootlight-stop`).
   - **Mixes are colour-balanced.** The buttons' built-in resistors are sized
     for 5 V; at 3.3 V red outshines green and green outshines blue, so on/off
     mixes all looked red or green. The service scales mixes by a white point
     tuned by eye on the bench (red 25 %, green 63 %, blue 100 %, `BALANCE` in
     `lights.py`); pure colours stay full. The lock's white uses it too. The
     shell stage cannot dim, so it shows the three pure colours only.
   - **The rainbow is an even crossfade between equally bright primaries**
     (red 30 %, green 25 %, blue 100 %: `RAINBOW_EQUAL`), red → green → blue,
     4.5 s a round — the ready glow's lesson: hold the brightness, move only
     the colour. The early stage is now `systemd/bootlight.py` on the system
     Python with lgpio PWM (1000 Hz, 60 updates/s), so the full rainbow runs
     from ~10.6 s, not on/off steps.
   - The service stops that unit as it starts and carries a smooth rainbow
     (`booting` in the lights plan) until it is first ready. It ends for good
     at the first ready, at any press or lock, if a message is waiting (its
     green pulse matters more), or after 3 minutes, when Record's not-ready
     blink takes over. It is shown once per power-on, never again.

   Play's colours otherwise mean messages (green) and the lock (white); the
   rainbow is only ever seen right after plugging in.
8. **Ready flows (2026-10-06).** Steady dim blue becomes a glow that flows
   blue → cyan → blue once every 4 s (`READY_DRIFT_S`), easing out so it
   lingers at cyan (`READY_CYAN_DWELL`), at 60 % of the brightness setting
   (`READY_LEVEL`). Cyan is the balanced cyan at the same brightness as full
   blue, counting 25 % green as worth all of blue (`READY_GREEN`, judged on the
   bench), so the brightness holds and only the colour moves. Play stays dark
   (a mirrored flow on Play was tried the same day and taken back). Never red
   (Record's red is the mic) and never pure green (green means a message). **While a message
   waits, Record is dark** — ready or not — so Play's breathing green has the
   child's eye. Not ready is otherwise unchanged: Record's slow blue blink,
   Play dark.

   Smoothness needed two driver changes, both measured on the bench: gpiozero
   rounds PWM duty down to whole percent (a dozen visible steps at this
   dimness), so the button LEDs are driven through lgpio directly with a
   fractional duty; and only channels that change are written. Rendering stays
   at 30 Hz — 90 Hz looked no different once the duty was fine-grained. Cost:
   lgpio's software PWM is ~0.85 % of one core per 100 Hz for two pins; the
   whole service runs at ~8 % of one core.

9. **The lock, seen and heard (2026-10-06).** §4's two white blinks on Play
   become, on both buttons: **lock on** — two flashes and a falling
   two-note marimba tone (G4 → C4); **lock off** — one flash and the
   same tone rising, then back to normal; **a press while locked** — three quick
   flashes, no sound, so a child learns the box is locked rather than
   broken. Record has no white: its red is the mic's pin. So **both buttons
   flash the same cyan-white** — the balanced white without its red — rather
   than Play white and Record cyan side by side (user decision). The lock tones answer a
   press, so they sound in quiet hours at half volume, like the record tones;
   locking mid-recording stops the recording and sounds only the lock tone.

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
