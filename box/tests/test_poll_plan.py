from dadbox.state import JUST_USED_POLL_S, JUST_USED_S, Poll, poll_plan

POLL = Poll()


def test_mains_is_always_fast_and_modem_on():
    assert poll_plan(POLL, mains=True, since_activity_s=None) == (60, True)
    assert poll_plan(POLL, mains=True, since_activity_s=10 * 3600) == (60, True)


def test_battery_idle_is_slow_and_modem_off():
    assert poll_plan(POLL, mains=False, since_activity_s=None) == (1800, False)


def test_battery_conversation_window():
    assert poll_plan(POLL, mains=False, since_activity_s=JUST_USED_S) == (60, True)
    assert poll_plan(POLL, mains=False, since_activity_s=90 * 60 - 1) == (60, True)
    assert poll_plan(POLL, mains=False, since_activity_s=90 * 60) == (1800, False)


def test_settings_from_server_are_honoured():
    poll = Poll(active_minutes=2, active_window_minutes=10, idle_minutes=60)
    assert poll_plan(poll, mains=False, since_activity_s=6 * 60) == (120, True)
    assert poll_plan(poll, mains=False, since_activity_s=11 * 60) == (3600, False)


def test_a_joined_doorbell_stretches_the_timer_to_the_backstop():
    assert poll_plan(POLL, mains=True, since_activity_s=None, doorbell=True) == (600, True)
    assert poll_plan(Poll(backstop_minutes=5), mains=True, since_activity_s=JUST_USED_S, doorbell=True) == (300, True)


def test_the_doorbell_is_ignored_on_battery():
    assert poll_plan(POLL, mains=False, since_activity_s=JUST_USED_S, doorbell=True) == (60, True)
    assert poll_plan(POLL, mains=False, since_activity_s=None, doorbell=True) == (1800, False)


def test_just_used_polls_every_15_s_whatever_the_power_or_doorbell():
    for mains, doorbell in ((True, True), (True, False), (False, False)):
        assert poll_plan(POLL, mains=mains, since_activity_s=0, doorbell=doorbell) == (JUST_USED_POLL_S, True)
        assert poll_plan(POLL, mains=mains, since_activity_s=JUST_USED_S - 1, doorbell=doorbell) == (15, True)
    assert poll_plan(POLL, mains=True, since_activity_s=JUST_USED_S) == (60, True)
    assert poll_plan(POLL, mains=True, since_activity_s=JUST_USED_S, doorbell=True) == (600, True)
