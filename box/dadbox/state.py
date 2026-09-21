"""State machines. Pure Python — no hardware imports — so this runs on the Mac.

The ring is the child's vocabulary (ADR 0009). Priority order, highest wins.
It never shows link, battery or faults; there is deliberately no RING_ERROR.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Ring(Enum):
    LISTENING = auto()   # 1. lid open — steady, bright, never animated. The mic-is-on signal.
    PLAYING = auto()     # 2. progress sweep
    GOT_IT = auto()      # 3. lid just closed AND the message is fsynced — one pulse, ~600 ms
    WAITING = auto()     # 4. inbox > 0 — slow warm breathing, N segments; resting after 2 h
    IDLE = auto()        # 5. dark, ring rail off


class Link(Enum):        # status LED, adults' vocabulary — off means fine
    OK = auto()          # off
    DOWN = auto()        # 1 blink / 3 s
    DOWN_QUEUED = auto() # 2 blinks / 3 s — messages waiting to go, safe on disk


class Power(Enum):
    OK = auto()          # off
    CHARGING = auto()    # steady
    LOW = auto()         # 1 blink / 3 s, below LOW_PCT on battery
    ASLEEP = auto()      # box shut down below SLEEP_PCT; lid does nothing


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
CHUNK_BYTES = 32 * 1024


def ring_state(*, lid_open: bool, playing: bool, got_it_pulse: bool, inbox: int) -> Ring:
    """Highest-priority ring state for the current inputs. Unit-tested on the Mac."""
    if lid_open:
        return Ring.LISTENING
    if playing:
        return Ring.PLAYING
    if got_it_pulse:
        return Ring.GOT_IT
    if inbox > 0:
        return Ring.WAITING
    return Ring.IDLE


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
