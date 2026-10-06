"""Rendering the button lights (ADR 0016, ADR 0024). Pure: plan + time → pin levels.

The core decides *what* the lights say (a `LightsPlan`); a driver thread
renders it at ~30 Hz through `render()` and writes the result to PWM pins on
the Pi or to the simulator's screen.

One hard rule lives here and is tested: **the record button's red channel is
never anything but 0 or 1.** That pin is also the microphone's supply. It is
on while recording and off otherwise — never dimmed, never animated, never
scaled by `led_brightness`. Everything else Record says — ready, not ready,
got it — is blue or green (ADR 0024).
"""
from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from .state import Lights

RGB = Tuple[float, float, float]

DARK: RGB = (0.0, 0.0, 0.0)
RED: RGB = (1.0, 0.0, 0.0)
BLUE: RGB = (0.0, 0.0, 1.0)       # Record: steady dim = ready, slow blink = not ready (ADR 0024)
WHITE: RGB = (1.0, 1.0, 1.0)      # the lock flashes, on both buttons (Record without its red)
GREEN: RGB = (0.0, 1.0, 0.0)      # Play: pulsing = a new message, steady = playing (ADR 0020)

# The buttons' resistors are sized for 5 V and we drive them at 3.3 V: red gets far
# more current than green, green more than blue, and any mix looks red (or green).
# Mixes are scaled by this balance, then lifted so the strongest channel is full.
# White = (0.25, 0.63, 1.0), tuned by eye on the bench, 2026-10-06. Pure colours unchanged.
BALANCE: RGB = (0.25, 0.63, 1.0)

GOT_IT_S = 0.6                    # one green pulse (ARCHITECTURE.md § Indication)
LOCK_BLINK_S = 1.2                # lock on: both buttons flash white twice (ADR 0016, ADR 0024 §9)
UNLOCK_FLASH_S = 0.5              # lock off: one white flash, then back to normal
LOCKED_PRESS_S = 0.9              # a press while locked: three quick white flashes, "still locked"
BREATHE_PERIOD_S = 4.0
RESTING_LEVEL = 0.15              # *resting*: dim, not off
QUIET_CAP = 0.3                   # quiet hours: the glow is capped, so it doesn't light a bedroom
READY_LEVEL = 0.6                 # Record's dim glow: ready drifts blue–green, not ready blinks blue (ADR 0024)
READY_DRIFT_S = 4.0               # ready: blue → cyan → blue, once in this long
READY_CYAN_DWELL = 2.0            # 1 = even pace; higher = more time at cyan
READY_GREEN = 0.25                # the green as bright to the eye as full blue (judge on the bench)
NOT_READY_PERIOD_S = 3.0          # not ready: 1 s on, 2 s off
NOT_READY_ON_S = 1.0
RAINBOW_PERIOD_S = 3.0           # powering on: Play runs through every colour, Record dark (ADR 0024 revised)


class Cue(Enum):
    GOT_IT = "got_it"             # one green pulse on Record after the message is fsynced
    LOCK = "lock"                 # travel lock engaged: both buttons flash white twice
    UNLOCK = "unlock"             # travel lock released: one white flash
    LOCKED_PRESS = "locked_press" # a press while locked: three quick white flashes


@dataclass(frozen=True)
class LightsPlan:
    lights: Lights = Lights.IDLE
    cue: Optional[Cue] = None
    cue_at: float = 0.0
    brightness: int = 40          # settings.led_brightness, 0–100
    resting: bool = False         # waiting for > 2 h without interaction
    quiet: bool = False           # quiet hours
    locked: bool = False          # travel lock: Record shows neither ready nor not-ready
    ready: bool = False           # the server answered recently and nothing is faulty (ADR 0024)
    booting: bool = False         # powered on, not yet ready: the rainbow on Play


@dataclass(frozen=True)
class Frame:
    record: RGB = DARK
    play: RGB = DARK


def _scale(c: RGB, k: float) -> RGB:
    return (c[0] * k, c[1] * k, c[2] * k)


def _breathe(t: float, period: float = BREATHE_PERIOD_S) -> float:
    return 0.5 - 0.5 * math.cos(2 * math.pi * t / period)


def balanced(c: RGB) -> RGB:
    """A colour as the eye should see it on these buttons (BALANCE)."""
    m = (c[0] * BALANCE[0], c[1] * BALANCE[1], c[2] * BALANCE[2])
    top = max(m)
    return DARK if top == 0 else (m[0] / top, m[1] / top, m[2] / top)


def _rainbow(t: float) -> RGB:
    return balanced(colorsys.hsv_to_rgb((t / RAINBOW_PERIOD_S) % 1.0, 1.0, 1.0))


