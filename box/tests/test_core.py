"""The core, driven by events on a fake clock. No threads, no disk."""
from dadbox import core as c
from dadbox.clock import FakeClock
from dadbox.gestures import Button, LockGesture
from dadbox.lights import Cue
from dadbox.settings import QuietHours, Settings
from dadbox.state import Fault, Lights, Link, Power

MID = "01JAYZ3K7QW9E8RVX2M4N6P8TD"


def make(**boot):
    clock = FakeClock(speed=1.0, wall=1_800_000_000.0)   # 2027-01-15 ~ 08:00 UTC: not quiet hours
    core = c.Core(clock)
    defaults = dict(outbox={}, inbox=(), locked=False, settings=Settings())
    defaults.update(boot)
    core.handle(c.Boot(**defaults))
    return clock, core


def press(clock, core, button):
    """A real press: contact down, half a second, fires on a tick."""
    out = core.handle(c.Contact(button, True))
    clock.skip(0.5)
    out += core.handle(c.Tick())
    out += core.handle(c.Contact(button, False))
    return out


def of(actions, kind):
    return [a for a in actions if isinstance(a, kind)]


def test_record_press_powers_the_mic_first_then_captures():
    clock, core = make()
    out = press(clock, core, Button.RECORD)
    kinds = [type(a) for a in out]
    assert kinds.index(c.MicPower) < kinds.index(c.StartCapture)
    assert of(out, c.MicPower)[0].on is True
    assert core.lights(clock.now()) is Lights.RECORDING
    assert core.s.mode is c.Mode.RECORDING


def test_second_press_stops_mic_before_anything_and_got_it_only_after_fsync():
    clock, core = make()
    press(clock, core, Button.RECORD)
    mid = core.s.recording_id
    clock.skip(5)
    out = press(clock, core, Button.RECORD)
    assert isinstance(out[0], c.MicPower) and out[0].on is False
    assert of(out, c.StopCapture)[0].message_id == mid
    assert core.lights(clock.now()) is Lights.IDLE
    assert not of(out, c.Encode)
    out = core.handle(c.CaptureEnded(mid, True))
    assert of(out, c.Encode)[0].message_id == mid
    assert core.s.cue is None                                    # no pulse yet: nothing is on disk
    out = core.handle(c.Queued(mid, 31000, 4200))
    assert core.s.cue is Cue.GOT_IT and core.lights(clock.now()) is Lights.GOT_IT
    assert of(out, c.LinkPlan)[0].wake is True                   # and the link is woken to send it
    assert core.s.outbox == {mid: 31000}


def test_a_forgotten_recording_stops_at_the_cap_and_after_silence():
    clock, core = make()
    press(clock, core, Button.RECORD)
    clock.skip(300)
    out = core.handle(c.Tick())
    assert of(out, c.StopCapture) and core.s.mode is c.Mode.IDLE
    press(clock, core, Button.RECORD)
    core.handle(c.CaptureLevel(core.s.recording_id, 30.0, 20.0))
    out = core.handle(c.Tick())
    assert of(out, c.StopCapture)


def test_a_message_arrives_chimes_and_waits_then_plays_oldest_first():
    clock, core = make()
    out = core.handle(c.Downloaded("01JAYZ3K7QW9E8RVX2M4N6P8TD"))
    assert of(out, c.Chime) and core.lights(clock.now()) is Lights.WAITING
    core.handle(c.Downloaded("01JAYZ3K7QW9E8RVX2M4N6P8TA"))
    out = press(clock, core, Button.PLAY)
    play = of(out, c.Play)[0]
    assert play.message_id == "01JAYZ3K7QW9E8RVX2M4N6P8TA" and play.volume == 70
    assert core.lights(clock.now()) is Lights.PLAYING
    out = core.handle(c.PlaybackEnded("01JAYZ3K7QW9E8RVX2M4N6P8TA"))
    assert of(out, c.MarkPlayed)[0].message_id == "01JAYZ3K7QW9E8RVX2M4N6P8TA"
    assert core.s.inbox == ["01JAYZ3K7QW9E8RVX2M4N6P8TD"] and core.lights(clock.now()) is Lights.WAITING
    assert core.snapshot()["window_open"]                        # playing opened the conversation window


