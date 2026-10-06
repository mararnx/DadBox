"""Small signal helpers on 16-bit mono PCM. Pure Python, no numpy: a 5-minute
message is 4.8 M samples and this runs on a Cortex-A53 in well under a second
via `audioop`-free integer math on 100 ms blocks."""
from __future__ import annotations

import array
import math
import operator
import struct
from typing import List, Tuple

RATE = 16000
BLOCK_MS = 100
BLOCK_SAMPLES = RATE * BLOCK_MS // 1000
BLOCK_BYTES = BLOCK_SAMPLES * 2
SPEECH_LEVEL = 10           # ~ -70 dBFS on `level`. Bench, 2026-10-06, mic in the open: speech at 50 cm
                            # -52 to -66, the room -70 to -85. Set low on purpose: a quiet room kept is
                            # harmless, a quiet child cut is not. Re-measure behind the grille.
MIC_SETTLE_MS = 100         # the MEMS mic clicks as its supply comes up: drop it
SLICE = 32                  # 2 ms: `level` removes each slice's mean and slope, a cheap high-pass
_RAMP = array.array("h", range(SLICE))


def level(pcm: bytes) -> float:
    """Speech-band level: the RMS left after taking each 2 ms slice's own mean
    and slope out, a cheap high-pass. The MEMS mic's output drifts for ~1.5 s
    after power-up (subsonic, up to -11 dBFS, bench 2026-10-06); plain RMS
    reads that drift as speech, this does not. The sums run in C."""
    a = array.array("h")
    a.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    if not a:
        return 0.0
    e = 0.0
    for i in range(0, len(a), SLICE):
        s = a[i:i + SLICE]
        n = len(s)
        t = sum(s)
        e += sum(map(operator.mul, s, s)) - t * t / n
        if n > 2:
            kx = sum(map(operator.mul, _RAMP, s)) - (n - 1) / 2 * t      # sum of (k - mean k) * x
            e -= kx * kx / (n * (n * n - 1) / 12)                       # / sum of (k - mean k)^2
    return math.sqrt(max(e, 0.0) / len(a))


def block_levels(pcm: bytes) -> List[float]:
    return [level(pcm[i:i + BLOCK_BYTES]) for i in range(0, len(pcm), BLOCK_BYTES)]


def trim(pcm: bytes, threshold: float = SPEECH_LEVEL, pad_ms: int = 200) -> Tuple[bytes, int]:
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


def chime_pcm(kind: str = "message") -> bytes:
    """The box's few sounds. "message": two soft notes, the only sound it makes
    unbidden. "record_start": a quick rising blip before the mic comes on.
    "record_end": a falling "done" after the mic is off."""
    if kind == "record_start":
        return tone(523, 0.06, 0.22) + tone(659, 0.06, 0.22) + tone(784, 0.10, 0.22)
    if kind == "record_end":
        return tone(784, 0.09, 0.22) + tone(523, 0.16, 0.2)
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
