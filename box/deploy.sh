#!/bin/sh
# Deploy box/ to the Pi and restart the service:  box/deploy.sh [host]   (default: dadbox)
# Files from the Mac arrive mode 600 in marco's group, and macOS openrsync
# ignores --chmod, so the modes are fixed on the Pi: the service runs as
# `dadbox`, which only reads /data/app through the group.
set -e
HOST=${1:-dadbox}
cd "$(dirname "$0")"
rsync -rt --exclude __pycache__ --exclude '*.pyc' --exclude .pytest_cache --exclude tests \
      --exclude .venv --exclude '*.egg-info' ./ "$HOST:/data/app/"
ssh "$HOST" 'sudo chgrp -R dadbox /data/app && sudo chmod -R u+rwX,g+rX,o-rwx /data/app &&
  sudo systemctl restart dadbox && sleep 8 && systemctl is-active dadbox && dadboxctl state'
