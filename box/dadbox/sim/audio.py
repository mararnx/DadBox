"""Synthetic audio for the simulator: a voice-shaped signal on capture, a real
Opus file on encode when ffmpeg is on the Mac (a WAV otherwise, flagged),
and a playback that takes as long as the message — on the simulated clock.

The capture is the interesting part: it streams to disk at the box's rate and
computes the same block levels the Pi does, so the silence auto-stop, the
5-minute cap and the < 1 s discard are exercised for real. Toggle
`speaking` to make the child fall silent.
"""
from __future__ import annotations

import array
import os
import random
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional, Tuple

from ..clock import Clock
from ..dsp import BLOCK_BYTES, BLOCK_MS, RATE, SPEECH_RMS, rms, synthetic_voice, wav

HAVE_FFMPEG = shutil.which("ffmpeg") is not None


class _FakeCapture:
    def __init__(self, backend: "SimAudio", path: str, on_level, on_end):
        self.b = backend
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._pump, args=(path, on_level, on_end), daemon=True)
        self.thread.start()

    def _pump(self, path, on_level, on_end):
        ok, reason = True, ""
        clock = self.b.clock
        try:
            with open(path, "wb") as f:
                start = clock.now()
                silence_s = 0.0
                pos = 0
                last_sync = start
                while not self._stop.is_set():
                    if self.b.fail_capture:
                        ok, reason = False, "simulated capture failure"
                        break
                    block = self.b.next_block(pos)
                    pos += BLOCK_BYTES
                    f.write(block)
                    now = clock.now()
                    if now - last_sync >= 1.0:
                        f.flush(); os.fsync(f.fileno()); last_sync = now
                    silence_s = silence_s + BLOCK_MS / 1000 if rms(block) < SPEECH_RMS else 0.0
                    on_level(now - start, silence_s)
                    clock.sleep(BLOCK_MS / 1000)
                f.flush(); os.fsync(f.fileno())
        except Exception as e:                       # noqa: BLE001
            ok, reason = False, str(e)
        on_end(ok, reason)

    def stop(self) -> None:
        self._stop.set()


class SimAudio:
    def __init__(self, clock: Clock, voice_wav: Optional[str] = None):
        self.clock = clock
        self.speaking = True                         # the child is talking (else: room tone)
        self.fail_capture = False
        self.playing: Optional[dict] = None          # what the browser can show
        self.voice = self._load(voice_wav) if voice_wav else synthetic_voice(12.0)
        self.encoded_real_opus = HAVE_FFMPEG
        self._stop_play: Optional[threading.Event] = None

    @staticmethod
    def _load(path: str) -> bytes:
        data = Path(path).read_bytes()
        return data[44:] if data[:4] == b"RIFF" else data

    def next_block(self, pos: int) -> bytes:
        if not self.speaking:                          # room tone: a faint hiss, well under SPEECH_RMS
            return array.array("h", (random.randint(-25, 25) for _ in range(BLOCK_BYTES // 2))).tobytes()
        i = pos % len(self.voice)
        block = self.voice[i:i + BLOCK_BYTES]
        return block + self.voice[:BLOCK_BYTES - len(block)] if len(block) < BLOCK_BYTES else block

    def start_capture(self, path, on_level, on_end):
        return _FakeCapture(self, path, on_level, on_end)

    def encode(self, pcm_path: str) -> Tuple[bytes, int]:
        pcm = Path(pcm_path).read_bytes()
        duration_ms = int(len(pcm) / 2 / RATE * 1000)
        if HAVE_FFMPEG:
            out = subprocess.run(
                ["ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", pcm_path,
                 "-c:a", "libopus", "-b:a", "16k", "-application", "voip", "-f", "ogg", "-"],
                capture_output=True, check=True)
            return out.stdout, duration_ms
        return wav(pcm), duration_ms                  # no ffmpeg on this Mac: a WAV labelled as codec 2 (sim only)

    def play(self, audio: bytes, codec: int, volume: int, on_end: Callable[[bool], None]) -> Callable[[], None]:
        duration_s = _duration_s(audio, codec)
        stop = threading.Event()
        self._stop_play = stop
        self.playing = {"audio": audio, "codec": codec, "volume": volume, "started": self.clock.now(), "duration_s": duration_s}

        def run():
            self.clock.wait(stop, duration_s)
            self.playing = None
            on_end(True)
        threading.Thread(target=run, daemon=True).start()
        return stop.set

    def chime(self, volume: int) -> None:
        self.clock.sleep(0.5)


def _duration_s(audio: bytes, codec: int) -> float:
    if audio[:4] == b"RIFF":
        return max(0.5, (len(audio) - 44) / 2 / RATE)
    if HAVE_FFMPEG:
        try:
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", "-"],
                                 input=audio, capture_output=True, timeout=10)
            return max(0.5, float(out.stdout.strip() or 0))
        except Exception:                            # noqa: BLE001
            pass
    return max(0.5, len(audio) / 2000.0)             # ~16 kbps
