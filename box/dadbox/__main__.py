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
from .sdnotify import notify, watchdog_interval_s
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
    # One sudoers rule allows exactly this command (box/setup/README.md step 5).
    svc.on_shutdown = lambda reason: subprocess.Popen(["sudo", "-n", "/usr/bin/systemctl", "poweroff"])
    ctl = CtlServer(socket_path(), svc.command)

    done = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: done.set())
    svc.start()
    ctl.start()
    notify("READY=1")
    _watchdog_loop(done, svc)
    svc.stop()
    ctl.stop()
    return 0


def _watchdog_loop(done: threading.Event, svc: Service) -> None:
    """systemd's WatchdogSec: say we're alive — but only while the core thread
    is. A dead core goes quiet, and systemd restarts the service."""
    every = watchdog_interval_s()
    while not done.wait(every):
        if svc.thread.is_alive():
            notify("WATCHDOG=1")
        else:
            log.error("core thread is dead: withholding the watchdog keepalive")
    notify("STOPPING=1")


if __name__ == "__main__":
    sys.exit(main())
