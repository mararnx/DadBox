"""`python3 -m dadbox.sim` — the virtual box.

    python3 -m dadbox.sim                      fake server, web UI on http://127.0.0.1:8765
    python3 -m dadbox.sim --speed 10           simulated time runs 10× faster
    python3 -m dadbox.sim --real-server        talk to the live Supabase server from tools/fakebox/.env
    python3 -m dadbox.sim --data DIR           where /data lives (default ~/.dadbox-sim; survives restarts,
                                               so a "power cut" mid-recording is recovered on the next start)
    DADBOX_CTL=~/.dadbox-sim/ctl.sock python3 -m dadbox.ctl state      dadboxctl against the simulator
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
from pathlib import Path

from ..clock import FakeClock
from ..ctl import CtlServer
from ..hal import Hardware
from ..link import Client, RequestsTransport
from ..service import Service
from ..store import Store
from .audio import SimAudio
from .hal import (FakeAmpGate, FakeButtonLights, FakeButtons, FakeMicGate, FakeModem, FakePower, FakeStatusLeds)
from .parent import Parent
from .server import FakeServer
from .web import SimApp, serve

SIM_KEY = bytes.fromhex("6461646206f8b0d2c1a3e5f7091b2d3f4a5c6e7081920b3c4d5e6f708192a3b4")   # a TEST key, sim only


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")), help="default: $PORT or 8765")
    p.add_argument("--data", default=os.path.expanduser("~/.dadbox-sim"))
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--voice", help="a 16 kHz mono WAV to record 'from' instead of the synthetic voice")
    p.add_argument("--real-server", action="store_true", help="use DADBOX_URL / DADBOX_TOKEN_BOX / DADBOX_KEY_1 from tools/fakebox/.env")
    p.add_argument("--battery", type=int, help="pretend a battery is fitted, at this percentage")
    p.add_argument("--log", default="INFO")
    a = p.parse_args()
    logging.basicConfig(level=a.log, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    clock = FakeClock(speed=a.speed)
    store = Store(Path(a.data))
    server = parent = None
    real_url = None
    if a.real_server:
        env = Path(__file__).resolve().parents[3] / "tools" / "fakebox" / ".env"
        cfg = dict(os.environ)
        if env.exists():
            for line in env.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    cfg.setdefault(k.strip(), v.strip())
        real_url = cfg["DADBOX_URL"]
        store.put_key(1, bytes.fromhex(cfg["DADBOX_KEY_1"]))
        client = Client(RequestsTransport(real_url, cfg["DADBOX_TOKEN_BOX"]))
    else:
        if 1 not in store.keys():
            store.put_key(1, SIM_KEY)
        server = FakeServer(clock)
        parent = Parent(server, store.keys()[1])
        client = Client(server.transport("box"))

    audio = SimAudio(clock, a.voice)
    hw = Hardware(buttons=FakeButtons(), lights=FakeButtonLights(), status=FakeStatusLeds(), mic=FakeMicGate(),
                  amp=FakeAmpGate(), modem=FakeModem(), power=FakePower(mains=True, battery_pct=a.battery), audio=audio)
    svc = Service(hw=hw, store=store, clock=clock, client=client, has_battery=a.battery is not None,
                  **({} if server is None else {"doorbell_connect": lambda url: server.doorbell_connect(url, hw.modem.is_up)}))
    app = SimApp(svc=svc, hw=hw, clock=clock, store=store, audio=audio, server=server, parent=parent, real_url=real_url)
    ctl = CtlServer(str(Path(a.data) / "ctl.sock"), svc.command)

    svc.start()
    ctl.start()
    httpd = serve(app, port=a.port)
    print(f"DadBox simulator: http://127.0.0.1:{a.port}   data: {a.data}   "
          f"{'REAL server ' + real_url if real_url else 'fake server in-process'}")
    print(f"dadboxctl: DADBOX_CTL={Path(a.data) / 'ctl.sock'} python3 -m dadbox.ctl state")
    done = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: done.set())
    done.wait()
    httpd.shutdown()
    svc.stop()
    ctl.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
