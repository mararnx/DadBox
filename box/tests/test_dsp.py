"""The speech gate on what the bench mic really does (2026-10-06): after power-up its
output drifts for ~1.5 s, slow and loud; a child at 50 cm is far quieter than that."""
import array
import math
import random

from dadbox.dsp import BLOCK_MS, RATE, SPEECH_LEVEL, level, trim


def _pcm(fn, seconds):
    return array.array("h", (int(max(-32768, min(32767, fn(i / RATE)))) for i in range(int(seconds * RATE)))).tobytes()


def _drift(t):          # 2 Hz swing at -11 dBFS fading out over 1.5 s, as measured
    return 9000 * max(0.0, 1 - t / 1.5) * math.sin(2 * math.pi * 2 * t)


def _quiet_speech(t):   # ~ -62 dBFS: a 220 Hz voice, its energy in the harmonics, with syllables
    syllable = 0.5 + 0.5 * math.sin(2 * math.pi * 4 * t)
    return syllable * sum(25 * math.sin(2 * math.pi * 220 * h * t) for h in (1, 2, 3, 4, 6, 8))


def test_the_power_up_drift_alone_is_not_speech():
    rnd = random.Random(1)
    assert trim(_pcm(lambda t: _drift(t) + rnd.randint(-8, 8), 3.0))[1] == 0


def test_quiet_speech_after_the_drift_is_kept_whole():
    rnd = random.Random(2)
    pcm = _pcm(lambda t: _drift(t) + rnd.randint(-8, 8) + (_quiet_speech(t) if 1.6 <= t < 5.6 else 0), 7.0)
    out, speech_ms = trim(pcm)
    assert speech_ms >= 3800
    start = (len(pcm) - len(out)) / 2  # roughly symmetric pads
    assert len(out) / 2 / RATE >= 4.0 and start >= 0


def test_room_tone_is_under_the_gate_and_speech_over_it():
    rnd = random.Random(3)
    room = _pcm(lambda t: rnd.randint(-8, 8), 0.1)
    assert level(room) < SPEECH_LEVEL < level(_pcm(_quiet_speech, BLOCK_MS / 1000))
