#!/usr/bin/env python3
"""
Fit the supplied background photograph onto the card.

The asset does not drop straight in: the card shows a crop of it, softened,
and tone-shifted (the asset's flare is #f04a1e where the card's is #d6863f).
So four things are solved at once against colours sampled off the prototype:

    crop rectangle  ·  blur radius  ·  per-channel gain  ·  per-channel bias

Geometry and blur are searched coarse-to-fine. Gain and bias are not searched
— for any candidate crop they have a closed-form least-squares solution, so
they come out exactly and for free at every trial.

Anchors that sit behind a bar are EXCLUDED from the objective. They could
only ever be read off the prototype as "background + bar", so scoring against
them would pull the fit toward the bars' own brightness.

Output is a card-resolution image, already cropped, blurred and tone-matched,
which build.py embeds as base64. Doing the work here rather than with runtime
CSS filters means the browser shows exactly what was fitted.

    python3 bg_fit.py assets/card-bg.png
"""

import sys, pathlib
import numpy as np
from PIL import Image, ImageFilter

HERE = pathlib.Path(__file__).parent
CARD_W, CARD_H = 558, 438
COLS, ROWS = 13, 9
OUT_SCALE = 2                       # render the embed at 2x card size

# same occluders the mesh fit uses, in frame coordinates
OCCLUDERS = [(747, 827, 320, 521), (878, 958, 205, 521)]


def anchors():
    """Anchor pixel positions in card space, and which are usable."""
    cw, ch = CARD_W / COLS, CARD_H / ROWS
    pts, keep = [], []
    for r in range(ROWS):
        for c in range(COLS):
            x, y = (c + .5) * cw, (r + .5) * ch
            hidden = any(x0 - 588 <= x <= x1 - 588 and y0 - 83 <= y <= y1 - 83
                         for x0, x1, y0, y1 in OCCLUDERS)
            pts.append((int(x), int(y)))
            keep.append(not hidden)
    return np.array(pts), np.array(keep)


# Tone is deliberately kept on a short leash. Left free, the solve will
# happily return something like gain 1.46 / bias -102 on the blue channel —
# that is not colour matching, it is destroying the photograph to chase
# anchors it cannot otherwise reach. Clamped, the search instead prefers a
# crop that genuinely resembles the prototype.
GAIN_RANGE = (0.85, 1.15)
BIAS_RANGE = (-25.0, 25.0)


def solve_tone(sample, target):
    """Least-squares gain and bias per channel, clamped to a mild correction."""
    gain = np.zeros(3)
    bias = np.zeros(3)
    for k in range(3):
        A = np.stack([sample[:, k], np.ones(len(sample))], axis=1)
        (g, b), *_ = np.linalg.lstsq(A, target[:, k], rcond=None)
        g = float(np.clip(g, *GAIN_RANGE))
        # re-solve the offset for the clamped gain so the pair stays consistent
        b = float(np.clip(np.mean(target[:, k] - g * sample[:, k]), *BIAS_RANGE))
        gain[k], bias[k] = g, b
    return gain, bias


def place(src, x0, y0, w, blur):
    """Crop, fit to the card, soften."""
    h = w * CARD_H / CARD_W
    box = (x0, y0, x0 + w, y0 + h)
    im = src.resize((CARD_W, CARD_H), Image.LANCZOS, box=box)
    if blur > 0:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im


def score(src, pts, target, x0, y0, w, blur):
    im = place(src, x0, y0, w, blur)
    a = np.asarray(im).astype(float)
    sample = np.array([a[y, x] for x, y in pts])
    gain, bias = solve_tone(sample, target)
    fitted = np.clip(sample * gain + bias, 0, 255)
    return np.sqrt(((fitted - target) ** 2).mean()), (gain, bias)


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: bg_fit.py <background image>')
    path = pathlib.Path(sys.argv[1])
    if not path.exists():
        sys.exit(f'{path} not found — commit the asset and re-run')

    src = Image.open(path).convert('RGB')
    SW, SH = src.size
    print(f'  asset {SW}x{SH}')

    grid = np.load(HERE / 'target_grid.npy')          # 13x9x3, prototype field
    pts, keep = anchors()
    target_all = grid.reshape(-1, 3)
    pts, target = pts[keep], target_all[keep]
    print(f'  scoring against {keep.sum()} unoccluded anchors '
          f'({(~keep).sum()} behind bars, excluded)')

    best = None
    BLUR_MAX = 40

    def trial(x0, y0, w, b):
        nonlocal best
        h = w * CARD_H / CARD_W
        if w < 120 or x0 < 0 or y0 < 0 or x0 + w > SW or y0 + h > SH:
            return
        err, tone = score(src, pts, target, x0, y0, w, b)
        if best is None or err < best[0]:
            best = (err, x0, y0, w, b, tone)

    # coarse sweep — widths include the full asset width so an untouched
    # placement is reachable, and blur includes 0
    for w in sorted({*range(300, SW, 96), SW}):
        for x0 in range(0, max(1, SW - w + 1), 64):
            for y0 in range(0, max(1, SH - int(w * CARD_H / CARD_W) + 1), 64):
                for b in (0, 3, 6, 12, 20, 30):
                    trial(x0, y0, w, b)
    print(f'  coarse   rms {best[0]:5.2f}/255  crop=({best[1]},{best[2]}) '
          f'w={best[3]} blur={best[4]}')

    # refine: every axis narrows together, and blur is searched over a real
    # window each pass rather than nudged by a fixed step
    for span, step in ((48, 12), (12, 3), (3, 1)):
        e, X, Y, W, B, _ = best
        bstep = max(1, step)
        blurs = range(max(0, B - span // 2), min(BLUR_MAX, B + span // 2) + 1, bstep)
        for x0 in range(max(0, X - span), X + span + 1, step):
            for y0 in range(max(0, Y - span), Y + span + 1, step):
                for w in range(W - span * 2, W + span * 2 + 1, step * 2):
                    for b in blurs:
                        trial(x0, y0, w, b)
        print(f'  refine   rms {best[0]:5.2f}/255  crop=({best[1]},{best[2]}) '
              f'w={best[3]} blur={best[4]}')

    err, x0, y0, w, blur, (gain, bias) = best
    print(f'\n  best fit  rms {err:.2f}/255')
    print(f'    crop   x {x0} y {y0}  {w} x {round(w * CARD_H / CARD_W)}')
    print(f'    blur   {blur}px at card scale')
    print(f'    gain   {np.round(gain, 3)}')
    print(f'    bias   {np.round(bias, 1)}')

    # render the embed at OUT_SCALE, applying the same crop/blur/tone
    h = w * CARD_H / CARD_W
    big = src.resize((CARD_W * OUT_SCALE, CARD_H * OUT_SCALE), Image.LANCZOS,
                     box=(x0, y0, x0 + w, y0 + h))
    if blur:
        big = big.filter(ImageFilter.GaussianBlur(blur * OUT_SCALE))
    arr = np.clip(np.asarray(big).astype(float) * gain + bias, 0, 255)
    out = Image.fromarray(arr.astype(np.uint8))

    dst = HERE / 'card-bg-fitted.webp'
    out.save(dst, 'WEBP', quality=92, method=6)
    print(f'  wrote {dst.name}  {out.size[0]}x{out.size[1]}  '
          f'{dst.stat().st_size / 1024:.0f} KB '
          f'(~{dst.stat().st_size * 4 / 3 / 1024:.0f} KB base64)')


if __name__ == '__main__':
    main()
