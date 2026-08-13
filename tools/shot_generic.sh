#!/bin/sh
# shot_generic.sh WIDTH HEIGHT OUT FILE
/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell \
  --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --window-size=$1,$2 --screenshot=$3 --virtual-time-budget=4000 \
  "file://$4" 2>/dev/null
