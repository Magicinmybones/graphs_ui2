"""Assemble the deliverable: template + embedded font + card background + bars.

The card background is the supplied photograph when a fitted copy exists
(bg_fit.py produces it, already cropped/blurred/tone-matched, so nothing has
to be recomputed in the browser). Until then it falls back to the fitted SVG
colour mesh, so the page always builds.
"""
import base64, pathlib, textwrap

HERE = pathlib.Path(__file__).parent
FITTED = HERE / 'card-bg-fitted.webp'

page = (HERE / 'page.template.html').read_text()
page = page.replace('__INTER_B64__', (HERE / 'inter-latin.b64').read_text().strip())
page = page.replace('__BARS_CSS__', (HERE / 'bars.css').read_text().strip())

if FITTED.exists():
    b64 = base64.b64encode(FITTED.read_bytes()).decode()
    bg = ('<img class="mesh" alt="" aria-hidden="true" decoding="async"\n'
          '         src="data:image/webp;base64,' + b64 + '">')
    src = f'photograph ({FITTED.stat().st_size // 1024} KB webp)'
else:
    bg = textwrap.indent((HERE / 'mesh.svg').read_text().strip(), '    ').lstrip()
    src = 'fitted SVG colour mesh'
page = page.replace('__MESH_SVG__', bg)

pathlib.Path('/home/user/graphs_ui2/index.html').write_text(page)
print(f'index.html: {len(page)} bytes   background: {src}')