def test_play_with_nothing_new_repeats_the_last_message():
    clock, core = make()
    assert not of(press(clock, core, Button.PLAY), c.Play)         # nothing ever heard: nothing to play
    core.handle(c.Downloaded(MID))
    press(clock, core, Button.PLAY)
    core.handle(c.PlaybackEnded(MID))
    assert core.lights(clock.now()) is Lights.IDLE and core.s.last_played == MID
    out = press(clock, core, Button.PLAY)
    assert of(out, c.Play)[0].message_id == MID and core.s.replaying
    assert core.lights(clock.now()) is Lights.PLAYING
    out = core.handle(c.PlaybackEnded(MID))
    assert not of(out, c.MarkPlayed)                                # a replay is not reported again
    assert core.lights(clock.now()) is Lights.IDLE and core.s.last_played == MID
    core.handle(c.Downloaded("01JAYZ3K7QW9E8RVX2M4N6P8TA"))       # something new wins over the replay
    assert of(press(clock, core, Button.PLAY), c.Play)[0].message_id == "01JAYZ3K7QW9E8RVX2M4N6P8TA"


def test_boot_remembers_the_last_played_message():
    clock, core = make(last_played=MID)
    assert of(press(clock, core, Button.PLAY), c.Play)[0].message_id == MID


def test_quiet_hours_no_chime_but_play_still_works():
    clock, core = make(settings=Settings(quiet_hours=QuietHours("00:00", "23:59", "UTC")))
    out = core.handle(c.Downloaded(MID))
    assert not of(out, c.Chime)
    assert of(out, c.SetLights)[-1].plan.quiet is True
    assert of(press(clock, core, Button.PLAY), c.Play)


def test_travel_lock_kills_the_buttons_and_persists():
    clock, core = make()
    core.handle(c.Downloaded(MID))
    out = core.handle(c.Contact(Button.RECORD, True)) + core.handle(c.Contact(Button.PLAY, True))
    clock.skip(3.0)
    out += core.handle(c.Tick())
    assert of(out, c.PersistLock)[0].locked is True and core.s.cue is Cue.LOCK
    core.handle(c.Contact(Button.RECORD, False)); core.handle(c.Contact(Button.PLAY, False))
    assert not of(press(clock, core, Button.RECORD), c.StartCapture)
    assert not of(press(clock, core, Button.PLAY), c.Play)
    assert core.lights(clock.now()) is Lights.WAITING            # a locked box still shows *waiting*
    clock.skip(2)
    out = core.handle(c.Contact(Button.RECORD, True)) + core.handle(c.Contact(Button.PLAY, True))
    clock.skip(3.0)
    out += core.handle(c.Tick())
    assert of(out, c.PersistLock)[0].locked is False


def lock(clock, core):
    out = core.handle(c.Contact(Button.RECORD, True)) + core.handle(c.Contact(Button.PLAY, True))
    clock.skip(3.0)
    out += core.handle(c.Tick())
    core.handle(c.Contact(Button.RECORD, False)); core.handle(c.Contact(Button.PLAY, False))
    return out


