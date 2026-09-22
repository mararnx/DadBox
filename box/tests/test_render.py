import itertools

from dadbox.lights import (Cue, LightsPlan, StatusPlan, render, render_status, QUIET_CAP)
from dadbox.state import Fault, Lights, Link, Power


def test_record_red_is_only_ever_on_or_off():
    for lights, cue, bright, resting, quiet, locked in itertools.product(
            Lights, [None, Cue.GOT_IT, Cue.LOCK], [0, 37, 100], [False, True], [False, True], [False, True]):
        plan = LightsPlan(lights=lights, cue=cue, cue_at=0.0, brightness=bright, resting=resting, quiet=quiet, locked=locked)
        for t in [i * 0.037 for i in range(120)]:
            red = render(plan, t).record[0]
            assert red in (0.0, 1.0)
            assert red == (1.0 if lights is Lights.RECORDING else 0.0)


def test_recording_ignores_brightness_and_quiet_hours():
    f = render(LightsPlan(lights=Lights.RECORDING, brightness=5, quiet=True), 1.0)
    assert f.record == (1.0, 0.0, 0.0) and f.play == (0.0, 0.0, 0.0)


def test_waiting_pulses_green_and_resting_is_dim_not_off():
    plan = LightsPlan(lights=Lights.WAITING, brightness=100)
    levels = {round(render(plan, t).play[1], 2) for t in [0, 1, 2, 3]}
    assert len(levels) > 1
    assert all(render(plan, t).play[0] == 0 and render(plan, t).play[2] == 0 for t in [0, 1, 2, 3])   # green only
    resting = render(LightsPlan(lights=Lights.WAITING, brightness=100, resting=True), 2.0).play[1]
    assert 0 < resting < 0.3


def test_playing_is_steady_green_and_record_is_dark():
    for t in [0.0, 0.7, 1.9]:
        f = render(LightsPlan(lights=Lights.PLAYING, brightness=100), t)
        assert f.play == (0.0, 1.0, 0.0) and f.record == (0.0, 0.0, 0.0)


def test_record_pulses_dimly_when_ready_and_not_when_locked():
    plan = LightsPlan(lights=Lights.IDLE, brightness=100)
    levels = {round(render(plan, t).record[2], 3) for t in [0, 0.75, 1.5, 2.25]}
    assert len(levels) > 1 and max(levels) <= 0.25 and min(levels) > 0      # dim, pulsing, never off
    assert all(render(plan, t).record[0] == 0.0 for t in [0, 0.75, 1.5])    # and never any red
    assert render(LightsPlan(lights=Lights.WAITING, brightness=100), 0.75).record[2] > 0   # also while a message waits
    assert render(LightsPlan(lights=Lights.IDLE, brightness=100, locked=True), 0.75).record == (0.0, 0.0, 0.0)


def test_quiet_hours_cap_the_glow():
    loud = render(LightsPlan(lights=Lights.PLAYING, brightness=100), 0.0).play[1]
    quiet = render(LightsPlan(lights=Lights.PLAYING, brightness=100, quiet=True), 0.0).play[1]
    assert quiet == loud * QUIET_CAP


def test_got_it_is_one_green_pulse_on_record():
    plan = LightsPlan(lights=Lights.IDLE, cue=Cue.GOT_IT, cue_at=10.0, brightness=100)
    assert render(plan, 10.3).record[1] > 0.9
    after = render(plan, 10.7).record
    assert after[1] < 0.1 and after[0] == 0.0                     # back to the dim ready pulse


def test_lock_blinks_both_twice():
    plan = LightsPlan(cue=Cue.LOCK, cue_at=0.0, brightness=100)
    on = [t for t in [i * 0.05 for i in range(30)] if render(plan, t).play[1] > 0]
    assert on and render(plan, 0.1).record[1] > 0 and render(plan, 0.3).play == (0.0, 0.0, 0.0)


def test_status_patterns():
    assert render_status(StatusPlan(link=Link.OK), 1.0) == (True, False)       # LINK steady green when fine
    assert render_status(StatusPlan(link=Link.DOWN), 1.0) == (False, False)
    blinks = sum(render_status(StatusPlan(link=Link.DOWN_QUEUED), t)[0] for t in [i * 0.01 for i in range(300)])
    assert 8 <= blinks <= 12                              # two 50 ms blinks in 3 s at 10 ms steps
    assert render_status(StatusPlan(power=Power.CHARGING), 2.0)[1] is True
    assert render_status(StatusPlan(power=Power.MAINS), 2.0)[1] is True
    assert render_status(StatusPlan(power=Power.OK), 2.0)[1] is False
    a, b = render_status(StatusPlan(fault=Fault.STORAGE), 0.1), render_status(StatusPlan(fault=Fault.STORAGE), 0.6)
    assert a == (True, False) and b == (False, True)
