"""Time, injected. The core never calls `time` itself: it asks the clock it was
given, so the simulator can run at 20× and jump two hours to test *resting*."""
from __future__ import annotations

import threading
import time


class Clock:
    """Real time. `now()` is monotonic seconds for intervals; `wall()` is Unix
    time for quiet hours and `created_at`."""

    def now(self) -> float:
        return time.monotonic()

    def wall(self) -> float:
        return time.time()

    def sleep(self, seconds: float) -> None:
        time.sleep(max(0.0, seconds))

    def wait(self, event: threading.Event, seconds: float) -> bool:
        return event.wait(max(0.0, seconds))


class FakeClock(Clock):
    """Simulated time: runs at `speed` × real time and can be skipped forward.

    Everything in the box that waits — the link loop, playback, the lights —
    waits on this clock, so a `skip(7200)` makes a waiting message go
    *resting* immediately and a `speed=20` makes a five-minute cap fifteen
    seconds of real time.
    """

    def __init__(self, speed: float = 1.0, wall: float | None = None):
        self._lock = threading.Lock()
        self._speed = speed
        self._base_real = time.monotonic()
        self._base_now = 0.0
        self._wall_offset = (time.time() if wall is None else wall) - self._base_now
        self._changed = threading.Condition(self._lock)

    @property
    def speed(self) -> float:
        return self._speed

    def now(self) -> float:
        with self._lock:
            return self._now_locked()

    def _now_locked(self) -> float:
        return self._base_now + (time.monotonic() - self._base_real) * self._speed

    def wall(self) -> float:
        return self.now() + self._wall_offset

    def set_speed(self, speed: float) -> None:
        with self._lock:
            self._base_now = self._now_locked()
            self._base_real = time.monotonic()
            self._speed = max(0.01, speed)
            self._changed.notify_all()

    def skip(self, seconds: float) -> None:
        """Jump forward. Waiters wake and re-check their deadlines."""
        with self._lock:
            self._base_now = self._now_locked() + seconds
            self._base_real = time.monotonic()
            self._changed.notify_all()

    def set_wall(self, wall: float) -> None:
        with self._lock:
            self._wall_offset = wall - self._now_locked()

    def sleep(self, seconds: float) -> None:
        deadline = self.now() + seconds
        with self._lock:
            while self._now_locked() < deadline:
                remaining = (deadline - self._now_locked()) / self._speed
                self._changed.wait(min(remaining, 0.25))

    def wait(self, event: threading.Event, seconds: float) -> bool:
        deadline = self.now() + seconds
        while not event.is_set():
            remaining = deadline - self.now()
            if remaining <= 0:
                return False
            if event.wait(min(remaining / self._speed, 0.1)):
                return True
        return True
