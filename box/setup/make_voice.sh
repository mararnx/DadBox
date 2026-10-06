#!/bin/sh
# Render the box's two spoken lines on a Mac and install them on the Pi
# (ADR 0024 §10). The audio is not committed: it is made with a macOS system
# voice, licensed for personal use, and this repo is public. Run from the Mac:
#   box/setup/make_voice.sh [host]        (default: dadbox)
# Writes /usr/local/lib/dadbox/voice/{starting,ready}.pcm on the Pi's root
# (through overlayroot-chroot): 16 kHz s16le mono, at 48 % of full scale.
set -e
HOST=${1:-dadbox}
VOICE="Reed (English (US))"
T=$(mktemp -d)
say -v "$VOICE" -o "$T/starting.aiff" "L X M A module is starting."
say -v "$VOICE" -o "$T/ready.aiff" "L X M A module is ready to record."
for f in starting ready; do
    afconvert -f WAVE -d LEI16@16000 -c 1 "$T/$f.aiff" "$T/$f.wav"
done
scp -q "$T/starting.wav" "$T/ready.wav" "$HOST:/tmp/"
ssh "$HOST" 'set -e; cd /tmp
  for f in starting ready; do ffmpeg -v error -i $f.wav -af volume=0.48 -ar 16000 -ac 1 -f s16le $f.pcm -y; done
  sudo overlayroot-chroot sh -c "mkdir -p /usr/local/lib/dadbox/voice" >/dev/null
  for f in starting ready; do
    sudo overlayroot-chroot sh -c "cat > /usr/local/lib/dadbox/voice/$f.pcm && chmod 644 /usr/local/lib/dadbox/voice/$f.pcm" < $f.pcm >/dev/null
  done
  rm -f starting.* ready.*
  ls -la /media/root-ro/usr/local/lib/dadbox/voice/'
rm -rf "$T"
