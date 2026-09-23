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
