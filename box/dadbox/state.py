"""State machines. Pure Python — no hardware imports — so this runs on the Mac.

The two button lights are the box's only lights (ADR 0016, ADR 0024).
`Lights` is their priority order, highest wins. On top of it, Record says
whether the box is ready: a blue–cyan flow when the server answered recently
and nothing is faulty, a slow blue blink when not. There are no status LEDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Lights(Enum):
    RECORDING = auto()   # 1. record button steady red. Same pin powers the mic: no light, no mic.
    PLAYING = auto()     # 2. play button steady warm
    GOT_IT = auto()      # 3. recording stopped AND the message is fsynced — one green pulse, ~600 ms
    WAITING = auto()     # 4. inbox > 0 — play button breathes warm; resting (dim) after 2 h
    IDLE = auto()        # 5. Play dark; Record shows ready (steady blue) or not (blinking blue)


class Link(Enum):        # Record steady blue when OK, blinking blue otherwise (ADR 0024); telemetry
    OK = auto()          # connected and the server answered within 2 × the check-in interval
    DOWN = auto()
    DOWN_QUEUED = auto() # down, and messages are waiting to go, safe on disk


class Power(Enum):      # telemetry and the app only; no light (ADR 0024)
    OK = auto()          # on battery, above LOW_PCT
    MAINS = auto()       # external power present (the USB port)
    CHARGING = auto()    # external power present and the pack is charging
    LOW = auto()         # below LOW_PCT on battery
    ASLEEP = auto()      # box shut down below SLEEP_PCT; buttons do nothing


class Fault(Enum):       # any non-NONE → Record blinks blue, and a push (ADR 0024)
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
    """`settings.poll` from the server (PROTOCOL.md, ADR 0015, ADR 0021). Minutes."""
    active_minutes: int = 1
    active_window_minutes: int = 90
    idle_minutes: int = 30
    backstop_minutes: int = 10


BOOT_LIGHT_MAX_S = 3 * 60   # the power-on rainbow gives way to "not ready" if the box isn't ready by then

JUST_USED_S = 5 * 60     # after an upload or a played message the parent often answers at once…
JUST_USED_POLL_S = 15    # …so check in this often meanwhile, whatever the power (ADR 0015, revised)
LINK_OK_MIN_S = 120      # the link is up while the last good check-in is at least this recent

RING_MIN_GAP_S = 5       # at most one ring-triggered round this often; later rings wait, never drop (ADR 0021)


def doorbell_wanted(*, mains: bool, locked: bool = False) -> bool:
    """The doorbell is open only on mains until the battery exists and its
    heartbeat cost has been measured (ADR 0021), and never while the travel
    lock is on: a locked box may be on a power bank in a bag (ADR 0015)."""
    return mains and not locked


def poll_plan(poll: Poll, *, mains: bool, since_activity_s: float | None,
              doorbell: bool = False, locked: bool = False) -> tuple[int, bool]:
    """(seconds to the next check-in, keep the modem on until then).

    `since_activity_s` is the time since the last completed upload or played
    message — the things that open a conversation window — or None if there
    has been none since boot. A message arriving is not activity.
    The first JUST_USED_S of that are polled every JUST_USED_POLL_S.
    `doorbell` is true while the doorbell is joined: the timer then only backs
    it up. A doorbell that is not joined changes nothing (ADR 0021).
    `locked` is the travel lock: the battery's idle cadence whatever the power,
    because a power bank looks like mains and nobody can play a reply anyway.
    """
    if locked:
        return poll.idle_minutes * 60, False
    if since_activity_s is not None and since_activity_s < JUST_USED_S:
        return JUST_USED_POLL_S, True
    if mains and doorbell:
        return poll.backstop_minutes * 60, True
    in_window = since_activity_s is not None and since_activity_s < poll.active_window_minutes * 60
    if mains or in_window:
        return poll.active_minutes * 60, True
    return poll.idle_minutes * 60, False
