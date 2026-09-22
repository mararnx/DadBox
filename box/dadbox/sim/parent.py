"""The parent's phone, as far as the box can tell: sends a message to the box
and reads the thread — through the same routes the iOS app uses, with the
parent's token. Reuses the box's own `link.Client` for the upload, because
the protocol is written as if both ends were boxes (ADR 0003)."""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .. import container as dbx
from ..dsp import RATE, synthetic_voice, wav
from ..ids import ulid
from ..link import Client
from .server import FakeServer


class Parent:
    def __init__(self, server: FakeServer, key: bytes, key_id: int = 1, who: str = "parent-a"):
        self.server, self.key, self.key_id, self.who = server, key, key_id, who
        self.transport = server.transport(who)
        self.client = Client(self.transport)
        self.seq = 0

    def _audio(self, seconds: float, audio: Optional[bytes]) -> bytes:
        if audio is not None:
            return audio
        pcm = synthetic_voice(seconds, seed=7)
        if shutil.which("ffmpeg"):
            out = subprocess.run(["ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", "pipe:0",
                                  "-c:a", "aac", "-b:a", "48k", "-movflags", "+frag_keyframe+empty_moov", "-f", "mp4", "-"],
                                 input=pcm, capture_output=True)
            if out.returncode == 0 and out.stdout:
                return out.stdout
        return wav(pcm)

    def send(self, seconds: float = 8.0, audio: Optional[bytes] = None, *, drop_after: Optional[int] = None) -> str:
        """Record-and-send from the app. Returns the message id."""
        data = self._audio(seconds, audio)
        mid = ulid(self.server._wall())
        duration_ms = int(seconds * 1000)
        sealed = dbx.seal(data, message_id=mid, key=self.key, key_id=self.key_id,
                          codec=dbx.CODEC_AAC_M4A, duration_ms=duration_ms, sample_rate=RATE)
        self.seq += 1
        meta = {"seq": self.seq, "to": "box",
                "created_at": datetime.fromtimestamp(self.server._wall(), timezone.utc).isoformat().replace("+00:00", "Z"),
                "time_ok": True, "duration_ms": duration_ms, "codec": dbx.CODEC_AAC_M4A,
                "key_id": self.key_id, "bytes": len(sealed)}
        self.transport.drop_after = None if drop_after is None else self.transport.count + drop_after
        try:
            self.client.upload(mid, sealed, meta)
        finally:
            self.transport.drop_after = None
        return mid

    def thread(self) -> List[Dict[str, Any]]:
        status, _, body = self.transport.request("GET", "/messages")
        return json.loads(body)["messages"] if status == 200 else []

    def status(self) -> Dict[str, Any]:
        status, _, body = self.transport.request("GET", "/device/status")
        return json.loads(body)

    def settings(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        status, _, body = self.transport.request("PATCH", "/settings", headers={"Content-Type": "application/json"},
                                                 body=json.dumps(patch).encode())
        return json.loads(body)

    def audio(self, mid: str) -> bytes:
        """Fetch and decrypt what the box sent — what the app would play."""
        status, _, body = self.transport.request("GET", f"/messages/{mid}/audio")
        if status != 200:
            raise RuntimeError(f"audio {status}")
        _, audio = dbx.open_(body, message_id=mid, keys={self.key_id: self.key})
        return audio
