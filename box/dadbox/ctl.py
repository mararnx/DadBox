"""`dadboxctl` — the debug console as a CLI over a Unix socket (DEV-PROCESS.md).

    dadboxctl state | record start|stop | play | inbox | outbox | checkin
              | modem on|off | led test | lock on|off | sim link down|up
              | sim doorbell silent|up

Wire format: one JSON line in — {"argv": [...]} — one JSON line back —
{"reply": "..."}. The socket is `$DADBOX_CTL` or /run/dadbox/ctl.sock.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
from pathlib import Path
from typing import Callable, Tuple

COMMANDS = ("state", "record", "play", "inbox", "outbox", "checkin", "modem", "led", "lock", "sim")
DEFAULT_SOCKET = "/run/dadbox/ctl.sock"


def socket_path() -> str:
    return os.environ.get("DADBOX_CTL", DEFAULT_SOCKET)


def call(argv: Tuple[str, ...], path: str = None) -> str:
    path = path or socket_path()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(60)
        s.connect(path)
        s.sendall(json.dumps({"argv": list(argv)}).encode() + b"\n")
        data = b""
        while not data.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
    return json.loads(data or b"{}").get("reply", "")


class CtlServer:
    def __init__(self, path: str, handler: Callable[[str, Tuple[str, ...]], str]):
        self.path, self.handler = path, handler
        self._stop = threading.Event()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        if os.path.exists(path):
            os.unlink(path)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(path)
        os.chmod(path, 0o660)
        self.sock.listen(4)
        self.sock.settimeout(0.5)
        self.thread = threading.Thread(target=self._run, name="ctl", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()
        self.sock.close()
        if os.path.exists(self.path):
            os.unlink(self.path)

    def _serve(self, conn: socket.socket) -> None:
        with conn:
            f = conn.makefile("rb")
            line = f.readline()
            try:
                argv = json.loads(line or b"{}").get("argv") or ["state"]
                reply = self.handler(argv[0], tuple(argv[1:]))
            except Exception as e:                       # noqa: BLE001
                reply = f"error: {e}"
            conn.sendall(json.dumps({"reply": reply}).encode() + b"\n")


def main() -> int:
    argv = tuple(sys.argv[1:])
    if not argv or argv[0] not in COMMANDS:
        print("usage: dadboxctl " + "|".join(COMMANDS), file=sys.stderr)
        return 2
    try:
        print(call(argv))
    except (FileNotFoundError, ConnectionRefusedError):
        print(f"dadbox is not running (no socket at {socket_path()})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
