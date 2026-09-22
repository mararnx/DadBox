from dadbox.gestures import Button, Gestures, LockGesture, Press

R, P = Button.RECORD, Button.PLAY


def test_a_tap_is_a_bag_not_a_finger():
    g = Gestures()
    assert g.contact(R, True, 0.0) == []
    assert g.tick(0.3) == []
    assert g.contact(R, False, 0.4) == []
    assert g.tick(1.0) == []


def test_a_press_fires_while_still_held_and_release_does_nothing():
    g = Gestures()
    g.contact(R, True, 0.0)
    assert g.tick(0.49) == []
    assert g.tick(0.5) == [Press(R)]
    assert g.tick(2.0) == []
    assert g.contact(R, False, 2.5) == []


def test_both_held_three_seconds_is_the_travel_lock():
    g = Gestures()
    g.contact(R, True, 0.0)
    g.contact(P, True, 0.1)
    assert g.tick(0.6) == []                 # no single presses once a pair is down
    assert g.tick(3.05) == []
    assert g.tick(3.1) == [LockGesture()]
    assert g.tick(9.0) == []                 # fires once
    g.contact(R, False, 9.1); g.contact(P, False, 9.2)
    g.contact(R, True, 10.0)
    assert g.tick(10.5) == [Press(R)]        # and the state is clean afterwards


def test_a_fumbled_pair_fires_nothing_at_all():
    g = Gestures()
    g.contact(R, True, 0.0)
    g.contact(P, True, 0.2)
    assert g.contact(P, False, 1.0) == []
    assert g.tick(5.0) == []                 # the still-held record button is not a press
    assert g.contact(R, False, 5.1) == []


def test_a_second_button_after_a_fired_press_is_its_own_press():
    g = Gestures()
    g.contact(R, True, 0.0)
    assert g.tick(0.5) == [Press(R)]
    g.contact(P, True, 0.6)
    assert g.tick(1.1) == [Press(P)]
    assert g.tick(4.0) == []                 # not a lock: record had already fired
