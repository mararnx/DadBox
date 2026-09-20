"""State machines. Pure Python — no hardware imports — so this runs on the Mac.

The ring is the child's vocabulary (ADR 0009). Priority order, highest wins.
It never shows link, battery or faults; there is deliberately no RING_ERROR.
"""
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
CHECKIN_DEFAULT_MIN = 10


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
