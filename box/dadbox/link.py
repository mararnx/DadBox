"""The link worker: one thread that owns the modem and the server (PROTOCOL.md).

It never gives up and never decides anything: the core tells it *when* to
check in and whether the modem may go off (`LinkPlan`); it does the work and
posts what it learned as events. Order of a round:

    1. modem on (if it was off) and wait for the interface
    2. upload everything in the outbox, oldest seq first, resuming from
       `upload-state`; delete locally only on `complete` 2xx (ADR 0010)
    3. report messages the child has played; then drop all but the newest (replay)
    4. check in: telemetry up, settings, inbox ids and the doorbell address down
    5. download every inbox id not on disk, crc-checked, and post `Downloaded`
    6. modem off if the plan says so; sleep until the next round or a wake

Any failure ends the round; the next attempt is at min(backoff, interval).
The transport is injected so the simulator's in-process server and the real
`requests` session are interchangeable.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

from . import container as dbx
from .clock import Clock
from .core import Checkin, Downloaded, Event, FaultEvent, LinkState, PlayedReported, UploadDone
from .hal import Modem
from .settings import Settings
from .state import CHUNK_BYTES, Fault
from .store import Store

log = logging.getLogger("dadbox.link")

MODEM_UP_TIMEOUT_S = 90        # from power key to a usable interface; longer means `fault: modem`
BACKOFF_MIN_S = 5
BACKOFF_MAX_S = 300


class Transport(Protocol):
    def request(self, method: str, path: str, *, headers: Optional[Dict[str, str]] = None,
                body: Optional[bytes] = None) -> Tuple[int, Dict[str, str], bytes]:
        """One HTTP request to the server. Raises on a transport failure."""


class LinkError(Exception):
    pass


class RequestsTransport:
    """The real thing: one TLS session kept alive, as every minute's check-in wants."""

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        import requests
        self.base = base_url.rstrip("/")
        self.http = requests.Session()
        self.http.headers["Authorization"] = f"Bearer {token}"
        self.timeout = timeout

    def request(self, method, path, *, headers=None, body=None):
        r = self.http.request(method, self.base + path, headers=headers or {}, data=body, timeout=self.timeout)
        return r.status_code, {k.lower(): v for k, v in r.headers.items()}, r.content


