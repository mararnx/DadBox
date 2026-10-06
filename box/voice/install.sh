#!/bin/sh
# Install the box's two spoken lines on the Pi (ADR 0024 §10):
#   box/voice/install.sh [host]        (default: dadbox)
# starting.pcm / ready.pcm here are 16 kHz s16le mono, levelled with
#   ffmpeg -af "loudnorm=I=-16:TP=-1.5,volume=0.24,aresample=16000"
# from the WAVs that render.py makes. They go to /usr/local/lib/dadbox/voice
# on the read-only root (through overlayroot-chroot): dadbox-bootvoice plays
# "starting" before /data is even mounted.
set -e
HOST=${1:-dadbox}
cd "$(dirname "$0")"
scp -q starting.pcm ready.pcm nolink.pcm "$HOST:/tmp/"
ssh "$HOST" 'set -e; cd /tmp
  sudo overlayroot-chroot sh -c "mkdir -p /usr/local/lib/dadbox/voice" >/dev/null
  for f in starting ready nolink; do
    sudo overlayroot-chroot sh -c "cat > /usr/local/lib/dadbox/voice/$f.pcm && chmod 644 /usr/local/lib/dadbox/voice/$f.pcm" < $f.pcm >/dev/null 2>&1
  done
  rm -f starting.* ready.* nolink.*
  ls -la /media/root-ro/usr/local/lib/dadbox/voice/'
