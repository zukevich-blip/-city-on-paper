#!/usr/bin/env python3
"""Generate a social-share JPG from genuine Paris Musées Benoist scans.

The three source JPEGs are shipped in book/img/benoist with CC0 Paris Musées
rights and individual source links in book/benoist-sheets.json.
No paintings, inscriptions or landscapes are AI-generated or altered.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1200, 630
INK = "#47211e"
ACCENT = "#6b2724"
GOLD = "#a87944"
CREAM = "#f5ead7"
PAPER = "#eee0ca"

WORKS = (
    ("pm-320291945.jpg", "НОТР-ДАМ"),
    ("pm-320291352.jpg", "ЛУВР"),
    ("pm-320292157.jpg", "ВАНДОМСКАЯ КОЛОННА"),
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"]
    )
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def generate(root: Path) -> Path:
    root = root.resolve()
    source = root / "book" / "img" / "benoist"
    for name, _ in WORKS:
        if not (source / name).is_file():
            raise FileNotFoundError(source / name)
    out = root / "assets" / "share" / "benoist-paris.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)

    random.seed(1845)
    for _ in range(9000):
        x, y = random.randrange(W), random.randrange(H)
        d.point((x, y), fill=random.choice(("#e7d6ba", "#eadcc4", "#e9dac0")))

    d.rectangle((15, 14, W - 16, H - 15), outline=ACCENT, width=2)
    d.rectangle((23, 22, W - 24, H - 23), outline=GOLD, width=1)
    d.rectangle((35, 31, W - 36, 39), fill=ACCENT)

    kicker = "ОНЛАЙН-МУЗЕЙ  ·  ЖИВОЙ ИСТОРИЧЕСКИЙ АТЛАС"
    fk = font(15, True)
    kw = d.textbbox((0, 0), kicker, font=fk)[2]
    d.text(((W - kw) / 2, 34), kicker, font=fk, fill=ACCENT)

    title = "ГОРОД НА БУМАГЕ"
    ft = font(64, True)
    box = d.textbbox((0, 0), title, font=ft)
    d.text(((W - (box[2] - box[0])) / 2, 56), title, font=ft, fill=INK)

    sub = "Париж XIX века · литографии Филиппа Бенуа"
    fs = font(24)
    bb = d.textbbox((0, 0), sub, font=fs)
    d.text(((W - (bb[2] - bb[0])) / 2, 141), sub, font=fs, fill=ACCENT)
    d.line((87, 184, 1113, 184), fill=GOLD, width=2)

    panels = [(80, 197, 330, 510), (391, 197, 809, 510), (870, 197, 1120, 510)]
    for (name, caption), rect in zip(WORKS, panels, strict=True):
        x0, y0, x1, y1 = rect
        d.rectangle((x0 - 7, y0 - 7, x1 + 7, y1 + 5), fill="#f8f0e2", outline=GOLD, width=2)
        src = Image.open(source / name).convert("RGB")
        # Keep genuine scans intact, including their paper margins and inscriptions.
        fit = ImageOps.contain(src, (x1 - x0 - 8, y1 - y0 - 16), Image.Resampling.LANCZOS)
        ix = x0 + (x1 - x0 - fit.width) // 2
        iy = y0 + (y1 - y0 - fit.height) // 2 - 6
        im.paste(fit, (ix, iy))
        label_font = font(15, True)
        tw = d.textbbox((0, 0), caption, font=label_font)[2]
        d.text(((x0 + x1 - tw) / 2, 520), caption, font=label_font, fill=INK)

    d.line((90, 549, 1110, 549), fill=GOLD, width=1)
    detail = "ОТКРЫТЬ ЦИФРОВОЙ МУЗЕЙ  ↗"
    fd = font(22, True)
    tw = d.textbbox((0, 0), detail, font=fd)[2]
    d.text(((W - tw) / 2, 563), detail, font=fd, fill=ACCENT)

    small = "zukevich-blip.github.io/-city-on-paper/"
    ff = font(17)
    tw = d.textbbox((0, 0), small, font=ff)[2]
    d.text(((W - tw) / 2, 598), small, font=ff, fill="#745e4b")

    im.save(out, "JPEG", quality=90, optimize=True, subsampling=0)
    assert Image.open(out).size == (W, H)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(generate(args.root))
