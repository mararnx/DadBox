"""The doorbell worker over the real WebSocket client, against a tiny local
server that speaks just enough Phoenix: join, heartbeat, broadcast, close."""
import base64
import hashlib
import json
import queue
import socket
import struct
import threading
import time

import pytest

from dadbox import core as c
from dadbox.doorbell import DoorbellWorker, WebSocket, connect_ws

TOPIC = "doorbell:0123456789abcdef"
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class PhoenixServer:
    """One thread per client. Frames from the client must be masked (RFC 6455)."""

    def __init__(self):
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen()
        self.port = self.srv.getsockname()[1]
        self.clients = []
        self.answer_heartbeats = True
        self.received = queue.Queue()
        threading.Thread(target=self._accept, daemon=True).start()

    @property
    def url(self):
        return f"ws://127.0.0.1:{self.port}/realtime/v1/websocket?apikey=x&vsn=1.0.0"

    def _accept(self):
        while True:
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn):
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += conn.recv(4096)
        head = buf.split(b"\r\n\r\n")[0].decode()
        key = [ln.split(":", 1)[1].strip() for ln in head.split("\r\n") if ln.lower().startswith("sec-websocket-key")][0]
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        conn.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                      f"Sec-WebSocket-Accept: {accept}\r\n\r\n").encode())
        self.clients.append(conn)
        rest = b""
        while True:
            try:
                while True:
                    frame = WebSocket._parse(rest)
                    if frame:
                        break
                    chunk = conn.recv(65536)
                    if not chunk:
                        return
                    rest += chunk
            except OSError:
                return
            fin, op, payload, rest = frame
            assert rest is not None
            if op == 0x8:
                return
            msg = json.loads(payload)
            self.received.put(msg)
            if msg["event"] == "phx_join":
                ok = msg["topic"] == "realtime:" + TOPIC
                self.send(conn, {"topic": msg["topic"], "event": "phx_reply", "ref": msg["ref"],
                                 "payload": {"status": "ok" if ok else "error", "response": {}}})
            elif msg["event"] == "heartbeat" and self.answer_heartbeats:
                self.send(conn, {"topic": "phoenix", "event": "phx_reply", "ref": msg["ref"],
                                 "payload": {"status": "ok", "response": {}}})

    @staticmethod
    def send(conn, obj):
        data = json.dumps(obj).encode()
        n = len(data)
        head = struct.pack("!BB", 0x81, n) if n < 126 else struct.pack("!BBH", 0x81, 126, n)
        conn.sendall(head + data)

    def ring(self, pad=0):
        for conn in list(self.clients):
            self.send(conn, {"topic": "realtime:" + TOPIC, "event": "broadcast", "ref": None,
                             "payload": {"event": "ring", "payload": {}, "type": "broadcast", "pad": "x" * pad}})

    def drop_all(self):
        for conn in list(self.clients):
            conn.close()
        self.clients.clear()

    def close(self):
        self.srv.close()
        self.drop_all()


@pytest.fixture
def server():
    s = PhoenixServer()
    yield s
    s.close()


def until(cond, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(0.02)
    return False


def worker(events, **kw):
    kw = {"heartbeat_s": 0.2, "reply_timeout_s": 0.3, "backoff_min_s": 0.1, "backoff_max_s": 0.5, **kw}
    w = DoorbellWorker(connect=connect_ws, post=events.put, **kw)
    w.start()
    return w


def drain(events):
    out = []
    while not events.empty():
        out.append(events.get())
    return out


def test_join_heartbeat_and_ring_over_a_real_socket(server):
    events = queue.Queue()
    w = worker(events)
    w.set_plan(server.url, TOPIC)
    try:
        assert until(lambda: w.joined)
        assert until(lambda: any(isinstance(e, c.DoorbellState) and e.joined for e in list(events.queue)))
        join = server.received.get(timeout=1)
        assert join["event"] == "phx_join" and join["payload"]["config"]["private"] is False
        time.sleep(0.5)                                          # a few heartbeats, all answered
        assert w.joined
        server.ring(pad=300)                                     # > 125 bytes: the 16-bit length form
        assert until(lambda: any(isinstance(e, c.Ring) for e in list(events.queue)))
    finally:
        w.stop()


def test_a_wrong_topic_never_joins(server):
    events = queue.Queue()
    w = worker(events)
    w.set_plan(server.url, "doorbell:wrong")
    try:
        time.sleep(0.6)
        assert not w.joined and w.failures >= 1
        assert not [e for e in drain(events) if isinstance(e, c.DoorbellState)]
    finally:
        w.stop()


def test_unanswered_heartbeats_mean_dead_and_it_comes_back(server):
    events = queue.Queue()
    w = worker(events)
    w.set_plan(server.url, TOPIC)
    try:
        assert until(lambda: w.joined)
        server.answer_heartbeats = False                         # half-open: TCP fine, nobody home
        assert until(lambda: not w.joined, timeout=3)
        server.answer_heartbeats = True
        assert until(lambda: w.joined, timeout=3)                # rejoined; the core checks in on the join
        states = [e.joined for e in drain(events) if isinstance(e, c.DoorbellState)]
        assert states[:3] == [True, False, True]
    finally:
        w.stop()


def test_a_dropped_connection_reconnects_and_closing_the_plan_closes_it(server):
    events = queue.Queue()
    w = worker(events)
    w.set_plan(server.url, TOPIC)
    try:
        assert until(lambda: w.joined)
        server.drop_all()
        assert until(lambda: not w.joined, timeout=3)
        assert until(lambda: w.joined, timeout=3)
        w.set_plan(None, None)
        assert until(lambda: not w.joined, timeout=3)
        time.sleep(0.3)
        assert not w.joined
    finally:
        w.stop()


def test_no_server_is_a_backoff_not_a_crash():
    events = queue.Queue()
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()                                                    # nothing listens here
    w = worker(events)
    w.set_plan(f"ws://127.0.0.1:{port}/x", TOPIC)
    try:
        assert until(lambda: w.failures >= 2, timeout=3)
        assert w.thread.is_alive() and not w.joined
    finally:
        w.stop()
