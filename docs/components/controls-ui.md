# Controls & UI

**Role.** Everything a 6-9 year old sees and touches. Two verbs — *talk* and
*listen* — and one signal: *something is waiting*.

## Current design

**Two lit buttons and nothing that moves** ([ADR 0016](../decisions/0016-two-buttons-no-lid.md)).
Both are 16 mm stainless momentary buttons with a raised head and an RGB
ring light; the plate is screwed down.

- **Record** — press to start, press again to stop. Auto-stop at 5 minutes or
  after ~20 s of continuous silence. On stop: trim, encode, fsync into the
  outbox, *got it*, upload. Under 1 s of speech → discarded silently.
- **Play** — plays the oldest unheard message, one per press.
- **The button lights are the child's whole display:**

  | State | Record button | Play button |
  | --- | --- | --- |
  | Recording | **steady red** | dark |
  | Got it — the message is fsynced | one green pulse | — |
  | Message(s) waiting | ready / not ready | **pulsing green**; *resting* (dim) after 2 h |
  | Playing | dark | **steady green** |
  | Idle | ready / not ready | dark — Play repeats the last message, unannounced |
  | Travel lock | dark | two white blinks when it engages or releases; then dark (green pulse persists if a message waits) |

  **Ready** = steady dim blue: the server answered recently and nothing is
  faulty. **Not ready** = slow blue blink (1 s on, 2 s off): no network, no
  server, or a fault
  ([ADR 0024](../decisions/0024-no-status-leds-record-says-ready.md)).
  Unplugged = everything dark. (Colours as revised by ADR 0020 and ADR 0024.)

  **One "not ready" state, nothing more.** Why the box is not ready, the
  battery and the number of waiting messages are the app's.
  Priority order is in [ARCHITECTURE.md § Indication](../ARCHITECTURE.md#indication).
- **No red light, no mic.** The record button's red LED and the mic's 3.3 V
  supply are the **same GPIO pin** — a wiring fact, not firmware. That pin is
  only ever on or off: the red light is never dimmed or animated, because
  dimming it would chop the mic's supply. Hence ready / not ready in blue.
- **There are no status LEDs** (ADR 0024). A dark box is unplugged; "not
  ready" is Record's blue blink; the details are in the app.
- **The bag.** Buttons on the outside of a box in a school bag: a press must
  last ≥ 0.5 s to count; under 1 s of speech is discarded; **travel lock** —
  hold both buttons 3 s, Play blinks white twice, buttons dead until the same
  gesture again, persists across reboot; quiet hours still apply to the chime.
- **Quiet hours** (default 20:00–07:00, enforced on the device): glow yes,
  chime no, play still works. There is no mute (ADR 0020). No sender identity
  on the box — the voice says who it is in the first second.
- **Electrically:** six LED pins (2 × RGB, common cathode, resistors built
  in) driven at 3.3 V straight from GPIO with software PWM, two switch
  inputs on the Pi's internal pull-ups. Setting `led_brightness` scales
  everything except the red recording light.
- `dadboxctl record start|stop`, `play`, `led test`, `lock on|off` drive all
  of it without touching the box.

History: the lid, reed contact and NeoPixel ring are in
[ADR 0007](../decisions/0007-lid-gesture.md) (superseded).

## Checked

- **Hold-to-talk was rejected** — no child holds a button for a three-minute
  story ([review §1](../REVIEW.md)). Press-to-start, press-to-stop keeps the
  5-minute cap honest; the silence auto-stop covers the forgotten stop.
- **The bag problem is back** without a lid ([review §5](../REVIEW.md)). The
  ordered buttons have a raised head (2.3 mm proud), which a bag presses more
  easily than a flush one — so the 0.5 s press, the < 1 s discard and the
  travel lock are not optional.
- *Recording* outranks everything and never animates: a bystander has to be
  able to tell "mic on" from "message waiting" without the key. It is also a
  different button.
- *Got it* is identical online and offline. The pulse promises *safe*, not
  *delivered*; delivery is the app's.
- Which button and how it moves (steady, one pulse, breathing) carry the
  meaning; colour is redundant, for anyone colour-blind in either household.
- Ready and not ready differ by pattern (steady vs blinking), not only by
  colour. Judge the dim blue (`READY_LEVEL`) on the bench, day and night.
- "Obvious to the room" is weaker than an open lid: a red ring on a 16 mm
  button is a small light. The wiring tie keeps the promise honest; say so to
  the co-parent ([security-privacy.md](security-privacy.md)).
- Chimes are the only sound the box makes unbidden. That makes them the only
  thing that can annoy the other household. Keep them short, gentle, and
  subject to quiet hours.

## Questions

1. **Wall or top plate?** Proposed: the lid (the top face), near the front edge
   ([ADR 0023](../decisions/0023-enclosure-layout.md)). At ~20 mm behind the panel the buttons fit either.
   The plate is nicer for a child at a bedside and more exposed in a bag; a
   wall is safer in the bag and wants rubber feet so the box doesn't slide.
   Decide with the box in hand ([enclosure.md](enclosure.md)).
2. **Bright enough at 3.3 V?** The LEDs are specified for 5 V. Judge green
   and the warm mix (red + green) in a daylit room; two 74AHCT125 buffers if
   too dim. The recording red stays on its 3.3 V pin regardless — it shares
   the mic's supply. Which PWM mix reads as *warm* is by eye.
3. **Waiting at night** — a glow the child *wants* across a dark room, or dim
   enough that the co-parent doesn't mind? Probably app-set `led_brightness`
   with a quiet-hours floor; confirm by living with it.
4. **Resting after 2 h** — right threshold? A child home at 16:00 with a
   message from 09:00 should still see it. Resting is dim, not off.
5. **Travel lock, seen from outside** — does a locked box still show
   *waiting*? Should the app show the lock? That needs a telemetry field —
   [PROTOCOL.md](../PROTOCOL.md) first.
6. ~~Status LED placement~~ — moot: no status LEDs (ADR 0024).
7. ~~LINK "brief on" at each check-in~~ — moot: no status LEDs (ADR 0024).
8. ~~Charged vs on battery~~ — moot: no POWER LED (ADR 0024); the app says it.
9. **Haptics?** A small vibration on *got it* is cheap and satisfying. Worth a
   motor and one more gated consumer?
