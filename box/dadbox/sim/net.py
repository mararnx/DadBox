"""The network between the simulated box and a *real* server (`--real-server`).

The fake server models its own outages; the live Supabase project cannot be
switched off from here. This gate sits between the box and it, so the
simulator's World switches mean the same thing in both modes:

- **coverage off** (the fake modem) or **server down**: every HTTP request
  fails as if there were no route, and the doorbell socket goes silent — a
  half-open socket, exactly like the fake server's. The doorbell worker must
  notice by its own heartbeat, as it would in the field.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

from ..doorbell import Connect, Socket


class Network:
    def __init__(self, modem_up: Callable[[], bool]):
        self.modem_up = modem_up
        self.server_down = False

    def reachable(self) -> bool:
        return self.modem_up() and not self.server_down


class GatedTransport:
    def __init__(self, inner, net: Network):
        self.inner, self.net = inner, net

    def request(self, method: str, path: str, *, headers: Optional[Dict[str, str]] = None, body: Optional[bytes] = None):
        if not self.net.reachable():
            raise ConnectionError("no route to the server (simulated)")
        return self.inner.request(method, path, headers=headers, body=body)


class GatedSocket:
    def __init__(self, inner: Socket, net: Network):
        self.inner, self.net = inner, net

    def send(self, text: str) -> None:
        if self.net.reachable():
            self.inner.send(text)                   # else: lost in the void, as on a half-open socket

    def recv(self, timeout: float) -> Optional[str]:
        text = self.inner.recv(timeout)
        return text if self.net.reachable() else None

    def close(self) -> None:
        self.inner.close()


def gated_connect(inner: Connect, net: Network) -> Connect:
    def connect(url: str) -> Socket:
        if not net.reachable():
            raise ConnectionError("no route to the server (simulated)")
        return GatedSocket(inner(url), net)
    return connect
