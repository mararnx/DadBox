"""The whole box on fake hardware, at 40× — the simulator, headless.

Record with the mouse-shaped fake buttons, watch the message land on the
server, answer as the parent, see the play button glow, play it, and see
`played_at` on the server. Everything the round trip needs, no hardware.
"""
import platform
import time

import pytest

from dadbox import core as c
from dadbox.clock import FakeClock
from dadbox.gestures import Button
from dadbox.hal import Hardware
from dadbox.link import Client
from dadbox.service import Service
from dadbox.sim.audio import SimAudio
from dadbox.sim.hal import (FakeAmpGate, FakeButtonLights, FakeButtons, FakeMicGate, FakeModem, FakePower)
from dadbox.sim.parent import Parent
from dadbox.sim.server import FakeServer
from dadbox.store import Store

KEY = bytes(range(32))
# 40x on the Mac; the Pi Zero cannot keep a 40x clock honest while running the rest of the suite.
E2E_SPEED = 10.0 if platform.machine() in ("aarch64", "armv7l") else 40.0


def until(cond, timeout=10.0, what="condition"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return
        time.sleep(0.02)
    pytest.fail(f"timed out waiting for {what}")


@pytest.fixture
def box(tmp_path):
    clock = FakeClock(speed=E2E_SPEED, wall=1_800_000_000.0)
    server = FakeServer(clock)
    store = Store(tmp_path)
    store.put_key(1, KEY)
    hw = Hardware(buttons=FakeButtons(), lights=FakeButtonLights(), mic=FakeMicGate(),
                  amp=FakeAmpGate(), modem=FakeModem(), power=FakePower(), audio=SimAudio(clock))
    svc = Service(hw=hw, store=store, clock=clock, client=Client(server.transport("box")),
                  doorbell_connect=lambda url: server.doorbell_connect(url, hw.modem.is_up))
    svc.doorbell.reply_timeout_s, svc.doorbell.heartbeat_s = 0.3, 0.2    # real seconds; the box runs at 40x
    svc.doorbell.backoff_min_s = 0.2
    svc.start()
    yield svc, hw, server, clock, store
    svc.stop()


def hold(svc, hw, button, seconds=0.7):
    hw.buttons.press(button, True)
    svc.clock.sleep(seconds)
    hw.buttons.press(button, False)


def test_round_trip(box):
    svc, hw, server, clock, store = box
    until(lambda: server.last_checkin_at is not None, what="first check-in")

    # Child records: the mic pin goes up with the press and down with the second press.
    hold(svc, hw, Button.RECORD)
    until(lambda: hw.mic.is_on(), what="mic on")
    assert svc.core.snapshot()["lights"] == "RECORDING"
    clock.sleep(6.0)
    hold(svc, hw, Button.RECORD)
    until(lambda: not hw.mic.is_on(), what="mic off")
    until(lambda: any(m["from"] == "box" and m["state"] == "uploaded" for m in server.messages.values()),
          what="upload complete")
    assert store.outbox_ids() == [] and store.pending_captures() == []
    assert hw.mic.transitions == [True, False]
    sent = next(m for m in server.messages.values() if m["from"] == "box")
    assert 1000 <= sent["duration_ms"] <= 7000 and sent["codec"] == 2

    # The parent hears it and answers.
    parent = Parent(server, KEY)
    assert parent.audio(sent["id"])[:4] in (b"OggS", b"RIFF")
    mid = parent.send(8.0)
    until(lambda: svc.core.snapshot()["lights"] == "WAITING", what="play button glowing")
    assert server.messages[mid]["state"] == "delivered"

    # Child plays it: amp on around playback only, played reported, inbox emptied.
    hold(svc, hw, Button.PLAY)
    until(lambda: svc.core.snapshot()["lights"] == "PLAYING" and hw.amp.on, what="playing with the amp on")
    until(lambda: server.messages[mid]["state"] == "played", timeout=20, what="played on the server")
    until(lambda: svc.core.snapshot()["lights"] == "IDLE", what="idle again")
    assert not hw.amp.on and store.inbox_unheard() == [] and store.inbox_count() == 1   # kept for replay

    # Nothing new: Play repeats the last message; the server is not told twice.
    played_at = server.messages[mid]["played_at"]
    hold(svc, hw, Button.PLAY)
    until(lambda: svc.core.snapshot()["replaying"], what="replaying")
    until(lambda: svc.core.snapshot()["lights"] == "IDLE", timeout=20, what="replay done")
    assert server.messages[mid]["played_at"] == played_at
    assert server.telemetry["fw"] and server.telemetry["locked"] is False


def test_offline_recording_is_kept_and_sent_when_the_link_returns(box):
    svc, hw, server, clock, store = box
    until(lambda: server.last_checkin_at is not None, what="first check-in")
    hw.modem.coverage = False
    hold(svc, hw, Button.RECORD); clock.sleep(4.0); hold(svc, hw, Button.RECORD)
    until(lambda: store.outbox_ids() != [], what="queued on disk")
    until(lambda: svc.core.snapshot()["link"] == "DOWN_QUEUED", timeout=15, what="LINK double-blink")
    assert not any(m["from"] == "box" for m in server.messages.values())
    hw.modem.coverage = True
    until(lambda: any(m["from"] == "box" and m["state"] == "uploaded" for m in server.messages.values()),
          timeout=20, what="upload after the link returned")
    assert store.outbox_ids() == []
    assert svc.core.snapshot()["link"] == "OK"                      # LINK steady green again


def test_a_short_recording_is_discarded_and_silence_stops_a_forgotten_one(box):
    svc, hw, server, clock, store = box
    svc.command("record", ("start",)); clock.sleep(0.4); svc.command("record", ("stop",))   # ~0.4 s of speech
    until(lambda: any("discarded" in line for _, _, line in svc.log_lines), what="discard")
    assert store.outbox_ids() == []
    hw.audio.speaking = False
    hold(svc, hw, Button.RECORD)
    until(lambda: hw.mic.is_on(), what="mic on")
    until(lambda: not hw.mic.is_on(), timeout=10, what="silence auto-stop")
    assert any("stopped by silence" in line for _, _, line in svc.log_lines)


def test_travel_lock_and_ctl(box):
    svc, hw, server, clock, store = box
    hw.buttons.press(Button.RECORD, True); hw.buttons.press(Button.PLAY, True)
    clock.sleep(3.5)
    hw.buttons.press(Button.RECORD, False); hw.buttons.press(Button.PLAY, False)
    until(lambda: store.locked(), what="lock persisted")
    assert "lock=on" in svc.command("state")
    hold(svc, hw, Button.RECORD)
    clock.sleep(1.0)
    assert not hw.mic.is_on()
    assert svc.command("lock", ("off",)) == "lock off"
    assert svc.command("record", ("start",)).startswith("recording ")
    until(lambda: hw.mic.is_on(), what="mic on via ctl")
    assert "encoding" in svc.command("record", ("stop",))
    assert svc.command("sim", ("link", "down")).startswith("link down")
    assert svc.command("checkin").startswith("check-in failed")
    assert svc.command("sim", ("link", "up")) == "link up"
    assert svc.command("checkin").startswith("check-in ok")


def test_a_power_cut_mid_recording_is_recovered_at_boot(tmp_path):
    """What ADR 0019 asks for: the capture is on disk while the child talks; a boot finishes the job."""
    from dadbox.dsp import synthetic_voice
    clock = FakeClock(speed=E2E_SPEED, wall=1_800_000_000.0)
    server = FakeServer(clock)
    store = Store(tmp_path)
    store.put_key(1, KEY)
    mid = "01JAYZ3K7QW9E8RVX2M4N6P8TD"
    store.begin_capture(mid, {"created_at": "2026-09-22T10:00:00Z", "time_ok": False}).write_bytes(synthetic_voice(3.0))
    hw = Hardware(buttons=FakeButtons(), lights=FakeButtonLights(), mic=FakeMicGate(),
                  amp=FakeAmpGate(), modem=FakeModem(), power=FakePower(), audio=SimAudio(clock))
    svc = Service(hw=hw, store=store, clock=clock, client=Client(server.transport("box")))
    svc.start()
    try:
        until(lambda: mid in server.messages and server.messages[mid]["state"] == "uploaded", what="recovered upload")
        assert server.messages[mid]["time_ok"] is False and store.pending_captures() == []
        assert not hw.mic.is_on() and hw.mic.transitions == []      # recovery never powers the mic
    finally:
        svc.stop()


def test_the_doorbell_delivers_a_reply_in_seconds_at_real_speed(tmp_path):
    """At 1x a poll every minute would take up to 60 s; only a ring explains a second."""
    clock = FakeClock(speed=1.0, wall=1_800_000_000.0)
    server = FakeServer(clock)
    store = Store(tmp_path)
    store.put_key(1, KEY)
    hw = Hardware(buttons=FakeButtons(), lights=FakeButtonLights(), mic=FakeMicGate(),
                  amp=FakeAmpGate(), modem=FakeModem(), power=FakePower(), audio=SimAudio(clock))
    svc = Service(hw=hw, store=store, clock=clock, client=Client(server.transport("box")),
                  doorbell_connect=lambda url: server.doorbell_connect(url, hw.modem.is_up))
    svc.doorbell.reply_timeout_s, svc.doorbell.heartbeat_s, svc.doorbell.backoff_min_s = 0.3, 0.2, 0.2
    svc.start()
    try:
        until(lambda: svc.doorbell.joined, what="doorbell joined")
        until(lambda: (server.telemetry or {}).get("doorbell") is True, what="a check-in saying so")
        assert server.telemetry["next_checkin_s"] == 600               # the timer is only the backstop now
        assert store.doorbell_json()["topic"] == server.doorbell_topic

        mid = Parent(server, KEY).send(2.0, audio=b"RIFF" + bytes(20_000))
        until(lambda: mid in svc.core.s.inbox, timeout=3.0, what="the ring to bring the message")

        server.down = True                                              # half-open: rings and beats vanish
        until(lambda: not svc.doorbell.joined, timeout=3.0, what="a dead socket to be noticed")
        until(lambda: svc.core.s.checkin_interval_s == 60, what="polling every minute again")
    finally:
        svc.stop()
