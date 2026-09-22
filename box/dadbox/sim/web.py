"""The simulator's window: a tiny HTTP server (stdlib only) that draws the box
and lets you press its buttons, be the parent, and pull the link or the plug.
The page polls `/api/state` ten times a second; every knob is a POST.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from ..clock import FakeClock
from ..gestures import Button
from ..hal import Hardware
from ..service import Service
from ..store import Store
from .audio import SimAudio
from .parent import Parent
from .server import FakeServer

log = logging.getLogger("dadbox.sim")
UI = Path(__file__).with_name("ui.html")


def _iso(wall: float) -> str:
    return datetime.fromtimestamp(wall, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class SimApp:
    def __init__(self, *, svc: Service, hw: Hardware, clock: FakeClock, store: Store, audio: SimAudio,
                 server: Optional[FakeServer], parent: Optional[Parent], real_url: Optional[str] = None):
        self.svc, self.hw, self.clock, self.store, self.audio = svc, hw, clock, store, audio
        self.server, self.parent, self.real_url = server, parent, real_url
        self.pushes_seen = 0
        if server is not None:
            threading.Thread(target=self._cron, name="pg_cron", daemon=True).start()

    def _cron(self) -> None:
        while True:
            self.clock.sleep(60)
            self.server.tick()

    # --- state for the page -----------------------------------------------------------------

    def state(self) -> Dict[str, Any]:
        snap = self.svc.core.snapshot()
        frame = self.hw.lights.frame
        modem = self.hw.modem
        power = self.hw.power
        playing = self.audio.playing
        box = dict(snap)
        box.update({
            "state_line": self.svc.core.state_line(),
            "mic": self.hw.mic.is_on(), "amp": self.hw.amp.on,
            "frame": {"record": list(frame.record), "play": list(frame.play)},
            "status": {"link": self.hw.status.link, "power": self.hw.status.power},
            "telemetry": self.svc.telemetry(),
            "outbox_ids": self.store.outbox_ids(), "inbox_on_disk": self.store.inbox_count(),
            "playing": None if not playing else {
                "codec": playing["codec"], "duration_s": playing["duration_s"],
                "elapsed_s": self.clock.now() - playing["started"], "real": playing["audio"][:4] != b"RIFF"},
            "link_worker": {"simulated_down": self.svc.link.simulated_down, "failures": self.svc.link._failures,
                            "next_in_s": max(0.0, self.svc.link._next_at - self.clock.now())},
            "doorbell_worker": {"joined": self.svc.doorbell.joined, "failures": self.svc.doorbell.failures,
                                "rings": self.svc.doorbell.rings, "silent": self.svc.doorbell.simulated_silent},
        })
        world = {"coverage": modem.coverage, "modem_powered": modem.powered, "mains": power.mains,
                 "battery_pct": power.battery_pct, "charging": power.charging, "speaking": self.audio.speaking,
                 "server_down": bool(self.server and self.server.down), "real_server": self.real_url,
                 "have_ffmpeg": self.audio.encoded_real_opus}
        srv: Dict[str, Any] = {}
        if self.server is not None:
            msgs = sorted(self.server.messages.values(), key=lambda m: m["uploaded_at"] or "~")
            srv = {"messages": [{k: m[k] for k in ("id", "seq", "from", "to", "duration_ms", "codec", "state",
                                                   "uploaded_at", "delivered_at", "played_at", "time_ok")} for m in msgs],
                   "pushes": self.server.pushes[-12:], "device": self.server.device_status(),
                   "alerts": sorted(k for k, v in self.server.alerts.items() if v), "requests": self.server.requests}
        return {"sim": {"now": self.clock.now(), "wall": _iso(self.clock.wall()), "speed": self.clock.speed},
                "box": box, "world": world, "server": srv,
                "log": [{"at": _iso(w), "level": lv, "text": t} for w, lv, t in self.svc.log_lines[-80:]]}

    # --- knobs -------------------------------------------------------------------------------------

    def button(self, b: Dict[str, Any]) -> Dict[str, Any]:
        self.hw.buttons.press(Button(b["button"]), bool(b["down"]))
        return {"ok": True}

    def world(self, b: Dict[str, Any]) -> Dict[str, Any]:
        if "coverage" in b:
            self.hw.modem.coverage = bool(b["coverage"])
        if "server_down" in b and self.server is not None:
            self.server.down = bool(b["server_down"])
        if "speaking" in b:
            self.audio.speaking = bool(b["speaking"])
        if "fail_capture" in b:
            self.audio.fail_capture = bool(b["fail_capture"])
        if "mains" in b or "battery_pct" in b or "charging" in b:
            p = self.hw.power
            p.mains = bool(b.get("mains", p.mains))
            p.battery_pct = b.get("battery_pct", p.battery_pct)
            p.charging = bool(b.get("charging", p.charging))
            self.svc.core.has_battery = p.battery_pct is not None
        if "speed" in b:
            self.clock.set_speed(float(b["speed"]))
        if "skip_s" in b:
            self.clock.skip(float(b["skip_s"]))
        if "wall_hhmm" in b:                     # set the local time of day (Europe/Zurich) for quiet hours
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(self.svc.core.s.settings.quiet_hours.tz)
            now = datetime.fromtimestamp(self.clock.wall(), tz)
            h, m = map(int, b["wall_hhmm"].split(":"))
            self.clock.set_wall(now.replace(hour=h, minute=m, second=0).timestamp())
        if "power_cut" in b:
            raise SystemExit("power cut (simulated): restart the simulator to see the recovery")
        return {"ok": True}

    def parent_send(self, b: Dict[str, Any]) -> Dict[str, Any]:
        if self.parent is None:
            return {"error": "real server: send from the iPhone app or tools/fakebox"}
        mid = self.parent.send(float(b.get("seconds", 8)), drop_after=b.get("drop_after"))
        return {"id": mid}

    def parent_settings(self, b: Dict[str, Any]) -> Dict[str, Any]:
        if self.parent is None:
            return {"error": "real server"}
        return self.parent.settings(b)

    def ctl(self, b: Dict[str, Any]) -> Dict[str, Any]:
        argv = b.get("argv") or ["state"]
        return {"reply": self.svc.command(argv[0], tuple(argv[1:]), timeout_s=15)}

    def audio_playing(self) -> Optional[Tuple[bytes, str]]:
        p = self.audio.playing
        if not p:
            return None
        ctype = "audio/mp4" if p["codec"] == 3 else "audio/ogg"
        if p["audio"][:4] == b"RIFF":
            ctype = "audio/wav"
        return p["audio"], ctype

    def audio_from_box(self, mid: str) -> Optional[Tuple[bytes, str]]:
        if self.parent is None:
            return None
        data = self.parent.audio(mid)
        return data, ("audio/wav" if data[:4] == b"RIFF" else "audio/ogg")


class _Handler(BaseHTTPRequestHandler):
    app: SimApp

    def log_message(self, *a):                        # quiet
        pass

    def _send(self, status: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, obj: Any) -> None:
        self._send(status, json.dumps(obj).encode())

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path in ("/", "/index.html"):
                self._send(200, UI.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/state":
                self._json(200, self.app.state())
            elif path == "/api/audio/playing":
                r = self.app.audio_playing()
                self._send(200, r[0], r[1]) if r else self._json(404, {"error": "nothing playing"})
            elif path.startswith("/api/audio/box/"):
                r = self.app.audio_from_box(path.rsplit("/", 1)[1])
                self._send(200, r[0], r[1]) if r else self._json(404, {"error": "no such message"})
            else:
                self._json(404, {"error": "not found"})
        except Exception as e:                       # noqa: BLE001
            log.exception("GET %s", path)
            self._json(500, {"error": str(e)})

    def do_POST(self):
        path = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            routes = {"/api/button": self.app.button, "/api/world": self.app.world,
                      "/api/parent/send": self.app.parent_send, "/api/parent/settings": self.app.parent_settings,
                      "/api/ctl": self.app.ctl}
            fn = routes.get(path)
            self._json(200, fn(body)) if fn else self._json(404, {"error": "not found"})
        except SystemExit as e:
            self._json(200, {"ok": True, "note": str(e)})
            threading.Thread(target=lambda: (__import__("time").sleep(0.2), __import__("os")._exit(3)), daemon=True).start()
        except Exception as e:                       # noqa: BLE001
            log.exception("POST %s", path)
            self._json(500, {"error": str(e)})


def serve(app: SimApp, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    handler = type("Handler", (_Handler,), {"app": app})
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, name="web", daemon=True).start()
    return httpd