def test_the_travel_lock_saves_power_and_unlocking_checks_in_at_once():
    clock, core = make()                                          # on mains — or a power bank, which looks the same
    core.handle(c.Checkin(True, Settings(), (), doorbell=BELL))
    core.handle(c.DoorbellState(True))
    out = lock(clock, core)
    assert of(out, c.LinkPlan)[-1] == c.LinkPlan(1800, False)     # modem off between check-ins
    assert of(out, c.DoorbellPlan) == [c.DoorbellPlan()]
    core.handle(c.DoorbellState(False))                           # the worker reports it closed
    out = core.handle(c.UploadDone(MID))                          # sent just before locking: no 15 s polling
    assert not of(out, c.LinkPlan) and core.s.checkin_interval_s == 1800
    t = core.telemetry(outbox_bytes=0, outbox_oldest_s=0, storage_pct=0, inbox_on_disk=0)
    assert t["locked"] is True and t["next_checkin_s"] == 1800 and t["doorbell"] is False
    clock.skip(1700)
    core.handle(c.Checkin(True, Settings(), (), doorbell=BELL))
    clock.skip(1500)
    out = lock(clock, core)                                       # unlocked 25 min after the last check-in
    assert any(p.wake for p in of(out, c.LinkPlan)) and core.s.checkin_interval_s == 60
    assert of(out, c.DoorbellPlan) == [c.DoorbellPlan(BELL["url"], BELL["topic"])]
    assert core.ready(clock.now())                                # not "not ready" while it checks in
    core.handle(c.Checkin(False, error="no route"))
    assert not core.ready(clock.now())                            # …but a failed round says so


def test_a_box_that_boots_locked_starts_on_the_slow_cadence():
    clock, core = make(locked=True)
    assert core.s.checkin_interval_s == 1800 and core.s.modem_on is False


def test_mic_and_amp_are_never_on_together():
    clock, core = make(inbox=[MID])
    press(clock, core, Button.PLAY)
    assert not of(press(clock, core, Button.RECORD), c.StartCapture)
    core.handle(c.PlaybackEnded(MID))
    core.handle(c.Downloaded("01JAYZ3K7QW9E8RVX2M4N6P8TA"))
    press(clock, core, Button.RECORD)
    assert not of(press(clock, core, Button.PLAY), c.Play)


def test_link_led_is_time_since_the_last_good_checkin():
    clock, core = make()
    assert core.link(clock.now()) is Link.DOWN
    core.handle(c.Checkin(True, Settings(), ()))
    assert core.link(clock.now()) is Link.OK                     # steady green
    clock.skip(121)
    assert core.link(clock.now()) is Link.DOWN
    core.handle(c.Queued(MID, 10, 1000))
    assert core.link(clock.now()) is Link.DOWN_QUEUED
    core.handle(c.Checkin(False, error="no route"))
    assert core.link(clock.now()) is Link.DOWN_QUEUED


def test_battery_cadence_and_the_conversation_window():
    clock, core = make()
    out = core.handle(c.PowerState(mains=False, battery_pct=60))
    assert of(out, c.LinkPlan)[-1] == c.LinkPlan(1800, False)
    out = core.handle(c.UploadDone(MID))
    assert of(out, c.LinkPlan)[-1] == c.LinkPlan(15, True)       # just used
    clock.skip(5 * 60)
    out = core.handle(c.Tick())
    assert of(out, c.LinkPlan)[-1] == c.LinkPlan(60, True)       # the rest of the window
    clock.skip(85 * 60)
    out = core.handle(c.Tick())
    assert of(out, c.LinkPlan)[-1] == c.LinkPlan(1800, False)
    out = core.handle(c.PowerState(mains=True, battery_pct=60, charging=True))
    assert of(out, c.LinkPlan)[-1] == c.LinkPlan(60, True) and core.power() is Power.CHARGING


def test_low_battery_and_shutdown_are_the_adults_business():
    clock, core = make()
    core.handle(c.PowerState(mains=False, battery_pct=15))
    assert core.power() is Power.LOW and core.lights(clock.now()) is Lights.IDLE
    core.handle(c.PowerState(mains=False, battery_pct=4))
    assert of(core.handle(c.Tick()), c.Shutdown)


