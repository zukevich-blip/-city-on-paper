"""SYNTHETIC test scenes for the alignment POC (no real archive content).

A tiny pinhole renderer draws the same 3-D scene (a flat facade 30 m away and a kiosk
15 m away) from two cameras: an "engraving" style image and a "photo" style image.
Because the 3-D points are known, control points are exact (plus 0.8 px noise) and the
expected verdict is known in advance:

  1. near_identical   - camera barely moved                         -> high
  2. rotation_only    - same position, camera turned/tilted         -> high (homography is exact)
  3. parallax         - camera moved 5 m sideways, two depth planes -> low / viewpoint_mismatch
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1000, 700


def rot(yaw: float, pitch: float) -> np.ndarray:
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    ry = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    return rx @ ry


def projector(cam: dict):
    R, C, f = rot(math.radians(cam["yaw"]), math.radians(cam["pitch"])), np.array(cam["pos"], float), cam["f"]

    def p(X):
        x = R @ (np.asarray(X, float) - C)
        assert x[2] > 0.5, f"point {X} is behind the camera"
        return (W / 2 + f * x[0] / x[2], H / 2 - f * x[1] / x[2])
    return p


def facade_polys():
    polys = [("wall", [(-10, 0, 30), (10, 0, 30), (10, 12, 30), (-10, 12, 30)]),
             ("pediment", [(-10.5, 12, 30), (10.5, 12, 30), (0, 16, 30)]),
             ("cornice", [(-10.5, 11.6, 30), (10.5, 11.6, 30), (10.5, 12.2, 30), (-10.5, 12.2, 30)]),
             ("door", [(-1.4, 0, 30), (1.4, 0, 30), (1.4, 4.5, 30), (-1.4, 4.5, 30)])]
    for col in range(-4, 5):
        if col == 0:
            continue
        x = col * 2.1
        for y in (1.5, 6.5):
            polys.append(("window", [(x - .6, y, 30), (x + .6, y, 30), (x + .6, y + 3, 30), (x - .6, y + 3, 30)]))
    return polys


def kiosk_polys():
    return [("kiosk", [(-7, 0, 15), (-4.5, 0, 15), (-4.5, 6, 15), (-7, 6, 15)]),
            ("kiosk_roof", [(-7.4, 6, 15), (-4.1, 6, 15), (-5.75, 8, 15)])]


CONTROL_3D = {
    "pediment apex": (0, 16, 30), "cornice left": (-10.5, 12.2, 30), "cornice right": (10.5, 12.2, 30),
    "wall base left": (-10, 0, 30), "wall base right": (10, 0, 30), "door top left": (-1.4, 4.5, 30),
    "window r2 top right": (8.4 + .6, 9.5, 30), "kiosk roof apex (15 m)": (-5.75, 8, 15),
    "kiosk base right (15 m)": (-4.5, 0, 15),
}

STYLE = {
    "engraving": {"bg": (236, 226, 204), "wall": (214, 200, 172), "pediment": (205, 190, 160),
                  "cornice": (180, 165, 135), "door": (90, 70, 50), "window": (120, 100, 80),
                  "kiosk": (160, 130, 95), "kiosk_roof": (110, 85, 60), "line": (70, 55, 40)},
    "photo": {"bg": (120, 170, 225), "wall": (222, 214, 196), "pediment": (230, 222, 205),
              "cornice": (200, 192, 176), "door": (40, 35, 35), "window": (60, 80, 100),
              "kiosk": (30, 90, 60), "kiosk_roof": (20, 60, 40), "line": (90, 90, 90)},
}


def render(cam: dict, style: str) -> Image.Image:
    p, s = projector(cam), STYLE[style]
    im = Image.new("RGB", (W, H), s["bg"])
    d = ImageDraw.Draw(im)
    ground = (175, 160, 130) if style == "engraving" else (110, 110, 115)
    d.polygon([p((-60, 0, 200)), p((60, 0, 200)), p((14, 0, 7)), p((-14, 0, 7))], fill=ground)
    for name, poly in facade_polys() + kiosk_polys():  # painter's order: far to near
        d.polygon([p(v) for v in poly], fill=s[name], outline=s["line"])
    if style == "engraving":  # hatching on the sky, like a print
        for y in range(0, H, 6):
            d.line([(0, y), (W, y + 40)], fill=(225, 214, 190), width=1)
        im = im.filter(ImageFilter.SMOOTH)
        d = ImageDraw.Draw(im)
        d.rectangle([4, 4, W - 5, H - 5], outline=(90, 70, 50), width=3)
        d.text((12, H - 22), "SYNTHETIC TEST IMAGE - not a historical work", fill=(90, 70, 50))
    else:
        arr = np.asarray(im).astype(np.int16)
        arr += np.random.default_rng(1).integers(-9, 10, arr.shape, dtype=np.int16)
        im = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
        ImageDraw.Draw(im).text((12, H - 22), "SYNTHETIC TEST PHOTO", fill=(255, 255, 255))
    return im


HIST_CAM = {"pos": (0, 1.7, 0), "yaw": 0, "pitch": 12, "f": 900}
CASES = {
    "synthetic-near-identical": {"pos": (0.15, 1.75, 0.3), "yaw": 0.6, "pitch": 11.5, "f": 905,
                                 "expect": "high", "condition": "near-identical viewpoint"},
    "synthetic-rotation-only": {"pos": (0, 1.7, 0), "yaw": 9, "pitch": 4, "f": 760,
                                "expect": "high", "condition": "partial: same position, camera turned (correctable)"},
    "synthetic-parallax": {"pos": (5.0, 1.7, 3.0), "yaw": -16, "pitch": 12, "f": 900,
                           "expect": "low|viewpoint_mismatch",
                           "condition": "unmatchable: camera moved, two depth planes"},
}


def build(out_dir: Path) -> list[Path]:
    rng = np.random.default_rng(42)
    out_dir.mkdir(parents=True, exist_ok=True)
    hist = render(HIST_CAM, "engraving")
    hist.save(out_dir / "synthetic-historic.jpg", quality=88)
    ph = projector(HIST_CAM)
    paths = []
    for cid, cam in CASES.items():
        render(cam, "photo").save(out_dir / f"{cid}-photo.jpg", quality=85)
        pp = projector(cam)
        cps = []
        for label, X in CONTROL_3D.items():
            a, b = np.array(ph(X)), np.array(pp(X))
            cps.append({"label": label, "historic": (a + rng.normal(0, .8, 2)).round(1).tolist(),
                        "photo": (b + rng.normal(0, .8, 2)).round(1).tolist()})
        pair = {
            "id": cid, "status": "synthetic_test", "condition": cam["condition"], "expected_confidence": cam["expect"],
            "historic": {"title": "Synthetic facade (engraving style)", "file": "synthetic-historic.jpg",
                         "size": [W, H], "credit": "Synthetic test image generated by tools/align/synthetic.py",
                         "rights": "CC0 (generated)", "object_url": None},
            "photo": {"title": f"Synthetic photo - {cam['condition']}", "file": f"{cid}-photo.jpg", "size": [W, H],
                      "credit": "Synthetic test image generated by tools/align/synthetic.py",
                      "rights": "CC0 (generated)"},
            "control_points": cps,
        }
        p = out_dir / f"{cid}.json"
        p.write_text(json.dumps(pair, ensure_ascii=False, indent=1) + "\n", "utf-8")
        paths.append(p)
    return paths


if __name__ == "__main__":
    import sys
    for p in build(Path(sys.argv[1] if len(sys.argv) > 1 else "poc/compare/pairs")):
        print(p)
