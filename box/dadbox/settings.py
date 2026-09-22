"""`settings` as the server sends them on every check-in (PROTOCOL.md § Settings),
parsed tolerantly and kept on /data so quiet hours work through a reboot with
no link."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, time as dtime, timezone
from typing import Any, Dict

from .state import Poll

try:
    from zoneinfo import ZoneInfo
except ImportError:                                            # pragma: no cover
    ZoneInfo = None  # type: ignore


@dataclass(frozen=True)
class QuietHours:
    start: str = "20:00"
    end: str = "07:00"
    tz: str = "Europe/Zurich"


@dataclass(frozen=True)
class Settings:
    poll: Poll = field(default_factory=Poll)
    mute_a: bool = False
    mute_b: bool = False
    quiet_hours: QuietHours = field(default_factory=QuietHours)
    led_brightness: int = 40
    volume: int = 70

    @property
    def muted(self) -> bool:
        return self.mute_a or self.mute_b

    @classmethod
    def from_json(cls, d: Dict[str, Any] | None) -> "Settings":
        d = d or {}
        p = d.get("poll") or {}
        q = d.get("quiet_hours") or {}
        m = d.get("mute") or {}
        dflt = cls()
        return cls(
            poll=Poll(active_minutes=int(p.get("active_minutes", 1)),
                      active_window_minutes=int(p.get("active_window_minutes", 90)),
                      idle_minutes=int(p.get("idle_minutes", 30))),
            mute_a=bool(m.get("a", False)), mute_b=bool(m.get("b", False)),
            quiet_hours=QuietHours(start=str(q.get("start", dflt.quiet_hours.start)),
                                   end=str(q.get("end", dflt.quiet_hours.end)),
                                   tz=str(q.get("tz", dflt.quiet_hours.tz))),
            led_brightness=int(d.get("led_brightness", dflt.led_brightness)),
            volume=int(d.get("volume", dflt.volume)),
        )

    def to_json(self) -> Dict[str, Any]:
        return {"poll": asdict(self.poll), "mute": {"a": self.mute_a, "b": self.mute_b},
                "quiet_hours": asdict(self.quiet_hours),
                "led_brightness": self.led_brightness, "volume": self.volume}


def _hhmm(s: str) -> dtime:
    h, m = s.split(":")
    return dtime(int(h), int(m))


def in_quiet_hours(q: QuietHours, wall: float) -> bool:
    """Enforced on the device, from the settings' own time zone."""
    tz = timezone.utc
    if ZoneInfo is not None:
        try:
            tz = ZoneInfo(q.tz)
        except Exception:
            pass
    local = datetime.fromtimestamp(wall, tz).time()
    start, end = _hhmm(q.start), _hhmm(q.end)
    if start == end:
        return False
    if start < end:
        return start <= local < end
    return local >= start or local < end
