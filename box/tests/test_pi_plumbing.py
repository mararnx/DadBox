"""The Linux plumbing that can be checked on the Mac: the systemd notify
datagram and the "is there a way out" test the modem driver uses."""
import os
import socket
import tempfile

from dadbox.sdnotify import notify, watchdog_interval_s


def test_notify_sends_one_datagram_to_the_notify_socket():
    path = os.path.join(tempfile.mkdtemp(), "notify")
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as srv:
        srv.bind(path)
        assert notify("WATCHDOG=1", path) is True
        assert srv.recv(64) == b"WATCHDOG=1"


def test_notify_outside_systemd_does_nothing(monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    assert notify("READY=1") is False


def test_watchdog_interval_is_half_of_watchdogsec(monkeypatch):
    monkeypatch.setenv("WATCHDOG_USEC", "60000000")
    assert watchdog_interval_s() == 30.0
    monkeypatch.delenv("WATCHDOG_USEC")
    assert watchdog_interval_s() == 20.0


def test_default_route_on_the_bench_and_in_the_field():
    import importlib.util, sys, types
    # hw/pi.py imports gpiozero lazily; the parser is plain text work.
    from dadbox.hw.pi import has_default_route
    assert has_default_route("default via 192.168.1.1 dev wlan0 proto dhcp src 192.168.1.23 metric 600\n")
    assert has_default_route("default via 192.168.225.1 dev usb0 proto dhcp metric 100\n")
    assert not has_default_route("")
    assert not has_default_route("192.168.1.0/24 dev wlan0 proto kernel scope link\n")


def test_csq_reply_to_dbm():
    from dadbox.hw.pi import csq_to_dbm
    assert csq_to_dbm("AT+CSQ\r\n+CSQ: 20,0\r\n\r\nOK\r\n") == -73
    assert csq_to_dbm("+CSQ: 0,99\r\nOK") == -113
    assert csq_to_dbm("+CSQ: 31,0\r\nOK") == -51
    assert csq_to_dbm("+CSQ: 99,99\r\nOK") is None       # not known or not detectable
    assert csq_to_dbm("ERROR") is None
    assert csq_to_dbm("") is None


class _BlockingArecord:
    """arecord's stand-in: a few blocks, then blocked in read until terminated, then EOF."""

    def __init__(self, blocks):
        import threading
        self._blocks, self._killed, self.returncode = list(blocks), threading.Event(), None
        self.stdout = self

    def read(self, n):
        if self._blocks:
            return self._blocks.pop(0)
        self._killed.wait(5)
        return b""

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = -15
        self._killed.set()


def _capture_with(monkeypatch, fake):
    from dadbox.dsp import BLOCK_BYTES
    from dadbox.hw import pi
    monkeypatch.setattr(pi.subprocess, "Popen", lambda *a, **k: fake)
    ended = []
    path = os.path.join(tempfile.mkdtemp(), "c.pcm")
    return pi._Capture(path, lambda *a: None, lambda ok, r: ended.append((ok, r))), ended, path, BLOCK_BYTES


def test_stopping_a_capture_blocked_in_read_is_a_normal_end(monkeypatch):
    # Found on the bench, 2026-10-06: stop() lands while the pump waits for a fresh block,
    # read() returns b"", and a normal release was reported as "arecord ended".
    fake = _BlockingArecord([b"\0\1" * 2000] * 4)
    cap, ended, path, block = _capture_with(monkeypatch, fake)
    import time
    time.sleep(0.2)
    cap.stop()
    cap.thread.join(2)
    assert ended == [(True, "")]
    assert os.path.getsize(path) == 3 * len(b"\0\1" * 2000)     # the first block is the mic's click


def test_arecord_dying_on_its_own_is_still_a_failure(monkeypatch):
    fake = _BlockingArecord([b"\0\1" * 2000] * 2)
    fake._killed.set()                                          # EOF without anyone calling stop()
    cap, ended, _, _ = _capture_with(monkeypatch, fake)
    cap.thread.join(2)
    assert ended == [(False, "arecord ended")]
