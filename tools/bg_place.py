#!/usr/bin/env python3
"""
Crop the supplied photograph to the prototype's composition.

bg_fit.py matches colour. That is the right tool when the asset IS the
prototype's background, and for assets/card-bg.png it is not — the best any
colour model reached was rms 25/255 against 0.2 for the fitted SVG mesh, and
only by mangling the picture. Different artwork, similar family.

Structure correlation was tried and rejected too: it scores 0.914 by
satisfying "light left, dark right, warm bottom" with a crop that drops the
warm flare altogether, which is the picture's defining feature. Maximising a
similarity number is not the same as choosing a good frame.

So the rule here is plain and explicable: take the largest crop the asset
allows — full height at card aspect, so the least of the picture is discarded
and the least upscaling is needed — then slide it horizontally to put the
flare as close to the prototype's mark as the asset permits. Colour is left
completely alone.

    python3 tools/bg_place.py assets/card-bg.png
"""

import sys, pathlib
import numpy as np
from PIL import Image, ImageFilter

HERE = pathlib.Path(__file__).parent
CARD_W, CARD_H = 558, 438
OUT_SCALE = 2                    # render the embed at 2x card size
SOFTEN = 3                       # px at card scale

# where the prototype puts the warm flare, as a fraction of the card
FLARE_X, FLARE_Y = 0.46, 0.05


def flare_centroid(a):
    """Warmest region of the picture: strongest red-minus-blue."""
    warm = a[:, :, 0] - a[:, :, 2]
    ys, xs = np.where(warm > np.percentile(warm, 99.7))
    return xs.mean(), ys.mean()


def main():
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'assets/card-bg.png')
    if not path.exists():
        sys.exit(f'{path} not found')

    src = Image.open(path).convert('RGB')
    W, H = src.size
    fx, fy = flare_centroid(np.asarray(src).astype(float))
    print(f'  asset {W}x{H}   flare at {fx / W * 100:.1f}% across, '
          f'{fy / H * 100:.1f}% down')

    ar = CARD_W / CARD_H
    w = min(W, int(round(H * ar)))          # full height unless that overflows
    h = min(H, int(round(w / ar)))
    x0 = int(round(np.clip(fx - FLARE_X * w, 0, W - w)))
    y0 = int(round(np.clip(fy - FLARE_Y * h, 0, H - h)))

    at_edge = x0 in (0, W - w)
    print(f'  crop {w} x {h} at ({x0}, {y0})  = {w * h / (W * H) * 100:.0f}% of the asset')
    print(f'  flare lands at {(fx - x0) / w * 100:.1f}% across, '
          f'{(fy - y0) / h * 100:.1f}% down  (prototype: '
          f'{FLARE_X * 100:.0f}%, {FLARE_Y * 100:.0f}%'
          f'{"; horizontally limited by the asset edge" if at_edge else ""})')

    out = src.resize((CARD_W * OUT_SCALE, CARD_H * OUT_SCALE), Image.LANCZOS,
                     box=(x0, y0, x0 + w, y0 + h))
    out = out.filter(ImageFilter.GaussianBlur(SOFTEN * OUT_SCALE))

    dst = HERE / 'card-bg-fitted.webp'
    out.save(dst, 'WEBP', quality=92, method=6)
    print(f'  wrote {dst.name}  {out.size[0]}x{out.size[1]}  '
          f'{dst.stat().st_size / 1024:.0f} KB  (colour left untouched)')


if __name__ == '__main__':
    main()
