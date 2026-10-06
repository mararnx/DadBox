"""Render the box's two spoken lines with Kokoro (ADR 0024 §10).

Kokoro-82M is an open neural TTS model (Apache 2.0, model and voices), run
offline here on a Mac: nothing goes to a speech service, and the audio may
live in this public repo. The box only plays the finished files.

    uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python kokoro-onnx soundfile
    # kokoro-v1.0.onnx and voices-v1.0.bin from
    # https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
    .venv/bin/python box/voice/render.py MODEL_DIR OUT_DIR

espeak-ng truncates long data paths: keep its data at a short path (here
~/.cache/dbx-espeak, copied from the espeakng_loader package). Level the WAVs
into starting.pcm / ready.pcm as box/voice/install.sh says, then run it.
"""
import os
import shutil
import sys

import espeakng_loader
import soundfile as sf
from kokoro_onnx import EspeakConfig, Kokoro

VOICE, LANG = "bm_george", "en-gb"          # chosen by ear on the bench, 2026-10-06
LINES = {
    "starting": "LXMA module is starting up.",   # one word, so the A is the letter, not "uh"
    "ready": "LXMA module is ready to record.",
}

model_dir, out_dir = sys.argv[1], sys.argv[2]
data = os.path.expanduser("~/.cache/dbx-espeak/espeak-ng-data")
if not os.path.isdir(data):
    shutil.copytree(espeakng_loader.get_data_path(), data)
k = Kokoro(os.path.join(model_dir, "kokoro-v1.0.onnx"), os.path.join(model_dir, "voices-v1.0.bin"),
           espeak_config=EspeakConfig(lib_path=espeakng_loader.get_library_path(), data_path=data))
for name, text in LINES.items():
    samples, rate = k.create(text, voice=VOICE, lang=LANG)
    sf.write(os.path.join(out_dir, name + ".wav"), samples, rate)
    print(name, round(len(samples) / rate, 2), "s")
