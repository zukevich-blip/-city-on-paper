#!/usr/bin/env python3
"""Cut a historic map into a Leaflet (CRS.Simple) tile pyramid: tiles/<name>/<z>/<x>/<y>.jpg.

z = max_zoom is the native resolution of the source; each lower level halves it. The map is only resampled and cut
(no crop of content, no colour change). Usage: make_tiles.py SRC.jpg OUT_DIR [--max-zoom N]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = 200_000_000
T = 256


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--quality", type=int, default=80)
    a = ap.parse_args()
    im = Image.open(a.src).convert("RGB")
    w, h = im.size
    zmax = math.ceil(math.log2(max(w, h) / T))
    out = Path(a.out)
    n = 0
    for z in range(zmax, -1, -1):
        s = 2 ** (zmax - z)
        lvl = im if s == 1 else im.resize((math.ceil(w / s), math.ceil(h / s)), Image.LANCZOS)
        for x in range(math.ceil(lvl.width / T)):
            for y in range(math.ceil(lvl.height / T)):
                t = lvl.crop((x * T, y * T, min((x + 1) * T, lvl.width), min((y + 1) * T, lvl.height)))
                if t.size != (T, T):  # Leaflet stretches every tile to 256x256: pad edge tiles with the page colour
                    pad = Image.new("RGB", (T, T), (239, 230, 214))
                    pad.paste(t, (0, 0))
                    t = pad
                d = out / str(z) / str(x)
                d.mkdir(parents=True, exist_ok=True)
                t.save(d / f"{y}.jpg", quality=a.quality, optimize=True, progressive=True)
                n += 1
    (out / "tiles.json").write_text(json.dumps({"width": w, "height": h, "tile": T, "max_zoom": zmax}) + "\n")
    print(f"{n} tiles, {w}x{h}, max_zoom {zmax}")


if __name__ == "__main__":
    main()