def test_resting_after_two_hours_without_interaction():
    clock, core = make()
    core.handle(c.Downloaded(MID))
    assert not core.resting(clock.now())
    clock.skip(2 * 3600)
    assert of(core.handle(c.Tick()), c.SetLights)[-1].plan.resting is True
    press(clock, core, Button.RECORD); press(clock, core, Button.RECORD)  # any press wakes it
    assert not core.resting(clock.now())


def test_boot_recovers_an_interrupted_recording():
    clock, core = make(pending_captures=[MID])
    # the Boot event was handled in make(); redo to inspect its actions
    out = core.handle(c.Boot(outbox={}, inbox=(), locked=False, settings=Settings(), pending_captures=[MID]))
    assert of(out, c.Encode)[0] == c.Encode(MID, recovered=True)
    assert of(out, c.MicPower)[0].on is False


def test_faults_live_on_the_status_leds_never_the_buttons():
    clock, core = make()
    core.handle(c.CaptureEnded(MID, False, "arecord died"))
    assert core.fault() is Fault.CAPTURE and core.lights(clock.now()) is Lights.IDLE
    core.handle(c.Queued(MID, 1, 1000))
    assert core.fault() is Fault.NONE
    core.handle(c.FaultEvent(Fault.MODEM, True))
    assert core.fault() is Fault.MODEM
    core.handle(c.Checkin(True, Settings(), ()))
    assert core.fault() is Fault.NONE


def test_telemetry_has_every_field_in_the_protocol():
    clock, core = make()
    t = core.telemetry(outbox_bytes=0, outbox_oldest_s=0, storage_pct=3, inbox_on_disk=0)
    assert set(t) == {"battery_pct", "charging", "mains", "rssi", "fw", "outbox", "outbox_bytes", "outbox_oldest_s",
                      "storage_pct", "inbox", "uptime_s", "offline_s", "next_checkin_s", "recording", "locked",
                      "house", "fault", "doorbell"}
    assert t["battery_pct"] is None and t["mains"] is True and t["next_checkin_s"] == 60


def test_power_led_says_external_power_present():
    clock, core = make()
    assert core.power() is Power.MAINS                            # steady: power on the USB port
    core.handle(c.PowerState(mains=False))
    assert core.power() is Power.OK                               # off: unplugged
    core.handle(c.PowerState(mains=True, battery_pct=100, charging=False))
    assert core.power() is Power.MAINS                            # full pack on mains: still steady


def test_ctl_commands_answer():
    clock, core = make()
    out = core.handle(c.Command("record", ("start",), 1))
    assert of(out, c.Reply)[0].text.startswith("recording ") and core.s.mode is c.Mode.RECORDING
    out = core.handle(c.Command("record", ("stop",), 2))
    assert "encoding" in of(out, c.Reply)[0].text
    out = core.handle(c.Command("lock", ("on",), 3))
    assert of(out, c.Reply)[0].text == "lock on" and core.s.locked
    out = core.handle(c.Command("state", (), 4))
    assert "lock=on" in of(out, c.Reply)[0].text


# --- the doorbell (ADR 0021) --------------------------------------------------------------------

BELL = {"url": "wss://example.test/realtime/v1/websocket?vsn=1.0.0", "topic": "doorbell:abc"}


def test_the_server_gives_a_doorbell_and_the_box_opens_it_on_mains_only():
    clock, core = make()
    out = core.handle(c.Checkin(True, Settings(), (), doorbell=BELL))
    assert of(out, c.DoorbellPlan) == [c.DoorbellPlan(BELL["url"], BELL["topic"])]
    out = core.handle(c.PowerState(mains=False, battery_pct=80))
    assert of(out, c.DoorbellPlan) == [c.DoorbellPlan()]              # unplugged: closed (battery deferred)
    out = core.handle(c.PowerState(mains=True, battery_pct=80))
    assert of(out, c.DoorbellPlan) == [c.DoorbellPlan(BELL["url"], BELL["topic"])]


