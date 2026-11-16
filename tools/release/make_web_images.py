#!/usr/bin/env python3
"""Light display copies for the home page (first screen): 720 px JPEGs under assets/web/.

Only resized (LANCZOS) and re-encoded; no crop, no colour change, EXIF not copied. The page still links to the
untouched original and to the holder's record. Rewrites <img src> in index.html to the light copy and keeps the
original path in data-full. Idempotent.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "web"
PAGES = ["index.html"]
W = 720


def light(src: str) -> str | None:
    p = ROOT / src
    if not p.exists() or p.suffix.lower() not in (".jpg", ".jpeg", ".png") or p.stat().st_size < 90_000:
        return None
    name = re.sub(r"[^a-zA-Z0-9]+", "-", str(Path(src).with_suffix(""))).strip("-")[-90:] + f"-{W}.jpg"
    out = OUT / name
    if not out.exists():
        im = Image.open(p).convert("RGB")
        im.thumbnail((W, W * 2), Image.LANCZOS)
        OUT.mkdir(parents=True, exist_ok=True)
        im.save(out, "JPEG", quality=80, optimize=True, progressive=True)
    return f"assets/web/{name}"


def main() -> None:
    for page in PAGES:
        f = ROOT / page
        s = f.read_text("utf-8")

        def rep(m: re.Match) -> str:
            tag, src = m.group(0), m.group(2)
            if "data-full=" in tag or src.startswith(("http", "assets/web/", "${")):
                return tag
            lt = light(src)
            return tag.replace(m.group(1), f'src="{lt}" data-full="{src}"') if lt else tag
        s2 = re.sub(r'<img\b[^>]*?(src="([^"]+)")[^>]*>', rep, s)
        if s2 != s:
            f.write_text(s2, "utf-8")
        print(page, s2.count("data-full="), "light images")


if __name__ == "__main__":
    main()
