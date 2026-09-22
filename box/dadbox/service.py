"""Where the pure core meets the world.

One thread steps the core: it takes events off a queue, hands each to
`Core.handle`, and dispatches the returned actions to drivers and workers.
Drivers and workers run their own threads and only ever `post()` events
back. Nothing else touches the core. The lights are rendered by their own
driver thread from the last `LightsPlan`, so a breathing button costs the
core nothing.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, Dict, List, Optional, Tuple

from . import core as c
from .audio import AudioWorker
from .clock import Clock
from .gestures import Button
from .hal import Hardware
from .lights import LightsPlan, StatusPlan, render, render_status
from .link import Client, LinkWorker
from .settings import Settings
from .state import Lights
from .store import Store

log = logging.getLogger("dadbox")

TICK_S = 0.05
RENDER_HZ = 30


class LightsDriver:
    """Renders the child's and the adults' channels at RENDER_HZ."""

    def __init__(self, hw: Hardware, clock: Clock):
        self.hw, self.clock = hw, clock
        self.plan = LightsPlan()
        self.status = StatusPlan()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._test_until = 0.0
        self.thread = threading.Thread(target=self._run, name="lights", daemon=True)

    def set_plan(self, plan: LightsPlan) -> None:
        with self._lock:
            self.plan = plan

    def set_status(self, status: StatusPlan) -> None:
        with self._lock:
            self.status = status

    def test(self) -> None:
        """`dadboxctl led test`: every button-light state for 2 s each. The
        recording state is shown without the mic pin — the driver never touches it."""
        with self._lock:
            self._test_until = self.clock.now() + 2.0 * len(Lights)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            now = self.clock.now()
            with self._lock:
                plan, status, test_until = self.plan, self.status, self._test_until
            if now < test_until:
                idx = int((test_until - now) / 2.0) % len(Lights)
                plan = LightsPlan(lights=list(Lights)[idx], brightness=100)
            frame = render(plan, now)
            self.hw.lights.write(frame)
            self.hw.status.write(*render_status(status, now))
            self._stop.wait(1.0 / RENDER_HZ)


class Service:
    def __init__(self, *, hw: Hardware, store: Store, clock: Clock, client: Optional[Client],
                 has_battery: bool = False, key_id: int = 1):
        self.hw, self.store, self.clock = hw, store, clock
        self.events: "queue.Queue[c.Event]" = queue.Queue()
        self.core = c.Core(clock, has_battery=has_battery)
        self.lights = LightsDriver(hw, clock)
        self.link = LinkWorker(client=client, store=store, modem=hw.modem, clock=clock,
                               post=self.post, telemetry=self.telemetry)
        self.audio = AudioWorker(backend=hw.audio, amp=hw.amp, store=store, clock=clock, post=self.post,
                                 key_id=key_id, keys=store.keys())
        self._replies: Dict[int, "queue.Queue[str]"] = {}
        self._token = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.on_shutdown: Callable[[str], None] = lambda reason: log.warning("shutdown requested: %s", reason)
        self.log_lines: List[Tuple[float, str, str]] = []      # (wall, level, text) — the simulator shows these

    # --- inputs ----------------------------------------------------------------------------

    def post(self, event: c.Event) -> None:
        self.events.put(event)

    def contact(self, button: Button, down: bool) -> None:
        self.post(c.Contact(button, down))

    def command(self, name: str, args: Tuple[str, ...] = (), timeout_s: float = 30.0) -> str:
        """`dadboxctl`: commands the service answers itself, then the core's."""
        if name in ("inbox", "outbox"):
            return self._list(name)
        if name == "sim" and args[:1] == ("link",):
            self.link.simulated_down = args[1:2] == ("down",)
            self.link.set_plan(self.link.interval_s, self.link.modem_on, wake=True)
            return "link " + ("down (simulated)" if self.link.simulated_down else "up")
        if name == "checkin":
            ok = self.link.request_checkin(timeout_s)
            snap = self.core.snapshot()
            return ("check-in ok" if ok else "check-in failed" if ok is False else "check-in timed out") + \
                f"; inbox {snap['inbox']}; settings {snap['settings']}"
        with self._lock:
            self._token += 1
            token = self._token
            self._replies[token] = queue.Queue()
        self.post(c.Command(name, tuple(args), token))
        try:
            return self._replies[token].get(timeout=timeout_s)
        except queue.Empty:
            return "no reply"
        finally:
            with self._lock:
                self._replies.pop(token, None)

    def _list(self, which: str) -> str:
        wall = self.clock.wall()
        lines = []
        if which == "outbox":
            sizes = self.store.outbox_bytes()
            for mid in self.store.outbox_ids():
                m = self.store.outbox_meta(mid)
                lines.append(f"{mid}  seq {m.get('seq')}  {sizes.get(mid, 0)} B  {m.get('duration_ms')} ms  {m.get('state')}")
        else:
            for mid in sorted(p.stem for p in (self.store.root / "inbox").glob("*.dbx")):
                f = self.store._inbox_flags(mid)
                lines.append(f"{mid}  {'played' if f.get('played') else 'unheard'}{' broken' if f.get('broken') else ''}")
        return "\n".join(lines) if lines else f"{which} empty"

    # --- telemetry for the link worker ----------------------------------------------------------

    def telemetry(self) -> dict:
        sizes = self.store.outbox_bytes()
        return self.core.telemetry(outbox_bytes=sum(sizes.values()),
                                   outbox_oldest_s=self.store.outbox_oldest_age_s(self.clock.wall()),
                                   storage_pct=self.store.storage_pct(), inbox_on_disk=len(self.store.inbox_unheard()))

    # --- lifecycle --------------------------------------------------------------------------------

    def boot_event(self) -> c.Boot:
        mains, pct, charging = self.hw.power.read()
        settings = Settings.from_json(self.store.settings_json())
        return c.Boot(outbox=self.store.outbox_bytes(), inbox=self.store.inbox_unheard(), locked=self.store.locked(),
                      settings=settings, pending_captures=self.store.pending_captures(),
                      mains=mains, battery_pct=pct, charging=charging, last_played=self.store.inbox_last_played())

    def start(self) -> None:
        self.hw.mic.set(False)
        self.store.wipe_tmp()
        self.lights.start()
        self.hw.buttons.watch(self.contact)
        self.post(self.boot_event())
        self.link.start()
        threading.Thread(target=self._power_poll, name="power", daemon=True).start()
        self.thread = threading.Thread(target=self.run, name="core", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.link.stop()
        self.lights.stop()
        self.hw.mic.set(False)
        self.hw.amp.set(False)

    def _power_poll(self) -> None:
        last = None
        while not self._stop.is_set():
            reading = self.hw.power.read()
            if reading != last:
                last = reading
                self.post(c.PowerState(*reading))
            self.clock.sleep(2.0)

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                event = self.events.get(timeout=TICK_S / max(1.0, getattr(self.clock, "speed", 1.0)))
            except queue.Empty:
                event = c.Tick()
            try:
                for action in self.core.handle(event):
                    self.dispatch(action)
            except Exception:                                    # noqa: BLE001 — the core must never die
                log.exception("while handling %r", event)

    # --- actions → the world ---------------------------------------------------------------------

    def dispatch(self, a: c.Action) -> None:
        if isinstance(a, c.MicPower):
            self.hw.mic.set(a.on)
        elif isinstance(a, c.SetLights):
            self.lights.set_plan(a.plan)
        elif isinstance(a, c.SetStatus):
            self.lights.set_status(a.plan)
        elif isinstance(a, c.StartCapture):
            self.audio.start_capture(a.message_id, a.created_at_wall, a.time_ok)
        elif isinstance(a, c.StopCapture):
            self.audio.stop_capture(a.message_id)
        elif isinstance(a, c.Encode):
            self.audio.encode(a.message_id, a.recovered)
        elif isinstance(a, c.Play):
            self.audio.play(a.message_id, a.volume)
        elif isinstance(a, c.StopPlay):
            self.audio.stop_play()
        elif isinstance(a, c.Chime):
            self.audio.chime(a.volume)
        elif isinstance(a, c.PersistLock):
            self.store.set_locked(a.locked)
        elif isinstance(a, c.MarkPlayed):
            self.audio.mark_played(a.message_id, a.ok)
            self.link.set_plan(self.link.interval_s, self.link.modem_on, wake=True)
        elif isinstance(a, c.LinkPlan):
            self.link.set_plan(a.interval_s, a.modem_on, a.wake)
        elif isinstance(a, c.Reply):
            q = self._replies.get(a.token)
            if q is not None:
                q.put(a.text)
        elif isinstance(a, c.Log):
            getattr(log, a.level, log.info)(a.message)
            self.log_lines.append((self.clock.wall(), a.level, a.message))
            del self.log_lines[:-300]
        elif isinstance(a, c.Shutdown):
            log.warning("shutting down: %s", a.reason)
            self.on_shutdown(a.reason)
        elif isinstance(a, c.LedTest):
            self.lights.test()
        elif isinstance(a, c.ModemPower):
            self.hw.modem.power(a.on)
        else:
            log.warning("unhandled action %r", a)
