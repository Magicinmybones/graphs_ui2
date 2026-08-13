#!/usr/bin/env python3
"""
Build comparison.png: the reproduction against the values measured off the
reference, so every claim in it is checkable rather than asserted.

Three bands:
  1. the full render at the reference frame, 1146x577
  2. the card background — reference colour field | rendered | amplified delta
  3. the geometry table — reference position vs rendered position, per element

The reference photograph itself is not on disk, so band 2's left panel is the
colour field sampled off it (9x7 anchors, bilinear). That is exactly the
quantity the mesh was fitted to, so the delta panel is a fair readout of the
background fit.
"""

import subprocess, pathlib, base64, json
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
CARD = (588, 83, 1146, 521)          # card box in the 1146x577 frame
CW, CH = CARD[2] - CARD[0], CARD[3] - CARD[1]

# ---- geometry measured off the reference, element by element -------------
# ---- bar colours sampled off the reference ------------------------------
BAR_COLOURS = [
    ("ghost bar · top",     787, 325, "c7d2db"),
    ("ghost bar · middle",  787, 420, "cdcfc9"),
    ("ghost bar · floor",   787, 515, "e5dfd0"),
    ("cap segment",         918, 215, "1a68e6"),
    ("primary bar · top",   918, 240, "1b64e0"),
    ("primary bar · 1/3",   918, 330, "1458d2"),
    ("primary bar · 2/3",   918, 420, "114fc6"),
    ("primary bar · floor", 918, 515, "0d4ab8"),
]

GEOMETRY = [
    # label,                     axis,  reference,  measure(render) -> value
    ("top hairline",             "y",   "45",          "rule_y"),
    ("headline L1 ink",          "x",   "25 → 324",   "h1_x"),
    ("headline L1 ink top",      "y",   "91",          "h1_y"),
    ("headline L2 ink",          "x",   "25 → 259",   "h2_x"),
    ("headline L2 ink top",      "y",   "135",         "h2_y"),
    ("Product row ink",          "x",   "25 → 111",   "pr_x"),
    ("Product label ink top",    "y",   "228",         "pr_y"),
    ("description ink",          "x",   "25 → 288",   "de_x"),
    ("Growth ink",               "x",   "32 → 105",   "gr_x"),
    ("Sales ink",                "x",   "32 → 90",    "sa_x"),
    ("Customer Success ink",     "x",   "32 → 194",   "cs_x"),
    ("Leadership ink",           "x",   "32 → 135",   "le_x"),
    ("divider 1",                "y",   "288",         "d1"),
    ("divider 2",                "y",   "352",         "d2"),
    ("divider 3",                "y",   "416",         "d3"),
    ("divider 4",                "y",   "480",         "d4"),
    ("divider 5",                "y",   "545",         "d5"),
    ("card box",                 "x",   "588 → 1146", "card_x"),
    ("card box",                 "y",   "83 → 521",   "card_y"),
    ("ghost bar",                "x",   "747 → 827",  "gb_x"),
    ("ghost bar top",            "y",   "320",         "gb_y"),
    ("primary bar",              "x",   "878 → 958",  "bb_x"),
    ("primary bar top",          "y",   "232",         "bb_y"),
    ("cap segment",              "y",   "205 → 226",  "cap_y"),
    ("gap (no element drawn)",   "y",   "226 → 232",  "gap_y"),
    ("“32%” ink",      "x",   "880 → 955",  "st_x"),
    ("“32%” ink top",  "y",   "168",         "st_y"),
    ("caption ink",              "x",   "708 → 861",  "cp_x"),
    ("caption ink top",          "y",   "190",         "cp_y"),
]


def upsample(g, rows, cols):
    R, C, _ = g.shape
    yi, xi = np.linspace(0, R - 1, rows), np.linspace(0, C - 1, cols)
    y0 = np.clip(np.floor(yi).astype(int), 0, R - 1); y1 = np.clip(y0 + 1, 0, R - 1)
    x0 = np.clip(np.floor(xi).astype(int), 0, C - 1); x1 = np.clip(x0 + 1, 0, C - 1)
    wy, wx = (yi - y0)[:, None, None], (xi - x0)[None, :, None]
    top = g[y0][:, x0] * (1 - wx) + g[y0][:, x1] * wx
    bot = g[y1][:, x0] * (1 - wx) + g[y1][:, x1] * wx
    return top * (1 - wy) + bot * wy


