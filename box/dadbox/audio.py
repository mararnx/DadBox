"""The audio worker: capture → trim → Opus → seal → outbox, and inbox → open → play.

Effectful, threaded, and deliberately dumb: it does what the core's actions
say and reports back with events. The codec work is `AudioBackend`'s (ALSA
and ffmpeg on the Pi, synthesis in the simulator); this module owns the
policy that never changes: the container is sealed and **fsynced before
`Queued` is posted**, the raw capture is unlinked only after that, and the
amp is enabled only around playback.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, Optional

from . import container as dbx
from .clock import Clock
from .core import CaptureEnded, CaptureLevel, Discarded, Event, PlaybackEnded, Queued
from .dsp import RATE, trim
from .hal import AmpGate, AudioBackend, CaptureHandle
from .link import iso
from .state import MIN_SPEECH_MS
from .store import Store

log = logging.getLogger("dadbox.audio")


class AudioWorker:
    def __init__(self, *, backend: AudioBackend, amp: AmpGate, store: Store, clock: Clock,
                 post: Callable[[Event], None], key_id: int, keys: Dict[int, bytes]):
        self.backend, self.amp, self.store, self.clock, self.post = backend, amp, store, clock, post
        self.key_id, self.keys = key_id, keys
        self._capture: Optional[CaptureHandle] = None
        self._capture_id: Optional[str] = None
        self._stop_play: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()
        self._chiming = threading.Lock()          # the sound card opens once: chimes never overlap

    # --- capture ------------------------------------------------------------------------

    def start_capture(self, message_id: str, created_at_wall: float, time_ok: bool) -> None:
        path = self.store.begin_capture(message_id, {"created_at": iso(created_at_wall), "time_ok": time_ok})
        mid = message_id

        def on_level(elapsed_s: float, silence_s: float) -> None:
            self.post(CaptureLevel(mid, elapsed_s, silence_s))

        def on_end(ok: bool, reason: str) -> None:
            with self._lock:
                if self._capture_id == mid:
                    self._capture, self._capture_id = None, None
            self.post(CaptureEnded(mid, ok, reason))

        with self._lock:
            self._capture_id = mid
            try:
                self._capture = self.backend.start_capture(str(path), on_level, on_end)
            except Exception as e:                       # noqa: BLE001
                self._capture, self._capture_id = None, None
                self.post(CaptureEnded(mid, False, f"could not start capture: {e}"))

    def stop_capture(self, message_id: str) -> None:
        with self._lock:
            h = self._capture if self._capture_id == message_id else None
        if h is not None:
            h.stop()                                     # the backend calls on_end when the file is closed

    # --- encode + seal + queue ---------------------------------------------------------------

    def encode(self, message_id: str, recovered: bool = False) -> None:
        threading.Thread(target=self._encode, args=(message_id, recovered), name=f"encode-{message_id[-6:]}", daemon=True).start()

    def _encode(self, mid: str, recovered: bool) -> None:
        path = self.store.capture_path(mid)
        info = self.store.capture_info(mid)
        try:
            pcm = path.read_bytes()
            pcm, speech_ms = trim(pcm)
            if speech_ms < MIN_SPEECH_MS:
                self.store.remove_capture(mid)
                self.post(Discarded(mid, f"{speech_ms} ms of speech"))
                return
            trimmed = self.store.tmp_dir() / f"{mid}.pcm"
            trimmed.write_bytes(pcm)
            audio, duration_ms = self.backend.encode(str(trimmed))
            trimmed.unlink(missing_ok=True)
            key = self.keys.get(self.key_id)
            if key is None:
                raise RuntimeError(f"no key {self.key_id} on this box")
            sealed = dbx.seal(audio, message_id=mid, key=key, key_id=self.key_id,
                              codec=dbx.CODEC_OGG_OPUS, duration_ms=duration_ms, sample_rate=RATE)
            meta = {"seq": self.store.next_seq(), "to": "parent-a",
                    "created_at": info.get("created_at") or iso(self.clock.wall()),
                    "time_ok": bool(info.get("time_ok", False)),
                    "duration_ms": duration_ms, "codec": dbx.CODEC_OGG_OPUS,
                    "key_id": self.key_id, "bytes": len(sealed), "recovered": recovered}
            self.store.enqueue(mid, sealed, meta)        # fsync-then-rename: the promise is now kept
            self.store.remove_capture(mid)               # the plaintext leaves the card
            self.post(Queued(mid, len(sealed), duration_ms))
        except Exception as e:                           # noqa: BLE001
            log.exception("encode %s failed", mid)
            self.post(CaptureEnded(mid, False, f"encode failed: {e}"))

    # --- playback --------------------------------------------------------------------------

    def play(self, message_id: str, volume: int) -> None:
        try:
            container = self.store.inbox_container(message_id)
            header, audio = dbx.open_(container, message_id=message_id, keys=self.keys)
        except Exception as e:                           # noqa: BLE001
            log.error("cannot open %s: %s", message_id, e)
            self.post(PlaybackEnded(message_id, ok=False))
            return

        def on_end(ok: bool) -> None:
            self.amp.set(False)
            with self._lock:
                self._stop_play = None
            self.post(PlaybackEnded(message_id, ok))

        if self._chiming.acquire(timeout=3.0):       # let a chime finish; it owns the sound card for ~0.5 s
            self._chiming.release()
        self.amp.set(True)
        try:
            with self._lock:
                self._stop_play = self.backend.play(audio, header.codec, volume, on_end,
                                                    duration_ms=header.duration_ms)
        except Exception as e:                           # noqa: BLE001
            log.error("play %s failed: %s", message_id, e)
            self.amp.set(False)
            self.post(PlaybackEnded(message_id, ok=False))

    def stop_play(self) -> None:
        with self._lock:
            stop = self._stop_play
        if stop:
            stop()

    def chime(self, volume: int, kind: str = "message", wait: bool = False) -> None:
        """`wait`: sound it now and return only when the amp is off again — the
        record-start tone, which must be over before the mic gets power."""
        def run():
            self.amp.set(True)
            try:
                self.backend.chime(volume, kind)
            finally:
                self.amp.set(False)
                self._chiming.release()
        if wait:
            if self._chiming.acquire(timeout=3.0):   # a chime still sounding: let it end first
                run()
            return
        if not self._chiming.acquire(blocking=False):
            return                                   # one is already sounding
        threading.Thread(target=run, name="chime", daemon=True).start()

    def mark_played(self, message_id: str, ok: bool) -> None:
        if ok:
            self.store.inbox_mark(message_id, played=True, played_at=self.clock.wall())
        else:
            self.store.inbox_mark(message_id, broken=True)
