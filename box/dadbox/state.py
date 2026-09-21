"""State machines. Pure Python — no hardware imports — so this runs on the Mac.

The two button lights are the child's vocabulary (ADR 0009, ADR 0016).
Priority order, highest wins. They never show link, battery or faults; there
is deliberately no error state.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Lights(Enum):
    RECORDING = auto()   # 1. record button steady red. Same pin powers the mic: no light, no mic.
    PLAYING = auto()     # 2. play button steady warm
    GOT_IT = auto()      # 3. recording stopped AND the message is fsynced — one green pulse, ~600 ms
    WAITING = auto()     # 4. inbox > 0 — play button breathes warm; resting (dim) after 2 h
    IDLE = auto()        # 5. both dark


class Link(Enum):        # status LED, adults' vocabulary — off means fine
    OK = auto()          # off
    DOWN = auto()        # 1 blink / 3 s
    DOWN_QUEUED = auto() # 2 blinks / 3 s — messages waiting to go, safe on disk


class Power(Enum):
    OK = auto()          # off
    CHARGING = auto()    # steady
    LOW = auto()         # 1 blink / 3 s, below LOW_PCT on battery
    ASLEEP = auto()      # box shut down below SLEEP_PCT; buttons do nothing


class Fault(Enum):       # any non-NONE → LINK and POWER alternate
    NONE = auto()
    STORAGE = auto()
    MODEM = auto()
    CAPTURE = auto()
    CHARGER = auto()


RESTING_AFTER_S = 2 * 3600
LOW_PCT = 20
SLEEP_PCT = 5
MAX_MESSAGE_S = 300
MIN_SPEECH_MS = 1000
MIN_PRESS_S = 0.5
STOP_AFTER_SILENCE_S = 20
TRAVEL_LOCK_HOLD_S = 3
CHUNK_BYTES = 32 * 1024


def lights_state(*, recording: bool, playing: bool, got_it_pulse: bool, inbox: int) -> Lights:
    """Highest-priority state of the button lights for the current inputs."""
    if recording:
        return Lights.RECORDING
    if playing:
        return Lights.PLAYING
    if got_it_pulse:
        return Lights.GOT_IT
    if inbox > 0:
        return Lights.WAITING
    return Lights.IDLE


def press_counts(held_s: float) -> bool:
    """A press shorter than this is a bag, not a finger (ADR 0016)."""
    return held_s >= MIN_PRESS_S


def should_stop_recording(*, elapsed_s: float, silence_s: float) -> bool:
    """Bounds a recording nobody stopped: the cap, or a long continuous silence."""
    return elapsed_s >= MAX_MESSAGE_S or silence_s >= STOP_AFTER_SILENCE_S


@dataclass(frozen=True)
class Poll:
    """`settings.poll` from the server (PROTOCOL.md, ADR 0015). Minutes."""
    active_minutes: int = 1
    active_window_minutes: int = 90
    idle_minutes: int = 30


def poll_plan(poll: Poll, *, mains: bool, since_activity_s: float | None) -> tuple[int, bool]:
    """(seconds to the next check-in, keep the modem on until then).

    `since_activity_s` is the time since the last completed upload or played
    message — the things that open a conversation window — or None if there
    has been none since boot. A message arriving is not activity.
    """
    in_window = since_activity_s is not None and since_activity_s < poll.active_window_minutes * 60
    if mains or in_window:
        return poll.active_minutes * 60, True
    return poll.idle_minutes * 60, False
