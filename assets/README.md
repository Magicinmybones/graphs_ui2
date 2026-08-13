# Card background source

`card-bg.png` is the supplied source photograph. To replace it, regenerate
the fitted card image and rebuild the page:

    python tools/bg_place.py assets/card-bg.png
    python tools/build.py

`bg_place.py` writes `tools/card-bg-fitted.webp`. `build.py` embeds that fitted
image directly into `index.html`; when it is unavailable, the build falls back
to `tools/mesh.svg`.
