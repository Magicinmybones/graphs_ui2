"""Assemble the deliverable: template + embedded font + card background + bars.

Everything is inlined, so index.html is a single file that renders with no
network and no sibling assets — which is what the brief asks for.

The card background is the supplied photograph once bg_fit.py has fitted it
(cropped, softened and tone-matched to the prototype, then written as WebP).
The raw asset is deliberately not used directly: it is 1.9 MB, the wrong
aspect ratio for the card, and uncropped. Until a fitted copy exists the page
falls back to the fitted SVG colour mesh, so it always builds.
"""
import base64, pathlib, textwrap

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
FITTED = HERE / 'card-bg-fitted.webp'

page = (HERE / 'page.template.html').read_text(encoding='utf-8')
page = page.replace('__INTER_B64__',
                    (HERE / 'inter-latin.b64').read_text(encoding='utf-8').strip())
page = page.replace('__BARS_CSS__',
                    (HERE / 'bars.css').read_text(encoding='utf-8').strip())

if FITTED.exists():
    b64 = base64.b64encode(FITTED.read_bytes()).decode()
    bg = ('<img class="mesh" alt="" aria-hidden="true" decoding="sync"\n'
          '         src="data:image/webp;base64,' + b64 + '">')
    src = f'fitted photograph ({FITTED.stat().st_size // 1024} KB webp, inlined)'
else:
    bg = textwrap.indent(
        (HERE / 'mesh.svg').read_text(encoding='utf-8').strip(), '    '
    ).lstrip()
    src = 'fitted SVG colour mesh'
page = page.replace('__MESH_SVG__', bg)

(ROOT / 'index.html').write_text(page, encoding='utf-8')
print(f'index.html: {len(page)} bytes   background: {src}')
