#!/usr/bin/env python3
"""
Fit the two bars against colours sampled off the reference.

The gap between the cap and the primary bar is a real gap — the photograph
shows through it — so nothing is drawn there and it is not fitted.

The ghost bar is frosted glass, so what lands on screen depends on the
backdrop, which varies from steel-blue at the top to cream at the floor.
Rather than solve the compositing algebra and hope the browser agrees, each
gradient stop is placed exactly at a sampled y and driven by the same
fixed-point loop used for the mesh:

    STOP <- STOP + (TARGET - measure(render(STOP)))

The primary bar and cap are opaque, so they converge immediately; the
translucent ghost bar takes a few passes.
"""

import subprocess, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
CARD_H = 438

# ---- geometry, frame coordinates -> card percentages --------------------
GHOST = dict(x='28.495%', w='14.337%', y0=320, y1=521)
BLUE  = dict(x='51.971%', w='14.337%', y0=232, y1=521)
CAP   = dict(x='51.971%', w='14.337%', y0=205, y1=226)

# ---- colours sampled off the reference ----------------------------------
GHOST_OBS = [(325, 'c7d2db'), (420, 'cdcfc9'), (515, 'e5dfd0')]
BLUE_OBS  = [(240, '1b64e0'), (330, '1458d2'), (420, '114fc6'), (515, '0d4ab8')]
CAP_OBS   = [(215, '1a68e6')]

# alpha profile for the glass: most opaque at the top, falling away toward
# the floor where the bar all but dissolves into the cream
GHOST_ALPHA = [0.58, 0.44, 0.40]

GHOST_X, BLUE_X = 787, 918


def rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def hexs(v):
    return '#%02x%02x%02x' % tuple(int(round(min(255, max(0, x)))) for x in v)


def stops(obs, y0, y1):
    """Gradient stop positions, one exactly at each sampled y."""
    return [(y - y0) / (y1 - y0) * 100 for y, _ in obs]


def css(gstops, bstops, cstop):
    def ramp(pairs, alpha=None):
        out = []
        for i, (pos, c) in enumerate(pairs):
            r, g, b = (int(round(min(255, max(0, v)))) for v in c)
            col = (f'rgba({r},{g},{b},{alpha[i]:.2f})' if alpha
                   else f'rgb({r},{g},{b})')
            out.append(f'{col} {pos:.3f}%')
        return ',\n    '.join(out)

    def box(d):
        top = (d['y0'] - 83) / CARD_H * 100
        return f"left:{d['x']};width:{d['w']};top:{top:.3f}%"

    return f'''/* ---- bars ---------------------------------------------------
   Frame coordinates -> card percentages (card is 558 x 438):
     ghost bar    x 747→827   y 320→521
     cap segment  x 878→958   y 205→226
     gap          x 878→958   y 226→232   nothing drawn: the photograph
                                          shows through it
     primary bar  x 878→958   y 232→521
   Both bars are 80/558 = 14.337% wide.

   Gradient stops sit exactly at the y positions sampled off the reference
   and were fitted by rendering, measuring and correcting, so each stop is
   responsible for one measured colour.
   ------------------------------------------------------------ */

/* Frosted glass. Alpha falls {GHOST_ALPHA[0]:.2f} -> {GHOST_ALPHA[-1]:.2f} down the bar and
   the tint travels cool -> warm, following the backdrop underneath it,
   which runs steel-blue at the top and cream at the floor. */
.bar-ghost{{
  position:absolute;
  {box(GHOST)};bottom:0;
  background:linear-gradient(180deg,
    {ramp(gstops, GHOST_ALPHA)});
  -webkit-backdrop-filter:blur(calc(2*var(--u))) saturate(106%);
  backdrop-filter:blur(calc(2*var(--u))) saturate(106%);
  box-shadow:inset 0 calc(1*var(--u)) 0 rgba(255,255,255,.22),
             inset calc(1*var(--u)) 0 0 rgba(255,255,255,.13);
}}

/* Opaque, and no outer bloom — the reference keeps these edges crisp
   against the photograph. */
.bar-blue{{
  position:absolute;
  {box(BLUE)};bottom:0;
  background:linear-gradient(180deg,
    {ramp(bstops)});
  box-shadow:inset calc(1.2*var(--u)) 0 0 rgba(255,255,255,.10);
}}

.bar-cap{{
  position:absolute;
  {box(CAP)};height:{(CAP['y1'] - CAP['y0']) / CARD_H * 100:.3f}%;
  background:{f'rgb({int(round(cstop[0]))},{int(round(cstop[1]))},{int(round(cstop[2]))})'};
  box-shadow:inset calc(1.2*var(--u)) 0 0 rgba(255,255,255,.12);
}}
'''


def render():
    subprocess.run(['python3', str(HERE / 'build.py')], check=True, capture_output=True)
    subprocess.run([str(HERE / 'shot.sh'), '1146', '577', str(HERE / 'render_1146.png')],
                   check=True, capture_output=True)
    return np.asarray(Image.open(HERE / 'render_1146.png').convert('RGB')).astype(float)


def main():
    gpos = stops(GHOST_OBS, GHOST['y0'], GHOST['y1'])
    bpos = stops(BLUE_OBS, BLUE['y0'], BLUE['y1'])
    gtar = [rgb(h) for _, h in GHOST_OBS]
    btar = [rgb(h) for _, h in BLUE_OBS]
    ctar = rgb(CAP_OBS[0][1])

    g, b, c = [t.copy() for t in gtar], [t.copy() for t in btar], ctar.copy()

    for it in range(1, 11):
        (HERE / 'bars.css').write_text(css(list(zip(gpos, g)), list(zip(bpos, b)), c))
        img = render()

        eg = [gtar[i] - img[y, GHOST_X] for i, (y, _) in enumerate(GHOST_OBS)]
        eb = [btar[i] - img[y, BLUE_X] for i, (y, _) in enumerate(BLUE_OBS)]
        ec = ctar - img[CAP_OBS[0][0], BLUE_X]

        worst = max(max(abs(e).max() for e in eg),
                    max(abs(e).max() for e in eb), abs(ec).max())
        print(f'  iter {it:2d}  worst |err| = {worst:4.1f}   '
              f'ghost {[round(abs(e).max()) for e in eg]}  '
              f'blue {[round(abs(e).max()) for e in eb]}  cap {round(abs(ec).max())}')
        if worst <= 1.0:
            break

        # translucent stops need the correction divided by their alpha
        g = [np.clip(g[i] + eg[i] / GHOST_ALPHA[i], 0, 255) for i in range(len(g))]
        b = [np.clip(b[i] + eb[i], 0, 255) for i in range(len(b))]
        c = np.clip(c + ec, 0, 255)

    print('  ghost stops:', ' '.join(f'{p:.1f}%={hexs(v)}@{a}'
                                     for p, v, a in zip(gpos, g, GHOST_ALPHA)))
    print('  blue  stops:', ' '.join(f'{p:.1f}%={hexs(v)}' for p, v in zip(bpos, b)))
    print('  cap        :', hexs(c))


if __name__ == '__main__':
    main()
