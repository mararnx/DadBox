"""The doorbell (ADR 0021, PROTOCOL.md § Doorbell): one thread that holds a
Supabase Realtime channel open and turns a ring into a check-in.

The ring carries nothing, and nothing here decides anything. The worker posts
two kinds of event: `DoorbellState(joined)` and `Ring()`. The core answers a
ring, or a join, with an ordinary check-in through the link worker. So a
doorbell that misbehaves can only make the box check in more often (forged
rings, rate-limited by the core) or less often (lost rings, caught by the
join-time check-in and the backstop timer). It can never lose a message.

"Joined" means the server answered the join `ok` and has answered every
heartbeat since. A heartbeat that goes unanswered for `reply_timeout_s` means
the socket is dead even if TCP says otherwise (LTE sockets die half-open).

The WebSocket client is a small RFC 6455 client on the standard library: text
frames, ping/pong, close. Enough for Phoenix, and no new package on the Pi.
Timing here is real time, not the simulator's clock: heartbeats are about
the network, which does not run at 10x.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import socket
import ssl
import struct
import threading
import time
from typing import Callable, Optional, Protocol, Tuple
from urllib.parse import urlsplit

from .core import DoorbellState, Event, Ring

log = logging.getLogger("dadbox.doorbell")

HEARTBEAT_S = 25.0          # Realtime closes a socket that stops beating; also what holds carrier NAT open
REPLY_TIMEOUT_S = 10.0      # join or heartbeat unanswered this long: the socket is dead
BACKOFF_MIN_S = 5.0
BACKOFF_MAX_S = 300.0
CONNECT_TIMEOUT_S = 15.0
_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class Socket(Protocol):
    def send(self, text: str) -> None: ...

    def recv(self, timeout: float) -> Optional[str]:
        """One text message, or None if none arrived in `timeout` seconds.
        Raises ConnectionError when the socket is closed."""

    def close(self) -> None: ...


Connect = Callable[[str], Socket]


# --- a minimal WebSocket client ------------------------------------------------------------------

class WebSocket:
    """Client side of RFC 6455 over `socket` + `ssl`. Frames from the client
    are masked, as the RFC requires; frames from the server are not."""

    def __init__(self, url: str, timeout: float = CONNECT_TIMEOUT_S):
        u = urlsplit(url)
        if u.scheme not in ("ws", "wss") or not u.hostname:
            raise ConnectionError(f"not a websocket url: {u.scheme}://")
        port = u.port or (443 if u.scheme == "wss" else 80)
        raw = socket.create_connection((u.hostname, port), timeout)
        try:
            if u.scheme == "wss":
                raw = ssl.create_default_context().wrap_socket(raw, server_hostname=u.hostname)
            key = base64.b64encode(os.urandom(16)).decode()
            path = (u.path or "/") + ("?" + u.query if u.query else "")
            host = u.hostname if u.port is None else f"{u.hostname}:{u.port}"
            raw.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
                         f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                         f"Sec-WebSocket-Version: 13\r\nUser-Agent: dadbox\r\n\r\n").encode())
            buf = b""
            while b"\r\n\r\n" not in buf:
                chunk = raw.recv(4096)
                if not chunk:
                    raise ConnectionError("closed during the handshake")
                buf += chunk
                if len(buf) > 16384:
                    raise ConnectionError("handshake too long")
            head, rest = buf.split(b"\r\n\r\n", 1)
            lines = head.decode("latin-1").split("\r\n")
            if len(lines[0].split()) < 2 or lines[0].split()[1] != "101":
                raise ConnectionError(f"handshake refused: {lines[0]}")
            headers = {k.strip().lower(): v.strip() for k, _, v in (ln.partition(":") for ln in lines[1:])}
            want = base64.b64encode(hashlib.sha1((key + _GUID).encode()).digest()).decode()
            if headers.get("sec-websocket-accept") != want:
                raise ConnectionError("handshake: bad Sec-WebSocket-Accept")
        except Exception:
            raw.close()
            raise
        self.sock = raw
        self._buf = rest
        self._frags: list = []
        self._send_lock = threading.Lock()
        self._closed = False

    def send(self, text: str) -> None:
        self._frame(0x1, text.encode())

    def _frame(self, opcode: int, payload: bytes) -> None:
        n = len(payload)
        if n < 126:
            head = struct.pack("!BB", 0x80 | opcode, 0x80 | n)
        elif n < 65536:
            head = struct.pack("!BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            head = struct.pack("!BBQ", 0x80 | opcode, 0x80 | 127, n)
        mask = os.urandom(4)
        body = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        with self._send_lock:
            try:
                self.sock.sendall(head + mask + body)
            except OSError as e:
                raise ConnectionError(f"send failed: {e}") from e

    @staticmethod
    def _parse(buf: bytes) -> Optional[Tuple[bool, int, bytes, bytes]]:
        """(fin, opcode, payload, rest), or None if `buf` holds no whole frame yet."""
        if len(buf) < 2:
            return None
        b0, b1 = buf[0], buf[1]
        n, i = b1 & 0x7F, 2
        if n == 126:
            if len(buf) < 4:
                return None
            n, i = struct.unpack("!H", buf[2:4])[0], 4
        elif n == 127:
            if len(buf) < 10:
                return None
            n, i = struct.unpack("!Q", buf[2:10])[0], 10
        mask = b""
        if b1 & 0x80:                                        # servers do not mask, but tolerate it
            if len(buf) < i + 4:
                return None
            mask, i = buf[i:i + 4], i + 4
        if len(buf) < i + n:
            return None
        payload = buf[i:i + n]
        if mask:
            payload = bytes(b ^ mask[j & 3] for j, b in enumerate(payload))
        return bool(b0 & 0x80), b0 & 0x0F, payload, buf[i + n:]

    def recv(self, timeout: float) -> Optional[str]:
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            if self._closed:
                raise ConnectionError("closed")
            frame = self._parse(self._buf)
            if frame is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self.sock.settimeout(remaining)
                try:
                    chunk = self.sock.recv(65536)
                except (socket.timeout, ssl.SSLWantReadError):
                    return None
                except OSError as e:
                    raise ConnectionError(f"recv failed: {e}") from e
                if not chunk:
                    raise ConnectionError("closed by the server")
                self._buf += chunk
                continue
            fin, op, payload, self._buf = frame
            if op == 0x8:                                    # close: answer and stop
                try:
                    self._frame(0x8, payload[:2])
                except ConnectionError:
                    pass
                self._closed = True
                raise ConnectionError("closed by the server")
            if op == 0x9:
                self._frame(0xA, payload)
                continue
            if op == 0xA:
                continue
            if op in (0x0, 0x1, 0x2):
                self._frags.append(payload)
                if fin:
                    data, self._frags = b"".join(self._frags), []
                    return data.decode("utf-8", "replace")

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                self._frame(0x8, struct.pack("!H", 1000))
            except ConnectionError:
                pass
        try:
            self.sock.close()
        except OSError:
            pass


def connect_ws(url: str) -> Socket:
    return WebSocket(url)


# --- the worker ----------------------------------------------------------------------------------

class DoorbellWorker:
    def __init__(self, *, connect: Optional[Connect], post: Callable[[Event], None],
                 heartbeat_s: float = HEARTBEAT_S, reply_timeout_s: float = REPLY_TIMEOUT_S,
                 backoff_min_s: float = BACKOFF_MIN_S, backoff_max_s: float = BACKOFF_MAX_S):
        self.connect, self.post = connect, post
        self.heartbeat_s, self.reply_timeout_s = heartbeat_s, reply_timeout_s
        self.backoff_min_s, self.backoff_max_s = backoff_min_s, backoff_max_s
        self.simulated_down = False               # `dadboxctl sim link down`: no network, no doorbell
        self.simulated_silent = False             # `dadboxctl sim doorbell silent`: a half-open socket
        self.joined = False
        self.failures = 0
        self.rings = 0
        self._plan: Optional[Tuple[str, str]] = None
        self._changed = threading.Event()
        self._stop = threading.Event()
        self._ref = 0
        self.thread = threading.Thread(target=self._run, name="doorbell", daemon=True)

    def set_plan(self, url: Optional[str], topic: Optional[str]) -> None:
        plan = (url, topic) if url and topic else None
        if plan != self._plan:
            self._plan = plan
            self._changed.set()

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._changed.set()

    def _next_ref(self) -> str:
        self._ref += 1
        return str(self._ref)

    def _run(self) -> None:
        while not self._stop.is_set():
            plan = self._plan
            if plan is None or self.connect is None:
                self._changed.wait(1.0)
                self._changed.clear()
                continue
            self._changed.clear()
            sock: Optional[Socket] = None
            try:
                if self.simulated_down:
                    raise ConnectionError("link down (simulated)")
                sock = self.connect(plan[0])
                self._session(sock, plan)
            except Exception as e:                   # noqa: BLE001 — the doorbell never gives up and never matters
                if not self._stop.is_set() and self._plan == plan:
                    self.failures += 1
                    log.info("doorbell: %s", e)
            finally:
                if sock is not None:
                    sock.close()
                self._set_joined(False)
            if self._stop.is_set():
                break
            if self._plan != plan:
                continue                             # a new address, or closed: no backoff
            delay = min(self.backoff_min_s * 2 ** max(0, self.failures - 1), self.backoff_max_s)
            self._changed.wait(delay)

    def _set_joined(self, joined: bool) -> None:
        if joined != self.joined:
            self.joined = joined
            self.post(DoorbellState(joined))

    def _session(self, sock: Socket, plan: Tuple[str, str]) -> None:
        """Returns when the plan changes or the worker stops; raises when the socket dies."""
        topic = "realtime:" + plan[1]
        join_ref = self._next_ref()
        sock.send(json.dumps({"topic": topic, "event": "phx_join", "ref": join_ref, "join_ref": join_ref,
                              "payload": {"config": {"broadcast": {"self": False, "ack": False},
                                                     "presence": {"key": ""}, "private": False}}}))
        waiting_ref: Optional[str] = join_ref
        deadline = time.monotonic() + self.reply_timeout_s
        next_beat = time.monotonic() + self.heartbeat_s
        while True:
            if self._stop.is_set() or self._plan != plan:
                return
            if self.simulated_down:
                raise ConnectionError("link down (simulated)")
            now = time.monotonic()
            if waiting_ref is not None and now >= deadline:
                raise ConnectionError("join unanswered" if waiting_ref == join_ref else "heartbeat unanswered")
            if now >= next_beat and waiting_ref is None:
                waiting_ref = self._next_ref()
                sock.send(json.dumps({"topic": "phoenix", "event": "heartbeat", "payload": {}, "ref": waiting_ref}))
                deadline, next_beat = now + self.reply_timeout_s, now + self.heartbeat_s
            until = min(next_beat, deadline if waiting_ref is not None else next_beat)
            text = sock.recv(max(0.0, min(until - time.monotonic(), 1.0)))
            if text is None or self.simulated_silent:
                continue
            try:
                msg = json.loads(text)
            except ValueError:
                continue
            if not isinstance(msg, dict):
                continue
            event, payload = msg.get("event"), msg.get("payload") or {}
            if event == "phx_reply" and msg.get("ref") == waiting_ref:
                if not isinstance(payload, dict) or payload.get("status") != "ok":
                    raise ConnectionError(f"refused: {payload}")
                if waiting_ref == join_ref:
                    self.failures = 0
                    self._set_joined(True)
                waiting_ref = None
            elif event == "broadcast" and msg.get("topic") == topic and self.joined:
                if isinstance(payload, dict) and payload.get("event") == "ring":
                    self.rings += 1
                    self.post(Ring())
            elif event in ("phx_error", "phx_close") and msg.get("topic") == topic:
                raise ConnectionError(event)
