"""Service entry point on the Pi: `python3 -m dadbox`.

Reads /data (or $DADBOX_DATA), brings up the real hardware (`hw/pi.py`),
talks to the server named in /data/config.env, and serves `dadboxctl` on
/run/dadbox/ctl.sock. The simulator is `python3 -m dadbox.sim`.
"""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

from .clock import Clock
from .ctl import CtlServer, socket_path
from .link import Client, RequestsTransport
from .service import Service
from .store import Store

log = logging.getLogger("dadbox")


def main() -> int:
    logging.basicConfig(level=os.environ.get("DADBOX_LOG", "INFO"),
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    log.info("DadBox starting")
    store = Store(Path(os.environ.get("DADBOX_DATA", "/data")))
    cfg = store.config()
    client = None
    if cfg.get("DADBOX_URL") and cfg.get("DADBOX_TOKEN"):
        client = Client(RequestsTransport(cfg["DADBOX_URL"], cfg["DADBOX_TOKEN"]))
    else:
        log.warning("no DADBOX_URL/DADBOX_TOKEN in %s/config.env: running without a server", store.root)

    from .hw.pi import make_hardware
    hw = make_hardware()
    svc = Service(hw=hw, store=store, clock=Clock(), client=client, has_battery=False)
    svc.on_shutdown = lambda reason: subprocess.Popen(["sudo", "systemctl", "poweroff"])
    ctl = CtlServer(socket_path(), svc.command)

    done = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: done.set())
    svc.start()
    ctl.start()
    _watchdog_loop(done)
    svc.stop()
    ctl.stop()
    return 0


def _watchdog_loop(done: threading.Event) -> None:
    """systemd's WatchdogSec: say we're alive every 20 s while the core thread is."""
    try:
        from systemd import daemon        # python3-systemd, optional
    except ImportError:
        daemon = None
    while not done.wait(20):
        if daemon:
            daemon.notify("WATCHDOG=1")


if __name__ == "__main__":
    sys.exit(main())
