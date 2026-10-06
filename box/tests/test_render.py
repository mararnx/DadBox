import itertools

from dadbox.lights import (Cue, LightsPlan, render, ready_colour, QUIET_CAP, READY_DRIFT_S, READY_LEVEL)
from dadbox.state import Lights


def test_record_red_is_only_ever_on_or_off():
    for lights, cue, bright, resting, quiet, locked, ready, booting in itertools.product(
            Lights, [None, Cue.GOT_IT, Cue.LOCK], [0, 37, 100], [False, True], [False, True], [False, True],
            [False, True], [False, True]):
        plan = LightsPlan(lights=lights, cue=cue, cue_at=0.0, brightness=bright, resting=resting, quiet=quiet,
                          locked=locked, ready=ready, booting=booting)
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
    for ready in (False, True):
        for t in [0.0, 0.7, 1.9]:
            f = render(LightsPlan(lights=Lights.PLAYING, brightness=100, ready=ready), t)
            assert f.play == (0.0, 1.0, 0.0) and f.record == (0.0, 0.0, 0.0)    # Record is ignored while playing


def test_ready_drifts_slowly_through_blue_and_green_on_record():
    from dadbox.lights import READY_GREEN
    for lights in (Lights.IDLE, Lights.WAITING):
        frames = [render(LightsPlan(lights=lights, brightness=100, ready=True), i * READY_DRIFT_S / 40) for i in range(41)]
        for f in frames:
            r, g, b = f.record
            assert r == 0.0 and 0 < g + b <= READY_LEVEL + 1e-9               # dim, never off, never red
        assert frames[0].record == (0.0, 0.0, READY_LEVEL)                    # blue
    for lights in (Lights.IDLE,):
        half = READY_DRIFT_S / 2
        f = render(LightsPlan(lights=lights, brightness=100, ready=True), half).record
        assert abs(f[1] - READY_LEVEL * READY_GREEN) < 1e-9 and f[2] < 1e-9       # green, as bright as blue
        g, b = render(LightsPlan(lights=lights, brightness=100, ready=True), half / 2).record[1:]
        assert 0 < g < b                                                      # cyan between
    assert ready_colour(0.0) == ready_colour(READY_DRIFT_S)


def test_ready_drift_has_no_big_steps():
    prev = ready_colour(0.0)
    for i in range(1, 601):                                                   # 30 Hz over the 20 s round
        c = ready_colour(i * READY_DRIFT_S / 600)
        assert max(abs(a - b) for a, b in zip(c, prev)) < 0.02
        prev = c
    for t in [0, 0.75, 1.5]:
        assert render(LightsPlan(lights=Lights.IDLE, brightness=100), t).play == (0.0, 0.0, 0.0)   # replay shows nothing


def test_not_ready_blinks_blue_on_record():
    plan = LightsPlan(lights=Lights.IDLE, brightness=100, ready=False)
    on = (0.0, 0.0, READY_LEVEL)
    assert [render(plan, t).record for t in [0.5, 1.5, 2.5, 3.5]] == [on, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), on]


def test_locked_record_is_dark():
    for ready in (False, True):
        for t in [0.5, 1.5]:
            assert render(LightsPlan(lights=Lights.IDLE, brightness=100, ready=ready, locked=True), t).record == (0.0, 0.0, 0.0)


def test_quiet_hours_cap_the_glow():
    loud = render(LightsPlan(lights=Lights.PLAYING, brightness=100), 0.0).play[1]
    quiet = render(LightsPlan(lights=Lights.PLAYING, brightness=100, quiet=True), 0.0).play[1]
    assert quiet == loud * QUIET_CAP


def test_got_it_is_one_green_pulse_on_record():
    plan = LightsPlan(lights=Lights.IDLE, cue=Cue.GOT_IT, cue_at=10.0, brightness=100, ready=True)
    assert render(plan, 10.3).record == (0.0, render(plan, 10.3).record[1], 0.0) and render(plan, 10.3).record[1] > 0.9
    assert render(plan, 10.7).record == render(LightsPlan(brightness=100, ready=True), 10.7).record   # back to ready


def test_lock_blinks_play_white_twice():
    plan = LightsPlan(cue=Cue.LOCK, cue_at=0.0, brightness=100, locked=True)
    from dadbox.lights import BALANCE
    assert render(plan, 0.1).play == BALANCE and render(plan, 0.3).play == (0.0, 0.0, 0.0)   # white, balanced
    assert render(plan, 0.1).record == (0.0, 0.0, 0.0)


def test_powering_on_runs_play_through_the_colours_and_record_is_dark():
    plan = LightsPlan(booting=True, brightness=100)
    frames = [render(plan, i * 0.1) for i in range(30)]
    assert all(f.record == (0.0, 0.0, 0.0) for f in frames)
    for f in frames:
        assert max(f.play) == 1.0                                # every hue at full strength
    hues = {tuple(round(x) for x in f.play) for f in frames}
    assert {(1, 0, 0), (0, 1, 0), (0, 0, 1)} <= hues


def test_mixes_are_balanced_for_the_buttons_pure_colours_are_not():
    from dadbox.lights import BALANCE, balanced
    assert balanced((1.0, 0.0, 0.0)) == (1.0, 0.0, 0.0)
    assert balanced((0.0, 1.0, 0.0)) == (0.0, 1.0, 0.0)
    assert balanced((1.0, 1.0, 1.0)) == BALANCE                  # white as judged on the bench
    r, g, b = balanced((0.0, 1.0, 1.0))                          # cyan: green held back for blue
    assert b == 1.0 and g == BALANCE[1]


def test_powering_on_gives_way_to_what_the_child_does():
    assert render(LightsPlan(lights=Lights.RECORDING, booting=True), 1.0).record[0] == 1.0
    assert render(LightsPlan(lights=Lights.PLAYING, booting=True, brightness=100), 1.0).play == (0.0, 1.0, 0.0)