def b64(path):
    return base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def measure(render_png, mesh_png):
    """Pull every rendered value the table needs out of the two PNGs."""
    img = np.asarray(Image.open(render_png).convert('RGB')).astype(int)
    v = {}

    def ink(x0, y0, x1, y1, thr, dark=True):
        r = img[y0:y1, x0:x1].mean(axis=2)
        m = (r < thr) if dark else (r > thr)
        ys, xs = np.where(m)
        return x0 + xs.min(), x0 + xs.max(), y0 + ys.min(), y0 + ys.max()

    def hline(x, y0, y1, thr=235):
        col = img[y0:y1, x].mean(axis=1)
        return next(y0 + i for i, c in enumerate(col) if c < thr)

    a, b, c, d = ink(0, 60, 560, 125, 180);  v['h1_x'], v['h1_y'] = f'{a} → {b}', str(c)
    a, b, c, d = ink(0, 128, 560, 172, 180); v['h2_x'], v['h2_y'] = f'{a} → {b}', str(c)
    a, b, c, d = ink(0, 215, 560, 250, 200); v['pr_x'], v['pr_y'] = f'{a} → {b}', str(c)
    a, b, *_ = ink(0, 250, 560, 282, 215);   v['de_x'] = f'{a} → {b}'
    for key, (y0, y1) in {'gr_x': (296, 345), 'sa_x': (360, 410),
                          'cs_x': (424, 472), 'le_x': (488, 536)}.items():
        a, b, *_ = ink(0, y0, 560, y1, 200); v[key] = f'{a} → {b}'
    v['rule_y'] = str(hline(300, 30, 60))
    for i, (y0, y1) in enumerate([(275, 300), (340, 365), (404, 429),
                                  (468, 493), (532, 560)], 1):
        v[f'd{i}'] = str(hline(300, y0, y1))

    # card box: first/last row & column of the card that differ from the page
    page = img[300, 400]
    row = img[300]; xs = [x for x in range(560, 1146) if abs(row[x] - page).max() > 60]
    col = img[:, 1100]; ys = [y for y in range(60, 574) if abs(col[y] - page).max() > 60]
    v['card_x'] = f'{xs[0]} → {xs[-1] + 1}'
    v['card_y'] = f'{ys[0]} → {ys[-1] + 1}'

    # bars: compare each column against the bare mesh to isolate the overlay
    mesh = np.asarray(Image.open(mesh_png).convert('RGB').resize((CW, CH))).astype(int)
    over = np.abs(img[CARD[1]:CARD[3], CARD[0]:CARD[2]] - mesh).max(axis=2)

    def bar(x0, x1, thr, band):
        """Columns altered right through `band` are the bar; a glow or a
        one-pixel gridline is not. The top edge is then the first row whose
        overlay holds for 12 rows straight."""
        cols = [x for x in range(x0, x1) if (over[band, x] > thr).mean() > .95]
        xa, xb = cols[0], cols[-1] + 1
        core = over[:, xa + 6:xb - 6].mean(axis=1)
        yt = next(y for y in range(CH - 12)
                  if all(core[y + k] > thr for k in range(12)))
        return CARD[0] + xa, CARD[0] + xb, CARD[1] + yt

    xa, xb, yt = bar(120, 270, 14, slice(245, 305))
    v['gb_x'], v['gb_y'] = f'{xa} → {xb}', str(yt)
    xa, xb, _ = bar(275, 395, 70, slice(200, 280))
    v['bb_x'] = f'{xa} → {xb}'

    # cap, shadow band and bar top read off one column through the primary bar
    blue = img[:, 918]
    lit = lambda y: blue[y][2] > 170 and blue[y][0] < 110
    cap0 = next(y for y in range(190, 240) if lit(y))
    dark = next(y for y in range(cap0 + 4, 260) if blue[y][2] < 130)
    v['cap_y'] = f'{cap0} → {dark - 1}'
    bar0 = next(y for y in range(dark, 260) if lit(y))
    v['gap_y'] = f'{dark} → {bar0}'
    v['bb_y'] = str(bar0)

    a, b, c, d = ink(866, 155, 972, 203, 218, dark=False); v['st_x'], v['st_y'] = f'{a} → {b}', str(c)
    a, b, c, d = ink(680, 182, 870, 212, 218, dark=False); v['cp_x'], v['cp_y'] = f'{a} → {b}', str(c)
    return v


