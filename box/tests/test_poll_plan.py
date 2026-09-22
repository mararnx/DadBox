from dadbox.state import Poll, poll_plan

POLL = Poll()


def test_mains_is_always_fast_and_modem_on():
    assert poll_plan(POLL, mains=True, since_activity_s=None) == (60, True)
    assert poll_plan(POLL, mains=True, since_activity_s=10 * 3600) == (60, True)


def test_battery_idle_is_slow_and_modem_off():
    assert poll_plan(POLL, mains=False, since_activity_s=None) == (1800, False)


def test_battery_conversation_window():
    assert poll_plan(POLL, mains=False, since_activity_s=0) == (60, True)
    assert poll_plan(POLL, mains=False, since_activity_s=90 * 60 - 1) == (60, True)
    assert poll_plan(POLL, mains=False, since_activity_s=90 * 60) == (1800, False)


def test_settings_from_server_are_honoured():
    poll = Poll(active_minutes=2, active_window_minutes=10, idle_minutes=60)
    assert poll_plan(poll, mains=False, since_activity_s=5 * 60) == (120, True)
    assert poll_plan(poll, mains=False, since_activity_s=11 * 60) == (3600, False)


def test_a_joined_doorbell_stretches_the_timer_to_the_backstop():
    assert poll_plan(POLL, mains=True, since_activity_s=None, doorbell=True) == (600, True)
    assert poll_plan(Poll(backstop_minutes=5), mains=True, since_activity_s=0, doorbell=True) == (300, True)


def test_the_doorbell_is_ignored_on_battery():
    assert poll_plan(POLL, mains=False, since_activity_s=0, doorbell=True) == (60, True)
    assert poll_plan(POLL, mains=False, since_activity_s=None, doorbell=True) == (1800, False)