class Client:
    """PROTOCOL.md, the box's half, on any Transport."""

    def __init__(self, transport: Transport):
        self.t = transport

    def _json(self, method: str, path: str, obj: Any = None, ok=(200,)) -> Tuple[int, Any]:
        body = None if obj is None else json.dumps(obj).encode()
        headers = {"Content-Type": "application/json"} if obj is not None else None
        status, _, data = self.t.request(method, path, headers=headers, body=body)
        try:
            parsed = json.loads(data) if data else None
        except ValueError:
            parsed = None
        return status, parsed

    def upload(self, message_id: str, container: bytes, meta: Dict[str, Any], *, cancelled: Callable[[], bool] = lambda: False) -> bool:
        """Idempotent, resumable. True when the server has said 2xx to `complete`."""
        status, body = self._json("PUT", f"/messages/{message_id}", meta)
        if status >= 400:
            raise LinkError(f"PUT metadata {status}: {body}")
        status, st = self._json("GET", f"/messages/{message_id}/upload-state")
        if status >= 400:
            raise LinkError(f"upload-state {status}")
        if st.get("complete"):
            return self._complete(message_id)
        have = set(st.get("received", []))
        total = -(-len(container) // CHUNK_BYTES)
        for i in range(total):
            if i in have:
                continue
            if cancelled():
                raise LinkError("cancelled")
            chunk = container[i * CHUNK_BYTES:(i + 1) * CHUNK_BYTES]
            status, _, _ = self.t.request("PUT", f"/messages/{message_id}/chunks/{i}",
                                          headers={"X-Chunk-Total": str(total), "Content-Type": "application/octet-stream"},
                                          body=chunk)
            if status >= 400:
                raise LinkError(f"chunk {i} {status}")
        return self._complete(message_id)

    def _complete(self, message_id: str) -> bool:
        status, body = self._json("POST", f"/messages/{message_id}/complete")
        if 200 <= status < 300:
            return True
        raise LinkError(f"complete {status}: {body}")

    def checkin(self, telemetry: Dict[str, Any]) -> Tuple[Settings, List[str], Optional[Dict[str, str]]]:
        """(settings, inbox ids, doorbell {url, topic} or None). An absent or
        malformed doorbell means none: the box polls (ADR 0021)."""
        status, body = self._json("POST", "/device/checkin", telemetry)
        if status >= 400 or not isinstance(body, dict):
            raise LinkError(f"checkin {status}: {body}")
        return (Settings.from_json(body.get("settings")), [m for m in body.get("inbox", []) if isinstance(m, str)],
                parse_doorbell(body.get("doorbell")))

    def download(self, message_id: str, have: bytes = b"") -> bytes:
        """Range-resumable: `have` is what an earlier attempt already got."""
        headers = {"Range": f"bytes={len(have)}-"} if have else None
        status, hdrs, data = self.t.request("GET", f"/messages/{message_id}/audio", headers=headers)
        if status == 416:
            return have
        if status == 206:
            return have + data
        if status == 200:
            return data
        raise LinkError(f"audio {status}")

    def played(self, message_id: str) -> None:
        status, body = self._json("POST", f"/messages/{message_id}/played")
        if status >= 400 and status != 404:      # 404: already gone or never ours — nothing to report
            raise LinkError(f"played {status}: {body}")


class LinkWorker:
    def __init__(self, *, client: Optional[Client], store: Store, modem: Modem, clock: Clock,
                 post: Callable[[Event], None], telemetry: Callable[[], Dict[str, Any]]):
        self.client, self.store, self.modem, self.clock, self.post, self.telemetry = client, store, modem, clock, post, telemetry
        self.interval_s = 60
        self.modem_on = True
        self.simulated_down = False              # `dadboxctl sim link down`
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._next_at = 0.0
        self._failures = 0
        self._partial: Dict[str, bytes] = {}      # download resume buffers
        self._checkin_done = threading.Event()
        self.last_round_ok: Optional[bool] = None
        self.thread = threading.Thread(target=self._run, name="link", daemon=True)

    # --- control from the service ---------------------------------------------------------

    def set_plan(self, interval_s: int, modem_on: bool, wake: bool) -> None:
        with self._lock:
            changed = (interval_s, modem_on) != (self.interval_s, self.modem_on)
            self.interval_s, self.modem_on = interval_s, modem_on
            if changed:
                self._next_at = min(self._next_at, self.clock.now() + interval_s)
        if wake or changed:
            self._wake.set()

    def request_checkin(self, timeout_s: float = 20.0) -> Optional[bool]:
        self._checkin_done.clear()
        self._wake.set()
        return self.last_round_ok if self.clock.wait(self._checkin_done, timeout_s) else None

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    # --- the loop --------------------------------------------------------------------------

    def _run(self) -> None:
        while not self._stop.is_set():
            now = self.clock.now()
            with self._lock:
                wait = self._next_at - now
            if wait > 0 and not self._wake.is_set():
                if not self.modem_on and self.modem.is_up():
                    self._modem(False)
                self.clock.wait(self._wake, wait)
                if self._stop.is_set():
                    break
            self._wake.clear()
            ok = self._round()
            self.last_round_ok = ok
            self._checkin_done.set()
            with self._lock:
                if ok:
                    self._failures = 0
                    delay = self.interval_s
                else:
                    self._failures += 1
                    delay = min(min(BACKOFF_MIN_S * 2 ** (self._failures - 1), BACKOFF_MAX_S), self.interval_s)
                self._next_at = self.clock.now() + delay

    def _modem(self, on: bool) -> None:
        self.modem.power(on)
        log.info("modem %s", "on" if on else "off")

    def _round(self) -> bool:
        if self.client is None:
            return False
        try:
            if self.simulated_down:
                raise LinkError("link down (simulated)")
            if not self.modem.is_up():
                self._modem(True)
                deadline = self.clock.now() + MODEM_UP_TIMEOUT_S
                while not self.modem.is_up():
                    if self.clock.now() > deadline:
                        self.post(FaultEvent(Fault.MODEM, True))
                        raise LinkError("modem did not come up")
                    self.clock.sleep(0.5)
            self.post(FaultEvent(Fault.MODEM, False))
            self.post(LinkState(True))
            for mid in self.store.outbox_ids():
                self._upload(mid)
            for mid in self.store.inbox_to_report():
                self.client.played(mid)
                self.store.inbox_mark(mid, reported=True)
                self.post(PlayedReported(mid))
            self.store.inbox_prune_played(keep=1)
            settings, inbox, doorbell = self.client.checkin(self.telemetry())
            self.store.save_settings(settings.to_json())
            if doorbell != self.store.doorbell_json():
                self.store.save_doorbell(doorbell)
            self.post(Checkin(True, settings, tuple(inbox), rssi=self.modem.rssi(), doorbell=doorbell))
            broken = set(self.store.inbox_broken())
            for mid in inbox:
                if mid in broken:
                    continue
                if not self.store.inbox_has(mid):
                    self._download(mid)
                else:
                    self.post(Downloaded(mid))   # idempotent: the core ignores what it knows
            return True
        except Exception as e:                   # noqa: BLE001 — any failure ends the round; the loop retries forever
            log.warning("link round failed: %s", e)
            self.post(LinkState(False))
            self.post(Checkin(False, error=str(e)))
            return False

    def _upload(self, mid: str) -> None:
        meta = self.store.outbox_meta(mid)
        body = {k: meta[k] for k in ("seq", "to", "created_at", "time_ok", "duration_ms", "codec", "key_id", "bytes")}
        self.store.outbox_set_state(mid, "uploading")
        if self.client.upload(mid, self.store.outbox_container(mid), body, cancelled=lambda: self.simulated_down):
            self.store.outbox_remove(mid)        # the 2xx has been given: two copies became one (ADR 0010)
            self.post(UploadDone(mid))

    def _download(self, mid: str) -> None:
        data = self.client.download(mid, self._partial.get(mid, b""))
        if not dbx.crc_ok(data):
            if len(data) < dbx.HEADER_LEN + 4 or len(self._partial.get(mid, b"")) < len(data):
                self._partial[mid] = data        # maybe a truncated body: try to resume next round
                raise LinkError(f"download {mid}: crc mismatch, {len(data)} bytes so far")
            self._partial.pop(mid, None)
            raise LinkError(f"download {mid}: crc mismatch")
        self._partial.pop(mid, None)
        self.store.inbox_put(mid, data)
        self.post(Downloaded(mid))


def parse_doorbell(d: Any) -> Optional[Dict[str, str]]:
    if not isinstance(d, dict):
        return None
    url, topic = d.get("url"), d.get("topic")
    if not (isinstance(url, str) and isinstance(topic, str) and topic
            and url.split("://", 1)[0] in ("wss", "ws", "sim")):
        return None
    return {"url": url, "topic": topic}


def iso(wall: float) -> str:
    return datetime.fromtimestamp(wall, timezone.utc).isoformat().replace("+00:00", "Z")
