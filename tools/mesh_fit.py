#!/usr/bin/env python3
"""
Fit the card's blurred-photograph background.

The reference background is an out-of-focus photo. Reproducing that with
hand-placed radial blobs gives visible blob edges, so instead we model it
the way such an image actually is: a coarse grid of average colours that
has been Gaussian-blurred.

TARGET is that grid, read off the reference at 9x7 cell centres.

Because the blur mixes each cell with its neighbours, feeding TARGET
straight into the blur comes back washed out. So we deconvolve with a
fixed-point loop:

    SRC <- SRC + (TARGET - measure(blur(SRC)))

measure() is a real headless render, so the loop converges against the
browser's actual filter implementation rather than a model of it.
"""

import subprocess, pathlib, sys
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
SHOT = HERE / 'shot_generic.sh'

CARD_W, CARD_H = 558, 438
COLS, ROWS = 13, 9
FINE_COLS, FINE_ROWS = 33, 23      # source grid actually drawn
STD_DEV = 19                       # feGaussianBlur stdDeviation
BLEED = 110                        # border cells extend this far outside

# ---- reference colour field ---------------------------------------------
# Read off the reference at 13x9 cell centres. 13 columns rather than 9 so
# that the navy/haze boundary either side of the primary bar is pinned: it
# falls where the bar hides it, and a coarser grid let the blur bleed the
# navy out across the light half of the card.
TARGET_HEX = [
    # 610     652      695      738      781      824      867      910      953      996     1039     1082     1125  (abs x)
    ['a6b6c4','acb9c1','b2bcbe','b8b8b0','c59468','d6863f','d67c34','9a6440','353d44','182c3e','142a40','12283e','12283e'],  # y=107
    ['9dafbe','a5b4bd','acb8bd','b1babe','b4bbbb','a8a8a4','8a9092','4d565e','1e3145','122940','102840','0f2740','0f2740'],  # y=156
    ['90a3b4','99a9b6','a1aeb6','a7b2b7','abb4b6','a4aaac','7e878c','33465a','1a2f45','0f2740','0e2640','0e2640','102843'],  # y=205
    ['849aac','8fa1af','98a7b0','9fabb1','a5aeb2','a5acae','96a0a2','5a6a76','2a4056','122942','102841','102842','122a45'],  # y=253
    ['7c91a3','869aa8','909fa8','99a5aa','a0aaac','a4acac','a0a8a6','7c8890','3e5266','1c3550','17324d','16314c','15304b'],  # y=302
    ['78899a','82909a','8c9799','969e98','a4a89e','aaaca0','adada0','a8a89a','909288','5a6668','3f5058','344a5c','34495c'],  # y=351
    ['8c9490','9aa096','a8ab9e','b4b4a6','bcbcac','c0bfae','c2c0ae','bcb8a6','a8a494','7c8078','666e6c','5e6a70','5e6a70'],  # y=399
    ['bdb8a6','c8c2ae','d0cab4','d6cfb8','dad3bb','dcd5bd','dbd3bb','d6ceb6','c9c1a9','ada693','a09884','9c9480','9e9682'],  # y=448
    ['d3ccb7','d9d1bb','ddd4bd','e0d7bf','e1d8c0','e0d7bf','ded5bd','dad1b9','d2c9b1','c8bfa5','c6bda3','c8bfa5','cabfa2'],  # y=497
]


# Bars occlude part of the card, so those anchors could only ever be read as
# "background + bar". Using them as background double-counts the bar. Each is
# replaced by a horizontal interpolation of the nearest unoccluded columns in
# its own row — the field is smooth, so that is the best available estimate.
OCCLUDERS = [(747, 827, 320, 521),      # ghost bar
             (878, 958, 205, 521)]      # cap + primary bar


def occluded_mask():
    cw, ch = CARD_W / COLS, CARD_H / ROWS
    m = np.zeros((ROWS, COLS), bool)
    for r in range(ROWS):
        y = 83 + (r + .5) * ch
        for c in range(COLS):
            x = 588 + (c + .5) * cw
            m[r, c] = any(x0 <= x <= x1 and y0 <= y <= y1
                          for x0, x1, y0, y1 in OCCLUDERS)
    return m


def fill_occluded(g, mask):
    """Replace masked cells by linear interpolation across their row."""
    g = g.copy()
    for r in range(g.shape[0]):
        good = np.where(~mask[r])[0]
        for c in np.where(mask[r])[0]:
            lo = good[good < c]
            hi = good[good > c]
            if not len(lo) or not len(hi):          # edge run: nearest value
                g[r, c] = g[r, good[np.argmin(abs(good - c))]]
                continue
            a, b = lo[-1], hi[0]
            t = (c - a) / (b - a)
            g[r, c] = g[r, a] * (1 - t) + g[r, b] * t
    return g


