"""Fake hardware for the simulator and the tests. Each fake records what the
box *would* do to the real part, so a test can assert on it and the web UI
can draw it."""
from __future__ import annotations

import threading
from typing import Callable, List, Optional, Tuple

from ..gestures import Button
from ..lights import DARK, Frame


class FakeButtons:
    def __init__(self):
        self.on_contact: Optional[Callable[[Button, bool], None]] = None
        self.down = {Button.RECORD: False, Button.PLAY: False}

    def watch(self, on_contact):
        self.on_contact = on_contact

    def press(self, button: Button, down: bool) -> None:
        """The mouse on the web UI, or a test."""
        if self.down[button] == down:
            return
        self.down[button] = down
        if self.on_contact:
            self.on_contact(button, down)


class FakeMicGate:
    """The one pin. `red` on the screen is drawn from *this*, not from the lights
    plan — the same wiring fact as the box."""

    def __init__(self):
        self._on = False
        self.transitions: List[bool] = []

    def set(self, on: bool) -> None:
        if on != self._on:
            self.transitions.append(on)
        self._on = on

    def is_on(self) -> bool:
        return self._on


class FakeButtonLights:
    def __init__(self):
        self.frame = Frame()

    def write(self, frame: Frame) -> None:
        self.frame = frame


class FakeStatusLeds:
    def __init__(self):
        self.link = False
        self.power = False

    def write(self, link_on: bool, power_on: bool) -> None:
        self.link, self.power = link_on, power_on


class FakeAmpGate:
    def __init__(self):
        self.on = False
        self.transitions: List[bool] = []

    def set(self, on: bool) -> None:
        if on != self.on:
            self.transitions.append(on)
        self.on = on


class FakeModem:
    """Powered or not, and a world with or without coverage (`coverage`)."""

    def __init__(self, coverage: bool = True, boot_s: float = 0.0):
        self.powered = True
        self.coverage = coverage
        self.boot_s = boot_s
        self.power_transitions: List[bool] = []
        self.signal = -85

    def power(self, on: bool) -> None:
        if on != self.powered:
            self.power_transitions.append(on)
        self.powered = on

    def is_up(self) -> bool:
        return self.powered and self.coverage

    def rssi(self) -> Optional[int]:
        return self.signal if self.is_up() else None


class FakePower:
    def __init__(self, mains: bool = True, battery_pct: Optional[int] = None, charging: bool = False):
        self.mains, self.battery_pct, self.charging = mains, battery_pct, charging

    def read(self) -> Tuple[bool, Optional[int], bool]:
        return self.mains, self.battery_pct, self.charging
