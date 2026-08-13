# Card background asset

The supplied background photograph is committed here as `card-bg.png`.
Rebuild the page after replacing it:

    python tools/build.py

`build.py` writes `index.html` with a direct `assets/card-bg.png`
reference. When the asset is absent, it uses the fitted SVG colour mesh
as a fallback so the page still builds.
