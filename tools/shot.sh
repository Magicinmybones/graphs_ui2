#!/bin/sh
# shot.sh WIDTH HEIGHT OUT
/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell \
  --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --window-size=$1,$2 --screenshot=$3 --virtual-time-budget=4000 \
  --allow-file-access-from-files \
  file:///home/user/graphs_ui2/index.html 2>/dev/null
