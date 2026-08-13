"""Assemble the deliverable: template + embedded font + card background + bars.

The supplied photograph is served directly from the repository when it exists.
Until then the page falls back to the fitted SVG colour mesh, so it always
builds.
"""
import pathlib, textwrap

HERE = pathlib.Path(__file__).parent
SOURCE = HERE.parent / 'assets' / 'card-bg.png'

page = (HERE / 'page.template.html').read_text(encoding='utf-8')
page = page.replace('__INTER_B64__',
                    (HERE / 'inter-latin.b64').read_text(encoding='utf-8').strip())
page = page.replace('__BARS_CSS__',
                    (HERE / 'bars.css').read_text(encoding='utf-8').strip())

if SOURCE.exists():
    bg = ('<img class="mesh" alt="" aria-hidden="true" decoding="async"\n'
          '         src="assets/card-bg.png">')
    src = f'photograph ({SOURCE.stat().st_size // 1024} KB png)'
else:
    bg = textwrap.indent(
        (HERE / 'mesh.svg').read_text(encoding='utf-8').strip(), '    '
    ).lstrip()
    src = 'fitted SVG colour mesh'
page = page.replace('__MESH_SVG__', bg)

(HERE.parent / 'index.html').write_text(page, encoding='utf-8')
print(f'index.html: {len(page)} bytes   background: {src}')