def _ready_cyan() -> RGB:
    """Balanced cyan (green : blue as in BALANCE) as bright to the eye as full blue,
    counting READY_GREEN of green as worth all of blue."""
    ratio = BALANCE[1] / BALANCE[2]
    b = 1.0 / (1.0 + ratio / READY_GREEN)
    return (0.0, ratio * b, b)


def ready_colour(t: float) -> RGB:
    """Record's ready glow: blue ↔ cyan, slowly, never red (the mic's pin) and never
    pure green (green means a message)."""
    # There and back, easing out so it lingers at cyan; a straight crossfade in duty
    # between two colours that look equally bright, so the brightness holds and only
    # the colour moves.
    phase = (t / READY_DRIFT_S) % 1.0
    u = 2 * phase if phase < 0.5 else 2 - 2 * phase                  # an even walk 0 → 1 → 0
    x = 1 - (1 - u) ** READY_CYAN_DWELL                               # 0 = blue, 1 = cyan
    c = _ready_cyan()
    return (0.0, x * c[1], (1 - x) + x * c[2])


def _lock_white() -> Tuple[RGB, RGB]:
    """(Record, Play) white. Record's red is the mic's pin, so its "white" is the
    balanced green and blue alone — a bright cyan-white."""
    w = balanced(WHITE)
    return (0.0, w[1], w[2]), w


def _lock_blink(x: float) -> bool:
    """Two blinks in LOCK_BLINK_S: on–off–on–off."""
    phase = x / LOCK_BLINK_S
    return (0.0 <= phase < 0.2) or (0.4 <= phase < 0.6)


def render(plan: LightsPlan, t: float) -> Frame:
    """Pin levels 0..1 for both buttons at time `t` (same clock as `cue_at`)."""
    k = max(0, min(100, plan.brightness)) / 100.0
    if plan.quiet:
        k = min(k, QUIET_CAP)

    # 1. Recording: steady red, exactly full, whatever the brightness setting.
    if plan.lights is Lights.RECORDING:
        return Frame(record=RED, play=DARK)

    # Powering on: until the box is first ready, Play runs through the colours and
    # Record stays dark. Anything the child does ends it (the core clears `booting`).
    if plan.booting and plan.lights is Lights.IDLE:
        return Frame(record=DARK, play=_scale(_rainbow(t), k))

    record: RGB = DARK
    play: RGB = DARK

    # Record, when not recording: a dim glow drifting slowly through blue and green =
    # ready to record and the server is reachable; slow dim blue blink = not (no network,
    # no server, or a fault). Dark when locked, while playing — a Record press is
    # ignored during playback — and while a message waits, so Play's green has the
    # child's eye (ADR 0024 §8).
    if not plan.locked and plan.lights not in (Lights.PLAYING, Lights.WAITING):
        if plan.ready:
            record = _scale(ready_colour(t), k * READY_LEVEL)
        elif (t % NOT_READY_PERIOD_S) < NOT_READY_ON_S:
            record = _scale(BLUE, k * READY_LEVEL)

    # 2. Playing: play button steady green.
    if plan.lights is Lights.PLAYING:
        play = _scale(GREEN, k)
    # 4. Waiting: play button pulses green; resting (dim) after 2 h. 5. Idle: both dark.
    elif plan.lights in (Lights.WAITING, Lights.GOT_IT):
        level = RESTING_LEVEL if plan.resting else (RESTING_LEVEL + (1 - RESTING_LEVEL) * _breathe(t))
        play = _scale(GREEN, k * level)

    # Cues overlay for their duration. A cue never touches Record's red.
    if plan.cue is not None:
        x = t - plan.cue_at
        if plan.cue is Cue.GOT_IT and 0 <= x < GOT_IT_S:
            record = _scale(GREEN, k * math.sin(math.pi * x / GOT_IT_S))    # replaces the blue
        else:
            flash = ((plan.cue is Cue.LOCK and 0 <= x < LOCK_BLINK_S and _lock_blink(x))
                     or (plan.cue is Cue.UNLOCK and 0 <= x < UNLOCK_FLASH_S * 0.7)
                     or (plan.cue is Cue.LOCKED_PRESS and 0 <= x < LOCKED_PRESS_S
                         and (x / (LOCKED_PRESS_S / 3)) % 1.0 < 0.5))
            if flash:
                rw, pw = _lock_white()
                record, play = _scale(rw, k), _scale(pw, k)

    assert record[0] == 0.0, "the record button's red is the mic's supply: only RECORDING lights it"
    return Frame(record=record, play=play)


def cue_active(plan: LightsPlan, t: float) -> bool:
    if plan.cue is None:
        return False
    length = {Cue.GOT_IT: GOT_IT_S, Cue.LOCK: LOCK_BLINK_S, Cue.UNLOCK: UNLOCK_FLASH_S,
              Cue.LOCKED_PRESS: LOCKED_PRESS_S}[plan.cue]
    return 0 <= t - plan.cue_at < length
