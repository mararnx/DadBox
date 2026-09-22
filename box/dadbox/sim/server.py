"""An in-process DadBox server: PROTOCOL.md v0.3, the same rules as
`server/supabase/functions/api`, with dicts instead of Postgres and Storage.

It implements the `link.Transport` interface directly, so the box's real
`link.Client` talks to it without an HTTP stack — and the web UI plays the
parent through the very same routes with the parent's token. What it does
not do: APNs (it records what it *would* have pushed) and Supabase.

It also rings the doorbell (ADR 0021): `doorbell_connect` hands the box's
doorbell worker an in-process socket that speaks the same Phoenix messages
as Supabase Realtime, and the server rings every open one when a message to
the box completes or the settings change — just as the database trigger does.
"""
from __future__ import annotations

import json
import queue
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from .. import container as dbx
from ..ids import is_ulid
from ..state import CHUNK_BYTES

MAX_DURATION_MS = 5 * 60 * 1000
MAX_MESSAGE_BYTES = 4 * 1024 * 1024
DEFAULT_SETTINGS = {
    "poll": {"active_minutes": 1, "active_window_minutes": 90, "idle_minutes": 30, "backstop_minutes": 10},
    "quiet_hours": {"start": "20:00", "end": "07:00", "tz": "Europe/Zurich"},
    "led_brightness": 40, "volume": 70,
}
TOKENS = {"box": "sim-box-token", "parent-a": "sim-parent-a-token", "parent-b": "sim-parent-b-token"}


def _iso(t: Optional[float] = None) -> str:
    return datetime.fromtimestamp(time.time() if t is None else t, timezone.utc).isoformat().replace("+00:00", "Z")


