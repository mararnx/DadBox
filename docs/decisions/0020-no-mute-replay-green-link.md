# ADR 0020 — No mute; Play repeats the last message; LINK steady green; POWER steady on USB power

**Date:** 2026-09-22
**Status:** accepted (user decisions, taken while driving the simulator) —
revises [ADR 0009](0009-two-led-vocabularies.md) ("off means fine" becomes
"steady means fine" for both status LEDs) and the mute of BRIEF principle 7;
closes controls-ui Q7/Q8, audio-playback Q3, storage-queue Q1

## Context

The first day with the virtual box (`python3 -m dadbox.sim`) put the LED
rules and the button rules in front of the user for the first time. Four
things looked wrong in use.

## Decisions

1. **There is no mute.** The mute setting, its two per-parent flags and the
   who-set-it metadata are removed from PROTOCOL.md § Settings. Quiet hours
   (device-enforced, app-set) are how a household keeps the box silent at
   night; the volume setting and the plug cover the rest. The box ignores a
   `mute` key from an older server.
2. **Play with nothing new repeats the last message.** The box keeps its
   most recently played message on disk (the rest leave after the server's
   `played` ack, as before). A replay lights the Play button steady warm like
   any playback, opens the conversation window, and is **not** reported to
   the server again. Something new always wins over the replay.
3. **LINK is a green LED, steady while the link is fine** — the box checked
   in and the server answered within 2 × the current interval. Blink
   patterns for trouble are unchanged (1 blink / 3 s: no connection; 2: and
   messages queued). The "brief on per check-in" idea is moot.
4. **POWER is steady while external power is present on the USB port**, with
   or without a battery, charging or full; off when unplugged; blinking below
   20 % on battery. (Decided earlier the same day; recorded here.)

## Alternatives considered

- **Keep mute** — the original argument was "a box nobody can silence gets
  unplugged". The user's view: quiet hours and the plug are enough, and one
  fewer remote switch over a child's box is a feature.
- **Replay any message with a gesture** (long press, double press) — more
  vocabulary for the child; rejected. Older messages are the app's archive.
- **LINK off when fine** (ADR 0009) — a dark LED and a dead box look the
  same at a glance; a steady green does not.

## Consequences

- PROTOCOL.md changed first; **server and iOS must drop `mute`** from
  `PATCH /settings`, the settings object and the settings UI. The box and
  the fake server already have.
- The inbox on the box holds one played message at all times once anything
  has been heard; eviction under pressure may still take it.
- Status LEDs are on most of the time now: choose dim parts and a large
  series resistor so a bedroom stays dark (to judge with the parts in hand).
  LINK green, POWER amber or white — the BOM says so.
- ADR 0009's rule stands in spirit: two channels, and the child's has no
  error state.
