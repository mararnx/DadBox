from datetime import datetime
from zoneinfo import ZoneInfo

from dadbox.settings import QuietHours, Settings, in_quiet_hours


def _wall(hhmm, tz="Europe/Zurich"):
    h, m = map(int, hhmm.split(":"))
    return datetime(2026, 9, 22, h, m, tzinfo=ZoneInfo(tz)).timestamp()


def test_quiet_hours_wrap_midnight_in_the_settings_time_zone():
    q = QuietHours("20:00", "07:00", "Europe/Zurich")
    assert in_quiet_hours(q, _wall("21:00"))
    assert in_quiet_hours(q, _wall("03:00"))
    assert not in_quiet_hours(q, _wall("12:00"))
    assert not in_quiet_hours(q, _wall("07:00"))
    assert in_quiet_hours(q, _wall("19:59:59"[:5]))is False
    assert in_quiet_hours(QuietHours("13:00", "14:00", "Europe/Zurich"), _wall("13:30"))
    assert not in_quiet_hours(QuietHours("13:00", "13:00", "Europe/Zurich"), _wall("13:00"))


def test_settings_parse_the_servers_shape_and_survive_junk():
    s = Settings.from_json({"poll": {"idle_minutes": 5}, "mute": {"a": True}, "volume": 30})
    assert s.poll.idle_minutes == 5 and s.poll.active_minutes == 1 and s.volume == 30
    assert "mute" not in s.to_json()                              # ignored from an older server (ADR 0020)
    assert Settings.from_json(None) == Settings()
    assert Settings.from_json(s.to_json()) == s