def hexgrid(rows):
    return np.array([[[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in r]
                     for r in rows], dtype=float)


def cell_centres():
    cw, ch = CARD_W / COLS, CARD_H / ROWS
    xs = [int(round((c + .5) * cw)) for c in range(COLS)]
    ys = [int(round((r + .5) * ch)) for r in range(ROWS)]
    return xs, ys


def upsample(g, rows, cols):
    """Bilinear resample of a (R,C,3) grid to (rows,cols,3)."""
    R, C, _ = g.shape
    yi = np.linspace(0, R - 1, rows)
    xi = np.linspace(0, C - 1, cols)
    y0 = np.clip(np.floor(yi).astype(int), 0, R - 1)
    y1 = np.clip(y0 + 1, 0, R - 1)
    x0 = np.clip(np.floor(xi).astype(int), 0, C - 1)
    x1 = np.clip(x0 + 1, 0, C - 1)
    wy = (yi - y0)[:, None, None]
    wx = (xi - x0)[None, :, None]
    top = g[y0][:, x0] * (1 - wx) + g[y0][:, x1] * wx
    bot = g[y1][:, x0] * (1 - wx) + g[y1][:, x1] * wx
    return top * (1 - wy) + bot * wy


def svg_markup(src, indent='      '):
    """Grid of rects + one Gaussian blur == a blurred photograph."""
    rows, cols, _ = src.shape
    cw, ch = CARD_W / cols, CARD_H / rows
    out = []
    for r in range(rows):
        for c in range(cols):
            x, y, w, h = c * cw, r * ch, cw, ch
            if c == 0:            x -= BLEED; w += BLEED
            if c == cols - 1:     w += BLEED
            if r == 0:            y -= BLEED; h += BLEED
            if r == rows - 1:     h += BLEED
            col = '#%02x%02x%02x' % tuple(int(round(v)) for v in src[r, c])
            out.append(f'{indent}<rect x="{x:.2f}" y="{y:.2f}" '
                       f'width="{w:.2f}" height="{h:.2f}" fill="{col}"/>')
    return '\n'.join(out)


def svg_document(src, standalone):
    style = ('style="position:absolute;inset:0;width:100%;height:100%;display:block"'
             if standalone else 'class="mesh"')
    return f'''<svg {style} viewBox="0 0 {CARD_W} {CARD_H}"
     preserveAspectRatio="none" aria-hidden="true" focusable="false">
  <defs>
    <filter id="cardBlur" x="-25%" y="-25%" width="150%" height="150%"
            filterUnits="objectBoundingBox" color-interpolation-filters="sRGB">
      <feGaussianBlur stdDeviation="{STD_DEV}"/>
    </filter>
  </defs>
  <g filter="url(#cardBlur)">
{svg_markup(src)}
  </g>
</svg>'''


def render(src, png):
    html = HERE / '_meshtest.html'
    html.write_text(
        '<!doctype html><meta charset="utf-8">'
        '<style>html,body{margin:0;padding:0;overflow:hidden;background:#000}'
        f'#c{{position:relative;width:{CARD_W}px;height:{CARD_H}px;overflow:hidden}}</style>'
        f'<div id="c">{svg_document(src, True)}</div>')
    subprocess.run([str(SHOT), str(CARD_W), str(CARD_H), str(png), str(html)],
                   check=True, capture_output=True)
    return np.asarray(Image.open(png).convert('RGB')).astype(float)


def main():
    mask = occluded_mask()
    target = fill_occluded(hexgrid(TARGET_HEX), mask)
    print(f'  {int(mask.sum())} occluded anchors replaced by row interpolation')
    xs, ys = cell_centres()
    src = target.copy()

    for it in range(1, 13):
        img = render(upsample(src, FINE_ROWS, FINE_COLS), HERE / '_mesh.png')
        got = np.array([[img[y, x] for x in xs] for y in ys], dtype=float)
        err = target - got
        mx, mean = np.abs(err).max(), np.abs(err).mean()
        print(f'  iter {it:2d}  max |err| = {mx:5.1f}   mean = {mean:4.1f}')
        if mx <= 2.0:
            break
        src = np.clip(src + err * 0.9, 0, 255)

    fine = upsample(src, FINE_ROWS, FINE_COLS)
    (HERE / 'mesh.svg').write_text(svg_document(fine, False))
    np.save(HERE / 'target_grid.npy', target)
    print(f'  wrote mesh.svg  ({FINE_ROWS}x{FINE_COLS} rects, stdDeviation={STD_DEV})')


if __name__ == '__main__':
    main()