class FakeServer:
    def __init__(self, clock=None):
        self.clock = clock
        self.messages: Dict[str, Dict[str, Any]] = {}
        self.chunks: Dict[str, Dict[int, bytes]] = {}
        self.blobs: Dict[str, bytes] = {}
        self.settings: Dict[str, Any] = json.loads(json.dumps(DEFAULT_SETTINGS))
        self.settings_meta: Dict[str, Any] = {}
        self.telemetry: Optional[Dict[str, Any]] = None
        self.last_checkin_at: Optional[float] = None
        self.next_due_at: Optional[float] = None
        self.pushes: List[Dict[str, Any]] = []
        self.alerts: Dict[str, bool] = {}
        self.audit: List[Dict[str, Any]] = []
        self.requests = 0
        self.down = False                       # the world without a server
        self.doorbell_topic: Optional[str] = "doorbell:" + secrets.token_hex(16)   # None: no doorbell
        self.doorbell_sockets: List["FakeDoorbellSocket"] = []
        self.rings_sent = 0
        self._lock = threading.RLock()
        self._counter = 0

    def _wall(self) -> float:
        return self.clock.wall() if self.clock else time.time()

    # --- Transport for one identity ---------------------------------------------------------

    def transport(self, who: str) -> "FakeTransport":
        return FakeTransport(self, TOKENS[who])

    # --- the router --------------------------------------------------------------------------

    def handle(self, method: str, path: str, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, Dict[str, str], bytes]:
        with self._lock:
            self.requests += 1
            if self.down:
                raise ConnectionError("server unreachable (simulated)")
            headers = {k.lower(): v for k, v in headers.items()}
            who = self._auth(headers.get("authorization", ""))
            if who is None:
                return self._json(401, {"error": "unauthorized"})
            try:
                return self._route(who, method, path, headers, body or b"")
            except _Fail as f:
                return self._json(f.status, dict({"error": f.error}, **f.extra))

    def _auth(self, header: str) -> Optional[str]:
        m = re.match(r"^Bearer\s+(\S+)$", header, re.I)
        if not m:
            return None
        for who, tok in TOKENS.items():
            if tok == m.group(1):
                return who
        return None

    @staticmethod
    def _json(status: int, obj: Any, extra_headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, str], bytes]:
        h = {"content-type": "application/json"}
        h.update(extra_headers or {})
        return status, h, json.dumps(obj).encode()

    def _route(self, who, method, path, headers, body):
        m = re.fullmatch(r"/messages/([^/]+)(/chunks/(\d+)|/upload-state|/complete|/audio|/played)?", path)
        if m:
            mid, sub, seq = m.group(1), m.group(2) or "", m.group(3)
            if method == "PUT" and not sub:
                return self._put_message(who, mid, body)
            if method == "PUT" and sub.startswith("/chunks/"):
                return self._put_chunk(who, mid, int(seq), headers, body)
            if method == "GET" and sub == "/upload-state":
                return self._upload_state(who, mid)
            if method == "POST" and sub == "/complete":
                return self._complete(who, mid)
            if method == "GET" and sub == "/audio":
                return self._audio(who, mid, headers)
            if method == "POST" and sub == "/played":
                return self._played(who, mid)
            if method == "GET" and not sub:
                return self._get_message(who, mid)
        if method == "GET" and path.startswith("/messages"):
            return self._list(who, path)
        if method == "GET" and path == "/device/status":
            return self._status(who)
        if method == "PATCH" and path == "/settings":
            return self._patch_settings(who, body)
        if method == "POST" and path == "/device/checkin":
            return self._checkin(who, body)
        if method == "PUT" and path == "/push-token":
            return self._json(200, {"ok": True}) if who != "box" else self._json(403, {"error": "parents only"})
        raise _Fail(404, "not found")

    # --- upload ---------------------------------------------------------------------------------

    def _put_message(self, who, mid, body):
        if not is_ulid(mid):
            raise _Fail(400, "id must be a ULID")
        try:
            b = json.loads(body)
        except ValueError:
            raise _Fail(400, "invalid metadata: body must be a JSON object")
        meta = self._validate(who, b)
        row = self.messages.get(mid)
        if row is None:
            if any(r["seq"] == meta["seq"] and r["from"] == who for r in self.messages.values()):
                raise _Fail(409, "seq already used by another message")
            row = dict(meta, id=mid, **{"from": who}, state="uploading", uploaded_at=None, delivered_at=None,
                       played_at=None, updated_at=self._wall(), chunk_total=-(-meta["bytes"] // CHUNK_BYTES))
            self.messages[mid] = row
            self.chunks[mid] = {}
        elif row["from"] != who or any(row[k] != meta[k] for k in meta):
            raise _Fail(409, "this id exists with different metadata")
        return self._json(200, self._wire(row))

    def _validate(self, who, b):
        if not isinstance(b, dict):
            raise _Fail(400, "invalid metadata: body must be a JSON object")
        for k, (lo, hi) in {"seq": (0, 2 ** 53), "duration_ms": (1, MAX_DURATION_MS), "key_id": (1, 255), "bytes": (1, MAX_MESSAGE_BYTES)}.items():
            v = b.get(k)
            if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
                raise _Fail(400, f"invalid metadata: {k}")
        if b.get("to") not in ("box", "parent-a", "parent-b"):
            raise _Fail(400, "invalid metadata: to")
        if not isinstance(b.get("time_ok"), bool):
            raise _Fail(400, "invalid metadata: time_ok")
        if b.get("codec") not in (2, 3):
            raise _Fail(400, "invalid metadata: codec")
        if not isinstance(b.get("created_at"), str):
            raise _Fail(400, "invalid metadata: created_at")
        if who == "box" and b["to"] != "parent-a":
            raise _Fail(400, "invalid metadata: v1: the box sends to parent-a only")
        if who != "box" and b["to"] != "box":
            raise _Fail(400, "invalid metadata: parents send to the box only")
        return {k: b[k] for k in ("seq", "to", "created_at", "time_ok", "duration_ms", "codec", "key_id", "bytes")}

    def _put_chunk(self, who, mid, seq, headers, body):
        row = self.messages.get(mid)
        if not row or row["from"] != who:
            raise _Fail(404, "no such message")
        if row["state"] != "uploading":
            return self._json(200, {"ok": True, "complete": True})
        total = int(headers.get("x-chunk-total", -1))
        if total != row["chunk_total"]:
            raise _Fail(400, f"X-Chunk-Total must be {row['chunk_total']}")
        if not 0 <= seq < total:
            raise _Fail(400, "chunk seq out of range")
        want = row["bytes"] - CHUNK_BYTES * (total - 1) if seq == total - 1 else CHUNK_BYTES
        if len(body) > CHUNK_BYTES:
            raise _Fail(413, "chunk larger than 32 KB")
        if len(body) != want:
            raise _Fail(400, f"chunk {seq} must be {want} bytes")
        self.chunks[mid][seq] = bytes(body)
        return self._json(200, {"ok": True})

    def _upload_state(self, who, mid):
        row = self.messages.get(mid)
        if not row or row["from"] != who:
            raise _Fail(404, "no such message")
        if row["state"] != "uploading":
            return self._json(200, {"received": list(range(row["chunk_total"])), "complete": True})
        return self._json(200, {"received": sorted(self.chunks[mid]), "complete": False})

    def _complete(self, who, mid):
        row = self.messages.get(mid)
        if not row or row["from"] != who:
            raise _Fail(404, "no such message")
        if row["state"] != "uploading":
            return self._json(200, self._wire(row))
        missing = [i for i in range(row["chunk_total"]) if i not in self.chunks[mid]]
        if missing:
            raise _Fail(409, "chunks missing", missing=missing)
        container = b"".join(self.chunks[mid][i] for i in range(row["chunk_total"]))
        if len(container) != row["bytes"]:
            raise _Fail(422, "assembled size differs from metadata")
        try:
            h = dbx.parse_header(container)
        except dbx.ContainerError as e:
            raise _Fail(422, str(e))
        if not h.flags & dbx.FLAG_ENCRYPTED:
            raise _Fail(422, "not encrypted — refused")
        if h.codec != row["codec"] or h.duration_ms != row["duration_ms"] or dbx.key_id_of(container) != row["key_id"]:
            raise _Fail(422, "header differs from metadata")
        if not dbx.crc_ok(container):
            raise _Fail(422, "crc mismatch")
        self.blobs[mid] = container                     # durable before the 2xx (ADR 0010)
        self.chunks.pop(mid, None)
        row["state"], row["uploaded_at"], row["updated_at"] = "uploaded", _iso(self._wall()), self._wall()
        if row["to"] != "box":
            self.pushes.append({"kind": "message", "to": row["to"], "id": mid, "at": _iso(self._wall())})
        else:
            self.ring()
        return self._json(200, self._wire(row))

    # --- download ----------------------------------------------------------------------------------

    def _audio(self, who, mid, headers):
        row = self.messages.get(mid)
        if not row or row["state"] == "uploading":
            raise _Fail(404, "no such message")
        if who == "box" and not (row["to"] == "box" and row["state"] != "played"):
            raise _Fail(404, "no such message")
        if who != "box" and who not in (row["from"], row["to"]):
            raise _Fail(404, "no such message")
        data = self.blobs[mid]
        rng = headers.get("range")
        start, end = 0, len(data) - 1
        if rng:
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng.strip())
            if not m:
                raise _Fail(416, "bad range")
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else len(data) - 1
            else:
                start = max(0, len(data) - int(m.group(2)))
            if start >= len(data):
                return 416, {"content-range": f"bytes */{len(data)}"}, b""
            end = min(end, len(data) - 1)
        if who == row["to"] and row["state"] == "uploaded" and end == len(data) - 1:
            row["state"], row["delivered_at"], row["updated_at"] = "delivered", _iso(self._wall()), self._wall()
        self.audit.append({"who": who, "action": "audio", "id": mid, "range": [start, end] if rng else None})
        h = {"content-type": "application/octet-stream", "accept-ranges": "bytes"}
        if rng:
            h["content-range"] = f"bytes {start}-{end}/{len(data)}"
        return (206 if rng else 200), h, data[start:end + 1]

    def _played(self, who, mid):
        row = self.messages.get(mid)
        if not row or row["to"] != who or row["state"] == "uploading":
            raise _Fail(404, "no such message")
        if row["state"] != "played":
            now = _iso(self._wall())
            row.update(state="played", played_at=now, delivered_at=row["delivered_at"] or now, updated_at=self._wall())
            self.alerts.pop(f"unplayed_48h:{mid}", None)
            if row["from"] != "box":
                self.pushes.append({"kind": "played", "to": row["from"], "id": mid, "at": now})
        self.audit.append({"who": who, "action": "played", "id": mid})
        return self._json(200, self._wire(row))

    # --- parents -------------------------------------------------------------------------------------

    def _parents_only(self, who):
        if who == "box":
            raise _Fail(403, "parents only")

    def _list(self, who, path):
        self._parents_only(who)
        rows = sorted((r for r in self.messages.values() if r["state"] != "uploading" and who in (r["from"], r["to"])),
                      key=lambda r: (r["updated_at"], r["id"]))
        mine = [r["seq"] for r in self.messages.values() if r["from"] == who]
        return self._json(200, {"messages": [self._wire(r) for r in rows], "cursor": None, "more": False,
                                "max_seq": max(mine) if mine else None})

    def _get_message(self, who, mid):
        self._parents_only(who)
        row = self.messages.get(mid)
        if not row or who not in (row["from"], row["to"]):
            raise _Fail(404, "no such message")
        return self._json(200, self._wire(row))

    def device_status(self) -> Dict[str, Any]:
        return {"telemetry": self.telemetry, "last_checkin_at": _iso(self.last_checkin_at) if self.last_checkin_at else None,
                "late": None if self.next_due_at is None else self._wall() > self.next_due_at,
                "settings": self.settings, "settings_meta": self.settings_meta}

    def _status(self, who):
        self._parents_only(who)
        return self._json(200, self.device_status())

    def _patch_settings(self, who, body):
        self._parents_only(who)
        try:
            patch = json.loads(body)
        except ValueError:
            raise _Fail(400, "body must be a JSON object")
        now = _iso(self._wall())
        before = json.dumps(self.settings, sort_keys=True)
        for k, v in (patch or {}).items():
            if k in ("poll", "quiet_hours"):
                self.settings[k].update(v or {})
                self.settings_meta[k] = {"by": who, "at": now}
            elif k in ("led_brightness", "volume"):
                self.settings[k] = int(v)
                self.settings_meta[k] = {"by": who, "at": now}
            else:
                raise _Fail(403, f"cannot set {k}")
        if json.dumps(self.settings, sort_keys=True) != before:
            self.ring()
        return self._json(200, self.device_status())

    # --- the box ----------------------------------------------------------------------------------------

    def _checkin(self, who, body):
        if who != "box":
            raise _Fail(403, "box only")
        try:
            t = json.loads(body)
        except ValueError:
            t = None
        if not isinstance(t, dict):
            raise _Fail(400, "telemetry must be a JSON object")
        self.telemetry = t
        self.last_checkin_at = self._wall()
        self.next_due_at = self.last_checkin_at + 2 * int(t.get("next_checkin_s") or 60)
        if self.alerts.pop("box_late", None):
            pass
        if isinstance(t.get("fault"), str):
            if not self.alerts.get(f"fault:{t['fault']}"):
                self.alerts[f"fault:{t['fault']}"] = True
                self.pushes.append({"kind": "fault", "to": "parent-a", "fault": t["fault"], "at": _iso(self._wall())})
        else:
            for k in [k for k in self.alerts if k.startswith("fault:")]:
                self.alerts.pop(k)
        pct = t.get("battery_pct")
        if isinstance(pct, int) and pct < 20 and t.get("mains") is False:
            if not self.alerts.get("battery_low"):
                self.alerts["battery_low"] = True
                self.pushes.append({"kind": "battery_low", "to": "parent-a", "battery_pct": pct, "at": _iso(self._wall())})
        elif t.get("mains") is True or (isinstance(pct, int) and pct >= 30):
            self.alerts.pop("battery_low", None)
        inbox = sorted(r["id"] for r in self.messages.values() if r["to"] == "box" and r["state"] in ("uploaded", "delivered"))
        bell = {"url": "sim://doorbell", "topic": self.doorbell_topic} if self.doorbell_topic else None
        return self._json(200, {"settings": self.settings, "inbox": inbox, "doorbell": bell})

    # --- the doorbell: what Realtime does, in-process --------------------------------------------------

    def doorbell_connect(self, url: str, alive: Callable[[], bool] = lambda: True) -> "FakeDoorbellSocket":
        """`alive` is the box's side of the network — the sim passes the fake
        modem's coverage, so a box out of coverage loses its doorbell as a real one would."""
        if self.down or not alive():
            raise ConnectionError("no route (simulated)")
        sock = FakeDoorbellSocket(self, alive)
        with self._lock:
            self.doorbell_sockets.append(sock)
        return sock

    def ring(self) -> None:
        """What `ring_doorbell()` does after commit: an empty broadcast on the topic."""
        with self._lock:
            socks = list(self.doorbell_sockets)
            self.rings_sent += 1
        for sock in socks:
            sock.deliver_ring()

    def tick(self) -> None:
        """What pg_cron does every minute: the box-late alert and unplayed-48h."""
        with self._lock:
            if self.next_due_at is not None and self._wall() > self.next_due_at and not self.alerts.get("box_late"):
                self.alerts["box_late"] = True
                self.pushes.append({"kind": "box_late", "to": "parent-a", "at": _iso(self._wall())})
            elif self.next_due_at is not None and self._wall() <= self.next_due_at:
                self.alerts.pop("box_late", None)
            for r in self.messages.values():
                if (r["to"] == "box" and r["state"] in ("uploaded", "delivered") and r["uploaded_at"]
                        and self._wall() - datetime.fromisoformat(r["uploaded_at"].replace("Z", "+00:00")).timestamp() > 48 * 3600
                        and not self.alerts.get(f"unplayed_48h:{r['id']}")):
                    self.alerts[f"unplayed_48h:{r['id']}"] = True
                    self.pushes.append({"kind": "unplayed_48h", "to": r["from"], "id": r["id"], "at": _iso(self._wall())})

    def _wire(self, row):
        return {k: row[k] for k in ("id", "seq", "from", "to", "created_at", "time_ok", "duration_ms", "codec",
                                    "key_id", "bytes", "state", "uploaded_at", "delivered_at", "played_at")}


class _Fail(Exception):
    def __init__(self, status: int, error: str, **extra):
        super().__init__(error)
        self.status, self.error, self.extra = status, error, extra


class FakeDoorbellSocket:
    """One Realtime connection. Answers joins on the current topic and
    heartbeats; goes silent when the server is down, like a half-open socket."""

    def __init__(self, server: FakeServer, alive: Callable[[], bool] = lambda: True):
        self.server, self.alive = server, alive
        self.inbox: "queue.Queue[str]" = queue.Queue()
        self.topics: set = set()
        self.closed = False

    def send(self, text: str) -> None:
        if self.closed:
            raise ConnectionError("closed")
        if self._silent():
            return                                   # nobody answers: the box must notice by itself
        msg = json.loads(text)
        ev, ref, topic = msg.get("event"), msg.get("ref"), msg.get("topic")
        if ev == "phx_join":
            ok = self.server.doorbell_topic is not None and topic == "realtime:" + self.server.doorbell_topic
            if ok:
                self.topics.add(topic)
            self.inbox.put(json.dumps({"topic": topic, "event": "phx_reply", "ref": ref, "join_ref": ref,
                                       "payload": {"status": "ok" if ok else "error", "response": {}}}))
        elif ev == "heartbeat":
            self.inbox.put(json.dumps({"topic": "phoenix", "event": "phx_reply", "ref": ref,
                                       "payload": {"status": "ok", "response": {}}}))

    def deliver_ring(self) -> None:
        if self._silent() or self.closed or self.server.doorbell_topic is None:
            return
        topic = "realtime:" + self.server.doorbell_topic
        if topic in self.topics:
            self.inbox.put(json.dumps({"topic": topic, "event": "broadcast", "ref": None,
                                       "payload": {"event": "ring", "payload": {}, "type": "broadcast"}}))

    def _silent(self) -> bool:
        return self.server.down or not self.alive()

    def recv(self, timeout: float) -> Optional[str]:
        if self.closed:
            raise ConnectionError("closed")
        try:
            text = self.inbox.get(timeout=max(0.0, timeout))
        except queue.Empty:
            return None
        return None if self._silent() else text          # a half-open socket: what was in flight is lost

    def close(self) -> None:
        self.closed = True
        with self.server._lock:
            if self in self.server.doorbell_sockets:
                self.server.doorbell_sockets.remove(self)


class FakeTransport:
    """`link.Transport` over the in-process server, as one identity."""

    def __init__(self, server: FakeServer, token: str):
        self.server, self.token = server, token
        self.drop_after: Optional[int] = None    # fail every request after this many: a link that drops mid-upload
        self.count = 0

    def request(self, method, path, *, headers=None, body=None):
        self.count += 1
        if self.drop_after is not None and self.count > self.drop_after:
            raise ConnectionError("link dropped (simulated)")
        h = dict(headers or {})
        h["Authorization"] = f"Bearer {self.token}"
        return self.server.handle(method, path, h, body)
