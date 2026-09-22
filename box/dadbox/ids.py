"""ULIDs, minted at the recording end (PROTOCOL.md § Message object)."""
from __future__ import annotations

import os
import time

_B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid(wall: float | None = None) -> str:
    ms = int((time.time() if wall is None else wall) * 1000)
    n = (ms << 80) | int.from_bytes(os.urandom(10), "big")
    return "".join(_B32[(n >> (5 * i)) & 31] for i in reversed(range(26)))


def is_ulid(s: str) -> bool:
    return len(s) == 26 and all(ch in _B32 for ch in s)
