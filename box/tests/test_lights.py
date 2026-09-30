from dadbox.state import Lights, lights_state, press_counts, should_stop_recording


def test_priority_order():
    assert lights_state(recording=True, playing=True, got_it_pulse=True, inbox=3) is Lights.RECORDING
    assert lights_state(recording=False, playing=True, got_it_pulse=True, inbox=3) is Lights.PLAYING
    assert lights_state(recording=False, playing=False, got_it_pulse=True, inbox=3) is Lights.GOT_IT
    assert lights_state(recording=False, playing=False, got_it_pulse=False, inbox=3) is Lights.WAITING
    assert lights_state(recording=False, playing=False, got_it_pulse=False, inbox=0) is Lights.IDLE


def test_the_states_are_the_childs():
    # Not-ready (blue blink on Record) is an overlay of LightsPlan.ready, not a state (ADR 0024).
    assert {s.name for s in Lights} == {"RECORDING", "PLAYING", "GOT_IT", "WAITING", "IDLE"}


def test_a_bag_is_not_a_finger():
    assert not press_counts(0.2)
    assert press_counts(0.5)


def test_forgotten_recording_is_bounded():
    assert not should_stop_recording(elapsed_s=120, silence_s=5)
    assert should_stop_recording(elapsed_s=300, silence_s=0)
    assert should_stop_recording(elapsed_s=40, silence_s=20)