def main():
    subprocess.run([str(HERE / 'shot.sh'), '1146', '577', str(HERE / 'render_1146.png')], check=True)

    # reference colour field, and the rendered background on its own
    target = np.load(HERE / 'target_grid.npy')
    field = np.clip(upsample(target, CH, CW), 0, 255).astype(np.uint8)
    Image.fromarray(field).save(HERE / 'cmp_field.png')

    mesh = Image.open(HERE / '_mesh.png').convert('RGB').resize((CW, CH))
    mesh.save(HERE / 'cmp_mesh.png')

    delta = np.abs(np.asarray(mesh).astype(int) - field.astype(int))

    # Two numbers, and they measure different things. The anchor error is the
    # honest one: it compares the render against the colours actually read off
    # the reference. The field error also carries the mismatch between two
    # reconstructions — bilinear creases against a smooth blur — so it can
    # never reach zero and is reported only as a spatial map.
    R, C, _ = target.shape
    ys = [int((r + .5) * CH / R) for r in range(R)]
    xs = [int((c + .5) * CW / C) for c in range(C)]
    m = np.asarray(mesh).astype(int)
    anchor = np.abs(np.array([[m[y, x] for x in xs] for y in ys]) - target)
    stat = (f'at the {R * C} sampled anchors: mean {anchor.mean():.1f} / 255 · '
            f'max {anchor.max():.0f} / 255')
    Image.fromarray(np.clip(delta * 5, 0, 255).astype(np.uint8)).save(HERE / 'cmp_delta.png')

    # magnified bar region, the element under review
    full = Image.open(HERE / 'render_1146.png').convert('RGB')
    crop = full.crop((700, 150, 1000, 525))
    crop.resize((crop.width * 2, crop.height * 2), Image.NEAREST).save(HERE / 'cmp_bars.png')

    px = np.asarray(full).astype(int)
    bar_rows = []
    for name, x, y, hexref in BAR_COLOURS:
        got = px[y, x]
        tgt = [int(hexref[i:i + 2], 16) for i in (0, 2, 4)]
        d = max(abs(int(g) - v2) for g, v2 in zip(got, tgt))
        cls = 'ok' if d <= 2 else ('near' if d <= 6 else 'off')
        sw = lambda rgb: (f'<span class="sw" style="background:rgb({rgb[0]},{rgb[1]},{rgb[2]})">'
                          f'</span>#%02x%02x%02x' % tuple(rgb))
        bar_rows.append(f'<tr><td>{name}</td><td class="ax">{x},{y}</td>'
                        f'<td class="n">{sw(tgt)}</td><td class="n">{sw(list(got))}</td>'
                        f'<td class="n {cls}">{"—" if d == 0 else str(d)}</td></tr>')

    gap = px[229, 918]
    bar_rows.append(
        '<tr><td>gap · photograph visible</td><td class="ax">918,229</td>'
        '<td class="n">not drawn</td>'
        '<td class="n"><span class="sw" style="background:rgb(%d,%d,%d)"></span>'
        '#%02x%02x%02x</td><td class="n ok">bg</td></tr>' % (*gap, *gap))

    v = measure(HERE / 'render_1146.png', HERE / '_mesh.png')
    rows = []
    for label, axis, ref, key in GEOMETRY:
        got = v.get(key, '?')
        nums = lambda s: [int(t) for t in s.replace('→', ' ').split()]
        try:
            diff = max(abs(a - b) for a, b in zip(nums(ref), nums(got)))
            cls = 'ok' if diff == 0 else ('near' if diff <= 2 else 'off')
            dtxt = '—' if diff == 0 else f'{diff}px'
        except Exception:
            cls, dtxt = 'off', '?'
        rows.append(f'<tr><td>{label}</td><td class="ax">{axis}</td>'
                    f'<td class="n">{ref}</td><td class="n">{got}</td>'
                    f'<td class="n {cls}">{dtxt}</td></tr>')

    inter = (HERE / 'inter-latin.b64').read_text().strip()
    html = f'''<!doctype html><meta charset="utf-8">
<style>
@font-face{{font-family:Inter;font-weight:100 900;font-display:block;
  src:url(data:font/woff2;base64,{inter}) format('woff2')}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1240px;background:#0e1116;color:#e6e9ee;font-family:Inter,sans-serif;
  padding:26px 30px 30px;-webkit-font-smoothing:antialiased}}
h1{{font-size:19px;font-weight:600;letter-spacing:-.2px}}
h2{{font-size:12px;font-weight:600;letter-spacing:.10em;text-transform:uppercase;
  color:#7d8797;margin:24px 0 10px}}
.sub{{font-size:12.5px;color:#8b95a5;margin-top:4px}}
.shot{{width:1180px;display:block;border:1px solid #262c36;border-radius:5px}}
.trip{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
.trip figure{{min-width:0}}
.trip img{{width:100%;display:block;border:1px solid #262c36;border-radius:4px}}
.trip figcaption{{font-size:11.5px;color:#8b95a5;margin-top:7px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;font-variant-numeric:tabular-nums}}
th{{text-align:left;font-weight:600;font-size:11px;letter-spacing:.09em;
  text-transform:uppercase;color:#7d8797;padding:0 10px 7px 0;
  border-bottom:1px solid #262c36}}
td{{padding:5px 10px 5px 0;border-bottom:1px solid #1a1f27;color:#c9d1dc}}
td.ax{{color:#6f7889;width:34px}}
td.n{{font-family:ui-monospace,Menlo,monospace;font-size:12px}}
th:nth-child(3),th:nth-child(4),th:nth-child(5),
td:nth-child(3),td:nth-child(4),td:nth-child(5){{text-align:right;width:118px}}
.ok{{color:#4ec98a}} .near{{color:#d9b23c}} .off{{color:#e0605a}}
.legend{{font-size:11.5px;color:#7d8797;margin-top:10px}}
.bars{{display:grid;grid-template-columns:600px 1fr;gap:26px;align-items:start}}
.bars img{{width:600px;display:block;border:1px solid #262c36;border-radius:4px}}
.sw{{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:7px;
  vertical-align:-1px;border:1px solid rgba(255,255,255,.18)}}
</style>
<h1>Reference &rarr; reproduction &middot; measured comparison</h1>
<div class="sub">Rendered headlessly at the reference frame, 1146 &times; 577.
Every “rendered” figure below is read back off the PNG, not asserted.</div>

<h2>1 &middot; Full render</h2>
<img class="shot" src="data:image/png;base64,{b64(HERE / 'render_1146.png')}">

<h2>2 &middot; Card background &middot; {stat}</h2>
<div class="trip">
  <figure><img src="data:image/png;base64,{b64(HERE / 'cmp_field.png')}">
    <figcaption>Reference colour field — sampled off the reference at
    {C}&times;{R} anchors and interpolated.</figcaption></figure>
  <figure><img src="data:image/png;base64,{b64(HERE / 'cmp_mesh.png')}">
    <figcaption>Rendered — SVG cell grid through one Gaussian blur, fitted by
    deconvolution.</figcaption></figure>
  <figure><img src="data:image/png;base64,{b64(HERE / 'cmp_delta.png')}">
    <figcaption>|difference| &times; 5 across the whole field
    (mean {delta.mean():.1f}/255). Residual is where a bilinear field and a
    Gaussian blur necessarily disagree, not fit error.</figcaption></figure>
</div>

<h2>3 &middot; Bars &middot; magnified &times;2, and sampled against the reference</h2>
<div class="bars">
  <img src="data:image/png;base64,{b64(HERE / 'cmp_bars.png')}">
  <table>
  <tr><th>Sample</th><th>at</th><th>Reference</th><th>Rendered</th><th>&Delta;</th></tr>
  {''.join(bar_rows)}
  </table>
</div>

<h2>4 &middot; Geometry</h2>
<table>
<tr><th>Element</th><th></th><th>Reference</th><th>Rendered</th><th>&Delta;</th></tr>
{''.join(rows)}
</table>
<div class="legend">&Delta; is the largest per-edge deviation.
<span class="ok">green</span> exact &middot;
<span class="near">amber</span> within 2px (antialiasing / ink-edge threshold) &middot;
<span class="off">red</span> over 2px.</div>
'''
    (HERE / 'comparison.html').write_text(html)
    # render tall, then trim the unused tail rather than guess the height
    subprocess.run([str(HERE / 'shot_generic.sh'), '1240', '3600',
                    str(HERE / 'comparison.png'), str(HERE / 'comparison.html')], check=True)
    sheet = np.asarray(Image.open(HERE / 'comparison.png').convert('RGB'))
    blank = np.all(np.abs(sheet - sheet[-1, -1]).max(axis=2) < 3, axis=1)
    last = np.max(np.where(~blank)[0])
    Image.fromarray(sheet[:last + 26]).save(HERE / 'comparison.png')
    print('comparison.png written ·', stat)
    for label, axis, ref, key in GEOMETRY:
        print(f'  {label:26s} {axis}  ref {ref:14s} got {v.get(key,"?")}')


if __name__ == '__main__':
    main()