def test_the_server_switches_the_doorbell_off_by_leaving_it_out():
    clock, core = make()
    core.handle(c.Checkin(True, Settings(), (), doorbell=BELL))
    out = core.handle(c.Checkin(True, Settings(), ()))
    assert of(out, c.DoorbellPlan) == [c.DoorbellPlan()]
    out = core.handle(c.Checkin(False, error="no route"))               # a failed check-in changes nothing
    assert not of(out, c.DoorbellPlan)


def test_a_join_is_a_knock_and_stretches_the_timer_to_the_backstop():
    clock, core = make()
    core.handle(c.Checkin(True, Settings(), (), doorbell=BELL))
    out = core.handle(c.DoorbellState(True))
    assert any(p.wake for p in of(out, c.LinkPlan))
    assert core.s.checkin_interval_s == 600
    t = core.telemetry(outbox_bytes=0, outbox_oldest_s=0, storage_pct=0, inbox_on_disk=0)
    assert t["doorbell"] is True and t["next_checkin_s"] == 600
    out = core.handle(c.DoorbellState(False))
    assert of(out, c.LinkPlan)[-1].interval_s == 60 and core.s.checkin_interval_s == 60


def test_a_joined_doorbell_on_battery_counts_as_closed():
    clock, core = make()
    core.handle(c.Checkin(True, Settings(), (), doorbell=BELL))
    core.handle(c.DoorbellState(True))
    core.handle(c.PowerState(mains=False, battery_pct=80))
    t = core.telemetry(outbox_bytes=0, outbox_oldest_s=0, storage_pct=0, inbox_on_disk=0)
    assert t["doorbell"] is False and core.s.checkin_interval_s == 1800


def test_rings_are_answered_at_most_every_five_seconds_and_never_dropped():
    clock, core = make()
    out = core.handle(c.Ring())
    assert [p.wake for p in of(out, c.LinkPlan)] == [True]
    clock.skip(2)
    out = core.handle(c.Ring())                                         # a second message, 2 s later
    assert not any(p.wake for p in of(out, c.LinkPlan))
    out = core.handle(c.Ring())                                         # and a third: still one round
    clock.skip(1)
    assert not any(p.wake for p in of(core.handle(c.Tick()), c.LinkPlan))
    clock.skip(2.1)
    assert [p.wake for p in of(core.handle(c.Tick()), c.LinkPlan)] == [True]
    assert not any(p.wake for p in of(core.handle(c.Tick()), c.LinkPlan))


def test_the_doorbell_address_survives_a_reboot():
    clock, core = make(doorbell=BELL)
    assert core.doorbell_plan() == c.DoorbellPlan(BELL["url"], BELL["topic"])


def test_a_burst_of_arrivals_chimes_once():
    clock, core = make()
    chimes = []
    for i, mid in enumerate(["01JAYZ3K7QW9E8RVX2M4N6P8T" + c for c in "ABCDEFG"]):
        chimes += of(core.handle(c.Downloaded(mid)), c.Chime)
    assert len(chimes) == 1 and len(core.s.inbox) == 7
    clock.skip(31)
    assert of(core.handle(c.Downloaded("01JAYZ3K7QW9E8RVX2M4N6P8TH")), c.Chime)


def test_power_on_rainbow_until_first_ready():
    clock, core = make()
    assert core.booting(clock.now())
    out = core.handle(c.Checkin(True, Settings(), ()))
    assert not core.booting(clock.now())
    assert of(out, c.SetLights)[-1].plan.booting is False and of(out, c.SetLights)[-1].plan.ready
    core.s.last_checkin_ok_at = None
    assert not core.booting(clock.now())                         # once over, never back


def test_power_on_rainbow_gives_way_to_not_ready_after_three_minutes():
    clock, core = make()
    clock.skip(179)
    core.handle(c.Tick())
    assert core.booting(clock.now())
    clock.skip(2)
    out = core.handle(c.Tick())
    assert of(out, c.SetLights)[-1].plan.booting is False         # Record blinks blue: not ready


