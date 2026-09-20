# Controls & UI

**Role.** Everything a 6-9 year old sees and touches. Two verbs — *talk* and
*listen* — and one signal: *something is waiting*.

## Current design

> **Platform change 2026-09-20 — [ADR 0014](../decisions/0014-raspberry-pi-zero-2w.md):** GPIO via `gpiozero` (lid as an interrupt), ring via SPI (`rpi_ws281x`) with a 74AHCT125 level shifter because the ring now runs at the Pi's 5 V; `dadboxctl` replaces the serial console.

> **Decided 2026-09-20:** **lid** — open to talk, close to send ([ADR 0007](../decisions/0007-lid-gesture.md)). Play button outside, recessed (Q2). Quiet hours: glow yes, chime no, play works (Q4). Mute = no sound, glow persists, app shows who (Q5). No sender identity on the box (Q7). Sleeping state: very slow, very dim pulse (Q6).

A lid (open to talk, close to send) with a reed contact that is also the mic's
power switch; one illuminated 33 mm play button through the front wall; a
16-pixel LED ring behind an acrylic disc in the lid; two status LEDs; chimes;
quiet hours enforced on-device; and a mute both households can set and see.

## Checked

- **Hold-to-talk × 5-minute cap × physical mic gating is inconsistent** —
  [review §1](../REVIEW.md). Something gives.
- **Transport lock is missing** — [review §5](../REVIEW.md). Buttons on the
  outside of a box that lives in a bag are a bug.
- Both are answered at once by a **lid**:

  ```
  closed   → idle. Nothing on the outside but the ring. Bag-safe.
  open     → mic powered (lid switch on the load switch), ring lit
             "listening", record for up to 5 minutes. No time pressure.
  close    → stop, trim, encode, queue, send. One pulse.
  play btn → inside the lid, or the only thing on the outside?
  ```

  Open questions in that sketch: where the play button lives, whether opening
  the lid *always* records (probably: yes, that's the gesture), and what an
  open lid with no speech does (trim to nothing, send nothing).

- **LED logic validated 2026-09-20** — the full priority table is in
  [ARCHITECTURE.md § Indication](../ARCHITECTURE.md#indication). What the
  validation found:
  - The ring was carrying two vocabularies (messages *and* link/sleep state).
    Split: the ring is the child's, two discrete status LEDs (LINK, POWER)
    are the adults' — [ADR 0009](../decisions/0009-two-led-vocabularies.md).
  - *Listening* must outrank *waiting* and must never animate: a bystander
    has to be able to tell "mic on" from "message waiting" without the key.
  - *Got it* must be identical online and offline. The pulse promises *safe*,
    not *delivered*; delivery is the adults' channel.
  - *Waiting* at full breathing all weekend costs ~30 % of the cell. It drops
    to *resting* (one breath / 10 s) after 2 h without interaction.
  - There was no boot state. Added: one sweep.
  - The status LEDs use patterns, not colours, and 10 ms blinks — so they are
    invisible in a dark bedroom and free.
- "Message count as lit segments" reads fine to a 7-year-old. A 4-year-old
  reads "more light = more"; that also works. Above ~8 waiting, just fill the
  ring — the number stops mattering.
- Ring colours must not be the only channel for anyone colour-blind in either
  household — use brightness and motion, not hue, to carry meaning.
- Chimes are the only sound the box makes unbidden. That makes them the only
  thing that can annoy the other household. Keep them short, gentle, and
  subject to mute and quiet hours.

## Questions

1. **Lid, or buttons?** Gates the enclosure, the mic gating circuit, the cap,
   and the shopping list (a lid switch instead of one arcade button).
2. ~~Play: inside or outside?~~ Outside, **through the front wall** — the
   1590DD is 32 mm inside and every arcade button is deeper than that. The
   33 mm button is illuminated: light it during *waiting* so the child knows
   what to press, dark otherwise. A second, quieter channel for the same
   fact as the ring.
2b. **Play: inside or outside?** (original) Outside: a child can listen without "opening
   to talk". Inside: nothing on the outside at all, and listening becomes
   part of the opening ritual. Suggest outside, recessed.
3. **What does "waiting" look like?** Slow breathe in a warm colour; N
   segments. Should it be visible across a dark room at night (a nightlight
   the child *wants*) or dim enough not to be (a nightlight the co-parent
   doesn't)? Probably app-set brightness with a quiet-hours floor.
4. **Quiet hours** — window? Default 20:00-07:00? Set per house?
   Behaviour: glow yes, chime no. Does play still work during quiet hours?
   Suggest yes — if the child is awake and presses it, that's their call.
5. **Mute** — mute what, exactly? Chimes only (glow still shows)? Or fully
   dark? Suggest: mute = no sound; glow persists. The app shows who muted and
   when.
6. **The "sleeping" state** — a box with no link for a day should look
   different from a box with nothing waiting, without looking *broken*.
   A very slow, very dim pulse? Or nothing, and let the adults handle it?
   This is the emotional-design question in the brief; it deserves an answer.
7. **Any sender identity on the box?** If a second parent gets the app, does
   the child need to know who a message is from before playing it? The voice
   tells them in the first second. Suggest: no.
8. **Haptics?** A small vibration on "sent" is cheap and satisfying. Worth a
   motor?
9. **Status LED placement** — beside the USB-C port, on the back, on the
   underside? They must be findable by an adult and ignorable by the child.
10. **LINK "brief on" at each sync** — helpful while placing the box, but is a
    flash every 10 minutes at night acceptable? Suggest: only while charging,
    or only for the first hour after power-up.
11. **Resting after 2 h** — right threshold? A child home from school at 16:00
    with a message that arrived at 09:00 should still see it glowing.
    Resting is dim, not off, so probably fine — but confirm by living with it.
12. **Should the box show *charged* distinctly from *on battery*?** Both are
    "POWER off". A parent packing the bag wants to know it's full. Suggest:
    POWER steady while charging, one long blink when the cable is plugged into
    a full cell, then off.
