"""What a button does when it is pushed — pure logic (ADR 0016).

The box rides in a bag, so a raw contact closure is not a press:

- A button counts as *pressed* once it has been held ≥ 0.5 s. The press fires
  at that moment, while the finger is still down, so the red light answers
  the child immediately; the release does nothing.
- Both buttons held together ≥ 3 s is the **travel lock** gesture. Both must
  go down before either one fires as a single press; a two-button hold that
  ends early is a fumble and fires nothing at all.
- While locked, single presses are ignored upstream (core.py); the lock
  gesture is the only thing that still counts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Union

from .state import MIN_PRESS_S, TRAVEL_LOCK_HOLD_S


class Button(Enum):
    RECORD = "record"
    PLAY = "play"


@dataclass(frozen=True)
class Press:
    button: Button


@dataclass(frozen=True)
class LockGesture:
    """Both buttons held for TRAVEL_LOCK_HOLD_S."""


Gesture = Union[Press, LockGesture]


@dataclass
class Gestures:
    down: Dict[Button, float] = field(default_factory=dict)   # button → when it went down
    fired: Set[Button] = field(default_factory=set)           # single presses already fired
    pair: bool = False                                        # a two-button gesture is in progress
    pair_fired: bool = False

    def contact(self, button: Button, is_down: bool, now: float) -> List[Gesture]:
        """A raw contact change from the hardware. Returns gestures that fired now."""
        if is_down:
            if button in self.down:
                return []
            self.down[button] = now
            if len(self.down) == 2 and not self.fired:
                self.pair = True
        else:
            if button not in self.down:
                return []
            held = now - self.down.pop(button)
            was_fired = button in self.fired
            self.fired.discard(button)
            if not self.down:
                pair, self.pair, self.pair_fired = self.pair, False, False
            else:
                pair = self.pair
            # A hold that reached 0.5 s counts even if no tick fell between the
            # mark and the release — the press must never depend on tick timing.
            if not pair and not was_fired and held >= MIN_PRESS_S:
                return [Press(button)]
            return []
        return self.tick(now)

    def tick(self, now: float) -> List[Gesture]:
        """Call every ~50 ms: presses fire by time held, not on release."""
        if self.pair:
            if (not self.pair_fired and len(self.down) == 2
                    and all(now - t0 >= TRAVEL_LOCK_HOLD_S for t0 in self.down.values())):
                self.pair_fired = True
                return [LockGesture()]
            return []
        out: List[Gesture] = []
        for button, t0 in self.down.items():
            if button not in self.fired and now - t0 >= MIN_PRESS_S:
                self.fired.add(button)
                out.append(Press(button))
        return out

    def held_s(self, button: Button, now: float) -> float:
        return now - self.down[button] if button in self.down else 0.0