def test_power_on_rainbow_ends_when_the_child_records_or_a_message_waits():
    clock, core = make()
    press(clock, core, Button.RECORD)
    assert not core.booting(clock.now())
    clock, core = make(inbox=(MID,))
    assert not core.booting(clock.now())                         # the green pulse matters more


def test_record_tones_bracket_the_mic_and_never_overlap_it():
    clock, core = make()
    out = press(clock, core, Button.RECORD)
    kinds = [type(a).__name__ for a in out if isinstance(a, (c.Chime, c.MicPower))]
    assert kinds == ["Chime", "MicPower"]                         # the start tone first…
    start = of(out, c.Chime)[0]
    assert start.kind == "record_start" and start.wait            # …and over before the mic gets power
    assert of(out, c.MicPower)[0].on
    out = press(clock, core, Button.RECORD)
    seq = [a for a in out if isinstance(a, (c.Chime, c.MicPower))]
    assert isinstance(seq[0], c.MicPower) and not seq[0].on       # mic off first…
    assert isinstance(seq[1], c.Chime) and seq[1].kind == "record_end" and not seq[1].wait   # …then "done"


def test_record_tones_are_half_volume_in_quiet_hours():
    clock, core = make(settings=Settings(volume=80, quiet_hours=QuietHours("00:00", "23:59", "UTC")))
    out = press(clock, core, Button.RECORD)
    assert of(out, c.Chime)[0].volume == 40


def test_the_message_chime_sounds_once_more_after_10_s():
    clock, core = make()
    out = core.handle(c.Downloaded(MID))
    assert len(of(out, c.Chime)) == 1
    clock.skip(9.9)
    assert not of(core.handle(c.Tick()), c.Chime)
    clock.skip(0.2)
    assert len(of(core.handle(c.Tick()), c.Chime)) == 1
    clock.skip(30)
    assert not of(core.handle(c.Tick()), c.Chime)             # once, never a nag


def test_no_repeat_once_the_child_pressed_or_the_message_was_heard():
    clock, core = make()
    core.handle(c.Downloaded(MID))
    out = press(clock, core, Button.PLAY)
    clock.skip(11)
    assert not [a for a in core.handle(c.Tick()) if isinstance(a, c.Chime) and a.kind == "message"]


def test_lock_and_unlock_sound_a_tone_and_a_press_while_locked_flashes():
    clock, core = make()
    def hold_both():
        out = core.handle(c.Contact(Button.RECORD, True)) + core.handle(c.Contact(Button.PLAY, True))
        clock.skip(3.0)
        out += core.handle(c.Tick())
        core.handle(c.Contact(Button.RECORD, False)); core.handle(c.Contact(Button.PLAY, False))
        return out
    out = hold_both()
    assert [a.kind for a in of(out, c.Chime)] == ["lock_on"] and core.s.cue is Cue.LOCK
    clock.skip(2)
    out = press(clock, core, Button.RECORD)
    assert core.s.cue is Cue.LOCKED_PRESS and not of(out, c.Chime) and not of(out, c.StartCapture)
    clock.skip(2)
    out = hold_both()
    assert [a.kind for a in of(out, c.Chime)] == ["lock_off"] and core.s.cue is Cue.UNLOCK


def test_locking_mid_recording_gives_the_lock_tone_not_the_done_tone():
    clock, core = make()
    press(clock, core, Button.RECORD)
    out = core.handle(c.Contact(Button.RECORD, True)) + core.handle(c.Contact(Button.PLAY, True))
    clock.skip(3.0)
    out += core.handle(c.Tick())
    assert [a.kind for a in of(out, c.Chime)] == ["lock_on"]
    assert of(out, c.MicPower) and not of(out, c.MicPower)[0].on
