"""systemd's notify protocol, without python3-systemd.

The service runs from its own venv, which cannot see apt's python3-systemd,
so the keepalive for `WatchdogSec=` is sent here directly: one datagram to
$NOTIFY_SOCKET. Outside systemd (the Mac, the simulator) it does nothing.
"""
from __future__ import annotations

import os
import socket
from typing import Optional


def notify(message: str, sock_path: Optional[str] = None) -> bool:
    path = sock_path or os.environ.get("NOTIFY_SOCKET")
    if not path:
        return False
    if path.startswith("@"):                      # abstract namespace
        path = "\0" + path[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.connect(path)
            s.sendall(message.encode())
        return True
    except OSError:
        return False


def watchdog_interval_s(default: float = 20.0) -> float:
    """Half of systemd's WatchdogSec, from $WATCHDOG_USEC; `default` without it."""
    usec = os.environ.get("WATCHDOG_USEC")
    try:
        return max(1.0, int(usec) / 1e6 / 2) if usec else default
    except ValueError:
        return default
