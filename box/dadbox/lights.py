"""Rendering the two vocabularies (ADR 0009, ADR 0016). Pure: plan + time → pin levels.

The core decides *what* the lights say (a `LightsPlan`); a driver thread
renders it at ~30 Hz through `render()` and writes the result to PWM pins on
the Pi or to the simulator's screen.

One hard rule lives here and is tested: **the record button's red channel is
never anything but 0 or 1.** That pin is also the microphone's supply. It is
on while recording and off otherwise — never dimmed, never animated, never
scaled by `led_brightness`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from .state import Fault, Lights, Link, Power

RGB = Tuple[float, float, float]

DARK: RGB = (0.0, 0.0, 0.0)
RED: RGB = (1.0, 0.0, 0.0)
GREEN: RGB = (0.0, 1.0, 0.0)      # Play: pulsing = a new message, steady = playing (ADR 0020)
READY: RGB = (0.0, 0.2, 1.0)      # Record: dim slow pulse = ready to record. No red: that channel is the mic pin
LOCK_BLINK_COLOUR: RGB = (0.0, 1.0, 1.0)   # both blink twice, bright cyan; no red, so the mic pin is never touched by a cue
READY_LEVEL = 0.22                # the ready pulse peaks here (× brightness); dim by design
READY_PERIOD_S = 3.0

GOT_IT_S = 0.6                    # one green pulse (ARCHITECTURE.md § Indication)
LOCK_BLINK_S = 1.2                # both blink twice on lock and unlock (ADR 0016)
BREATHE_PERIOD_S = 4.0
RESTING_LEVEL = 0.15              # *resting*: dim, not off
QUIET_CAP = 0.3                   # quiet hours: the glow is capped, so it doesn't light a bedroom
BLINK_S = 0.05                    # status-LED blink width; ~10 ms in the ADR, 50 ms so a human sees it
STATUS_PERIOD_S = 3.0


class Cue(Enum):
    GOT_IT = "got_it"             # one green pulse on Record after the message is fsynced
    LOCK = "lock"                 # both blink twice: travel lock engaged or released


@dataclass(frozen=True)
class LightsPlan:
    lights: Lights = Lights.IDLE
    cue: Optional[Cue] = None
    cue_at: float = 0.0
    brightness: int = 40          # settings.led_brightness, 0–100
    resting: bool = False         # waiting for > 2 h without interaction
    quiet: bool = False           # quiet hours
    locked: bool = False          # travel lock: Record shows no ready pulse


@dataclass(frozen=True)
class Frame:
    record: RGB = DARK
    play: RGB = DARK


def _scale(c: RGB, k: float) -> RGB:
    return (c[0] * k, c[1] * k, c[2] * k)


def _breathe(t: float, period: float = BREATHE_PERIOD_S) -> float:
    return 0.5 - 0.5 * math.cos(2 * math.pi * t / period)


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

    record: RGB = DARK
    play: RGB = DARK

    # 2. Playing: play button steady green. Record dark — the mic cannot be used now.
    if plan.lights is Lights.PLAYING:
        play = _scale(GREEN, k)
    else:
        # Ready to record: a dim, slow pulse on Record whenever a press would start a recording.
        if not plan.locked:
            record = _scale(READY, k * READY_LEVEL * (0.25 + 0.75 * _breathe(t, READY_PERIOD_S)))
        # 4. Waiting: play button pulses green; resting (dim) after 2 h.
        if plan.lights in (Lights.WAITING, Lights.GOT_IT):
            level = RESTING_LEVEL if plan.resting else (RESTING_LEVEL + (1 - RESTING_LEVEL) * _breathe(t))
            play = _scale(GREEN, k * level)

    # Cues overlay for their duration. A cue never touches Record's red.
    if plan.cue is not None:
        x = t - plan.cue_at
        if plan.cue is Cue.GOT_IT and 0 <= x < GOT_IT_S:
            record = _scale(GREEN, k * math.sin(math.pi * x / GOT_IT_S))
        elif plan.cue is Cue.LOCK and 0 <= x < LOCK_BLINK_S and _lock_blink(x):
            record = _scale(LOCK_BLINK_COLOUR, k)
            play = _scale(LOCK_BLINK_COLOUR, k)

    assert record[0] in (0.0, 1.0), "the record button's red is the mic's supply: on or off, never PWM"
    return Frame(record=record, play=play)


def cue_active(plan: LightsPlan, t: float) -> bool:
    if plan.cue is None:
        return False
    length = GOT_IT_S if plan.cue is Cue.GOT_IT else LOCK_BLINK_S
    return 0 <= t - plan.cue_at < length


# --- The adults' channel -------------------------------------------------------------

@dataclass(frozen=True)
class StatusPlan:
    link: Link = Link.DOWN
    power: Power = Power.OK
    fault: Fault = Fault.NONE


def _blink_at(phase: float, at: float) -> bool:
    return at <= phase < at + BLINK_S


def render_status(plan: StatusPlan, t: float) -> Tuple[bool, bool]:
    """(LINK on, POWER on) at time `t`. LINK is a green LED: steady = fine."""
    phase = t % STATUS_PERIOD_S
    if plan.fault is not Fault.NONE:            # both alternate: an adult must act
        half = (t % 1.0) < 0.5
        return half, not half
    link = False
    if plan.link is Link.OK:                    # steady green: connected and the server answered (ADR 0020)
        link = True
    elif plan.link is Link.DOWN:
        link = _blink_at(phase, 0.0)
    elif plan.link is Link.DOWN_QUEUED:
        link = _blink_at(phase, 0.0) or _blink_at(phase, 0.25)
    power = False
    if plan.power in (Power.MAINS, Power.CHARGING):
        power = True
    elif plan.power is Power.LOW:
        power = _blink_at(phase, 0.0)
    return link, power
