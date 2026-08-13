# Card background asset

Drop the supplied background photograph here as `card-bg.png`
(any of .png/.jpg/.webp works), commit, and run:

    python3 tools/bg_fit.py assets/card-bg.png
    python3 tools/build.py

`bg_fit.py` solves the crop rectangle, blur radius and per-channel
gain/bias that map the asset onto the card, scoring against colours
sampled off the prototype. Anchors hidden behind the bars are excluded
from the objective — read through a bar they carry the bar's own
brightness, not the background's.

It writes `card-bg-fitted.webp` (already cropped, blurred and
tone-matched at 2x card resolution). `build.py` embeds that as base64 and
uses it in place of the fitted SVG colour mesh, which is the fallback
while no asset is present.
