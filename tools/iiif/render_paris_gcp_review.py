#!/usr/bin/env python3
"""Make six review-only triptychs of Paris 1878 GCPs.

Historical image: exact LoC 2012586603, 25-percent IIIF or local copy.
Modern image: optional user-supplied LICENSED north-up Web Mercator raster
with exact WGS84 bounds (west south east north). No satellite image is faked.
The error arrow is affine fit residual, NOT ground truth or photo alignment.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/vision-lab/georef-paris-1878.json"
PICKS = ("Arc de Triomphe", "Obélisque de Louxor", "Colonne Vendôme",
         "Palais Garnier", "Colonne de Juillet", "Cour Carrée du Louvre")
SIDE = 480
EARTH = 6378137.0


def font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)
    except OSError:
        return ImageFont.load_default()


def metric(lon: float, lat: float, doc: dict) -> tuple[float, float]:
    p = doc["local_projection"]
    return ((lon - p["lon0"]) * math.pi / 180 * p["R_m"] * math.cos(math.radians(p["lat0"])),
            (lat - p["lat0"]) * math.pi / 180 * p["R_m"])


def affine(px: float, py: float, doc: dict) -> tuple[float, float]:
    a = doc["transforms"]["affine"]["forward_pixel_to_local_metres"]
    u, v = px / doc["pixel_space"]["width"], py / doc["pixel_space"]["width"]
    east, north = a["coef_X_east_m"], a["coef_Y_north_m"]
    return (east[0] + east[1] * u + east[2] * v, north[0] + north[1] * u + north[2] * v)


def mercator(lat: float) -> float:
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def modern_crop(image: Image.Image, lon: float, lat: float,
                bounds: tuple[float, float, float, float], radius: float) -> Image.Image:
    west, south, east, north = bounds
    if not (-85 < south < north < 85 and west < east):
        raise ValueError("Invalid WGS84 bounds")
    dl = radius / EARTH * 180 / math.pi
    dlon = dl / math.cos(math.radians(lat))

    def xy(lon0: float, lat0: float) -> tuple[float, float]:
        return ((lon0 - west) / (east - west) * image.width,
                (mercator(north) - mercator(lat0))
                / (mercator(north) - mercator(south)) * image.height)

    x1, y1 = xy(lon - dlon, lat + dl)
    x2, y2 = xy(lon + dlon, lat - dl)
    if x1 < 0 or y1 < 0 or x2 > image.width or y2 > image.height:
        raise ValueError("Modern raster does not cover requested landmark window")
    return image.crop((x1, y1, x2, y2)).resize((SIDE, SIDE), Image.Resampling.LANCZOS)


def placeholder() -> Image.Image:
    image = Image.new("RGB", (SIDE, SIDE), "#eef2f6")
    draw = ImageDraw.Draw(image)
    for x in range(0, SIDE, 48):
        draw.line((x, 0, x, SIDE), fill="#d2dce6")
        draw.line((0, x, SIDE, x), fill="#d2dce6")
    draw.text((12, 15), "ГЕОСХЕМА: снимок отсутствует", font=font(15, True), fill="#526272")
    return image


def marker(draw: ImageDraw.ImageDraw, x: float, y: float, color: str, r: int = 10) -> None:
    draw.ellipse((x - r, y - r, x + r, y + r), outline=color, fill="white", width=4)
    draw.line((x - r - 4, y, x + r + 4, y), fill=color, width=2)
    draw.line((x, y - r - 4, x, y + r + 4), fill=color, width=2)


def download_official(doc: dict, out: Path) -> Path:
    service = doc["iiif_service"]
    if not service.startswith("https://tile.loc.gov/image-services/iiif/"):
        raise ValueError("Only the official Library of Congress IIIF Image API is allowed")
    url = service + "/full/pct:25/0/default.jpg"
    req = Request(url, headers={"User-Agent": "CityOnPaperResearch/0.1"})
    with urlopen(req, timeout=40) as response:
        if not response.headers.get("Content-Type", "").startswith("image/"):
            raise ValueError("Expected LoC JPEG")
        data = response.read(25_000_001)
    if len(data) > 25_000_000:
        raise ValueError("Source JPEG exceeds 25 MB")
    dest = out / "paris-1878-official-pct25.jpg"
    dest.write_bytes(data)
    return dest


def generate(doc: dict, historic: Image.Image, out: Path, modern: Image.Image | None = None,
             bounds: tuple[float, float, float, float] | None = None,
             attribution: str | None = None, radius_m: float = 400) -> dict:
    if (modern is None) != (bounds is None):
        raise ValueError("Modern image and WGS84 bounds must be provided together")
    if modern is not None and not attribution:
        raise ValueError("Modern raster requires copyright/source attribution")
    if radius_m <= 0:
        raise ValueError("Radius must be positive")
    out.mkdir(parents=True, exist_ok=True)
    points = doc["gcps"]
    selected = []
    for key in PICKS:
        hits = [p for p in points if p["name"].startswith(key)]
        if len(hits) != 1:
            raise ValueError("Missing or ambiguous GCP: " + key)
        selected.append(hits[0])

    rows = []
    for n, point in enumerate(selected, 1):
        x, y = point["px"], point["py"]
        source_x = x * historic.width / doc["pixel_space"]["width"]
        source_y = y * historic.height / doc["pixel_space"]["height"]
        r = 1100 * historic.width / doc["pixel_space"]["width"]
        old = historic.crop((source_x - r, source_y - r, source_x + r, source_y + r))
        old = old.resize((SIDE, SIDE), Image.Resampling.LANCZOS)
        marker(ImageDraw.Draw(old), SIDE / 2, SIDE / 2, "#b83c43")
        modern_panel = (modern_crop(modern, point["lon"], point["lat"], bounds, radius_m)
                        if modern is not None else placeholder())
        difference = modern_panel.copy()
        actual = metric(point["lon"], point["lat"], doc)
        prediction = affine(x, y, doc)
        east, north = prediction[0] - actual[0], prediction[1] - actual[1]
        error = math.hypot(east, north)
        marker(ImageDraw.Draw(modern_panel), SIDE / 2, SIDE / 2, "#197455")
        d3 = ImageDraw.Draw(difference)
        dx, dy = east / (2 * radius_m) * SIDE, -north / (2 * radius_m) * SIDE
        d3.line((SIDE / 2, SIDE / 2, SIDE / 2 + dx, SIDE / 2 + dy), fill="#b83c43", width=5)
        marker(d3, SIDE / 2, SIDE / 2, "#197455")
        marker(d3, SIDE / 2 + dx, SIDE / 2 + dy, "#b83c43", 7)
        page = Image.new("RGB", (3 * SIDE + 92, SIDE + 160), "#fffdf7")
        d = ImageDraw.Draw(page)
        d.text((20, 16), f"{n}. {point['name']}", font=font(23, True), fill="#263749")
        for k, (label, panel) in enumerate(zip(
            ("Карта 1878: пиксель GCP", "Современная геопозиция", "Остаток модели: зелёная → красная"),
            (old, modern_panel, difference), strict=True,
        )):
            xoff = 20 + k * (SIDE + 26)
            d.text((xoff, 61), label, font=font(15, True), fill="#445466")
            page.paste(panel, (xoff, 85))
        d.text((20, SIDE + 97),
               f"WGS84 {point['lat']:.6f}, {point['lon']:.6f}  |  пиксель {x:.1f}, {y:.1f}",
               font=font(16), fill="#263749")
        d.text((20, SIDE + 122),
               f"Внутренняя ошибка: {error:.1f} м (восток {east:+.1f}, север {north:+.1f}). НЕ GPS-точность.",
               font=font(15, True), fill="#914141")
        if modern is None:
            d.text((20, SIDE + 144), "Спутниковое фото не загружено. Геосхема только для тестов.",
                   font=font(13), fill="#914141")
        filename = f"gcp-{n:02d}.png"
        page.save(out / filename)
        rows.append({"name": point["name"], "pixel": [x, y],
                     "coordinates_lonlat": [point["lon"], point["lat"]],
                     "model_residual_m": round(error, 2),
                     "historic_pick_confidence": point["pick_confidence"],
                     "review_status": "needs_independent_visual_check", "file": filename})

    overview = ImageOps.contain(historic, (1200, 900), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(overview)
    for p in points:
        xx = p["px"] / doc["pixel_space"]["width"] * overview.width
        yy = p["py"] / doc["pixel_space"]["height"] * overview.height
        marker(draw, xx, yy, "#b83c43" if p in selected else "#197455", 6 if p in selected else 3)
    overview.save(out / "overview.png")
    report = {"schema": "city-on-paper/gcp-visual-review/v1",
              "publication_status": "research_only", "human_review": "required",
              "source": "https://www.loc.gov/item/2012586603/",
              "modern_image": attribution or "NOT PROVIDED: diagram only", "points": rows}
    (out / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    figures = "".join(
        f'<figure><img src="{row["file"]}" alt="{html.escape(row["name"])}">'
        f'<figcaption>{html.escape(row["name"])} | {row["model_residual_m"]} м</figcaption></figure>'
        for row in rows
    )
    webpage = ("<!doctype html><html lang='ru'><meta charset='utf-8'>"
               "<meta name='viewport' content='width=device-width,initial-scale=1'>"
               "<title>Paris 1878 GCP research</title>"
               "<style>body{max-width:1100px;margin:auto;padding:20px;background:#f7f3ea;"
               "font:16px/1.5 system-ui}img{max-width:100%}figure{background:white;padding:10px}</style>"
               "<h1>Париж, 1878: проверка опорных точек</h1>"
               "<p>Черновой научный материал. Расхождение модели не подтверждает правильность выбора GCP.</p>"
               f"<p>Современная подложка: {html.escape(attribution or 'не предоставлена')}</p>"
               "<p>Источник карты: <a href='https://www.loc.gov/item/2012586603/'>Library of Congress</a></p>"
               "<figure><img src='overview.png' alt='Исторический план и опорные точки'></figure>"
               + figures + "</html>")
    (out / "index.html").write_text(webpage, "utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--georef", type=Path, default=SOURCE)
    parser.add_argument("--historic-image", type=Path)
    parser.add_argument("--download-loc", action="store_true")
    parser.add_argument("--modern-image", type=Path)
    parser.add_argument("--modern-bounds", type=float, nargs=4, metavar=("W", "S", "E", "N"))
    parser.add_argument("--modern-attribution")
    parser.add_argument("--radius-m", type=float, default=400)
    parser.add_argument("--out", type=Path, default=Path("gcp-review"))
    args = parser.parse_args()
    if bool(args.historic_image) == bool(args.download_loc):
        parser.error("Choose --historic-image OR --download-loc")
    if bool(args.modern_image) != bool(args.modern_bounds):
        parser.error("Modern image requires exact --modern-bounds (W S E N)")
    if args.modern_image and not args.modern_attribution:
        parser.error("--modern-attribution required for licensed modern imagery")
    args.out.mkdir(parents=True, exist_ok=True)
    doc = json.loads(args.georef.read_text("utf-8"))
    path = args.historic_image or download_official(doc, args.out)
    with Image.open(path) as historic:
        old = historic.convert("RGB")
    modern = None
    if args.modern_image:
        with Image.open(args.modern_image) as raster:
            modern = raster.convert("RGB")
    report = generate(doc, old, args.out, modern,
                      tuple(args.modern_bounds) if args.modern_bounds else None,
                      args.modern_attribution, args.radius_m)
    print(f"{len(report['points'])} research sheets at {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
