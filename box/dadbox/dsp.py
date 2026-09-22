"""Small signal helpers on 16-bit mono PCM. Pure Python, no numpy: a 5-minute
message is 4.8 M samples and this runs on a Cortex-A53 in well under a second
via `audioop`-free integer math on 100 ms blocks."""
from __future__ import annotations

import array
import math
import struct
from typing import List, Tuple

RATE = 16000
BLOCK_MS = 100
BLOCK_SAMPLES = RATE * BLOCK_MS // 1000
BLOCK_BYTES = BLOCK_SAMPLES * 2
SPEECH_RMS = 400            # ~ -38 dBFS: a child talking at 20–60 cm is well above; room tone below. Tune on real recordings.
MIC_SETTLE_MS = 100         # the MEMS mic clicks as its supply comes up: drop it


def rms(pcm: bytes) -> float:
    if len(pcm) < 2:
        return 0.0
    a = array.array("h")
    a.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    return math.sqrt(sum(s * s for s in a) / len(a)) if len(a) else 0.0


def block_levels(pcm: bytes) -> List[float]:
    return [rms(pcm[i:i + BLOCK_BYTES]) for i in range(0, len(pcm), BLOCK_BYTES)]


def trim(pcm: bytes, threshold: float = SPEECH_RMS, pad_ms: int = 200) -> Tuple[bytes, int]:
    """Drop leading and trailing silence. Returns (trimmed pcm, speech_ms) where
    speech_ms is the span between the first and last loud block: under
    MIN_SPEECH_MS the caller discards the recording (ADR 0016)."""
    levels = block_levels(pcm)
    loud = [i for i, l in enumerate(levels) if l >= threshold]
    if not loud:
        return b"", 0
    pad = pad_ms // BLOCK_MS
    first = max(0, loud[0] - pad)
    last = min(len(levels), loud[-1] + 1 + pad)
    out = pcm[first * BLOCK_BYTES:last * BLOCK_BYTES]
    return out, (loud[-1] + 1 - loud[0]) * BLOCK_MS


def wav(pcm: bytes, rate: int = RATE) -> bytes:
    """Wrap raw s16le mono PCM in a WAV header — for the Mac, for ffmpeg, for the simulator."""
    return (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE"
            + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(pcm)) + pcm)


def tone(freq: float, seconds: float, amp: float = 0.3, rate: int = RATE) -> bytes:
    n = int(seconds * rate)
    a = array.array("h", (int(32767 * amp * math.sin(2 * math.pi * freq * i / rate)
                              * min(1.0, (n - i) / (0.02 * rate)) * min(1.0, i / (0.02 * rate)))
                          for i in range(n)))
    return a.tobytes()


def chime_pcm() -> bytes:
    """Two soft notes. Short, gentle, the only sound the box makes unbidden."""
    return tone(660, 0.18, 0.25) + tone(880, 0.28, 0.22)


def synthetic_voice(seconds: float, seed: int = 1, rate: int = RATE) -> bytes:
    """A voice-shaped stand-in for the simulator: a buzzy fundamental with
    syllable-rate amplitude modulation and short pauses. Loud enough to pass
    `trim`, obviously not speech."""
    n = int(seconds * rate)
    out = array.array("h", bytes(2 * n))
    f0 = 180 + (seed % 5) * 30
    for i in range(n):
        t = i / rate
        syllable = 0.55 + 0.45 * math.sin(2 * math.pi * 4.5 * t + seed)
        pause = 0.0 if (t % 3.1) > 2.5 else 1.0          # a breath every ~3 s
        s = 0.35 * syllable * pause * (math.sin(2 * math.pi * f0 * t)
                                       + 0.5 * math.sin(2 * math.pi * 2 * f0 * t)
                                       + 0.25 * math.sin(2 * math.pi * 3 * f0 * t))
        out[i] = int(max(-1.0, min(1.0, s)) * 32767)
    return out.tobytes()
