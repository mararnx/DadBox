import itertools

from dadbox.lights import (Cue, LightsPlan, StatusPlan, render, render_status, QUIET_CAP)
from dadbox.state import Fault, Lights, Link, Power


def test_record_red_is_only_ever_on_or_off():
    for lights, cue, bright, resting, quiet in itertools.product(
            Lights, [None, Cue.GOT_IT, Cue.LOCK], [0, 37, 100], [False, True], [False, True]):
        plan = LightsPlan(lights=lights, cue=cue, cue_at=0.0, brightness=bright, resting=resting, quiet=quiet)
        for t in [i * 0.037 for i in range(120)]:
            red = render(plan, t).record[0]
            assert red in (0.0, 1.0)
            assert red == (1.0 if lights is Lights.RECORDING else 0.0)


def test_recording_ignores_brightness_and_quiet_hours():
    f = render(LightsPlan(lights=Lights.RECORDING, brightness=5, quiet=True), 1.0)
    assert f.record == (1.0, 0.0, 0.0) and f.play == (0.0, 0.0, 0.0)


def test_waiting_breathes_and_resting_is_dim_not_off():
    plan = LightsPlan(lights=Lights.WAITING, brightness=100)
    levels = {round(render(plan, t).play[0], 2) for t in [0, 1, 2, 3]}
    assert len(levels) > 1
    resting = render(LightsPlan(lights=Lights.WAITING, brightness=100, resting=True), 2.0).play[0]
    assert 0 < resting < 0.3


def test_quiet_hours_cap_the_glow():
    loud = render(LightsPlan(lights=Lights.PLAYING, brightness=100), 0.0).play[0]
    quiet = render(LightsPlan(lights=Lights.PLAYING, brightness=100, quiet=True), 0.0).play[0]
    assert quiet == loud * QUIET_CAP


def test_got_it_is_one_green_pulse_on_record():
    plan = LightsPlan(lights=Lights.IDLE, cue=Cue.GOT_IT, cue_at=10.0, brightness=100)
    assert render(plan, 10.3).record[1] > 0.9
    assert render(plan, 10.7).record == (0.0, 0.0, 0.0)


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
