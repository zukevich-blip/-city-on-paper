#!/usr/bin/env python3
"""Fetch six official IGN aerial-photo crops and make source-labelled GCP panels.

Uses 6 individual WMS GetMap requests (not OSM scraping). The map-year in
the provider mosaic is UNKNOWN until checked through separate IGN metadata.
The red vector is the model residual, not a historical-image difference.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import shutil
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw

from tools.iiif.render_paris_gcp_review import (
    EARTH,
    ROOT,
    SIDE,
    affine,
    font,
    marker,
    metric,
)

WMS_ENDPOINT = "https://data.geopf.fr/wms-r/wms"
ORTHO_LAYER = "ORTHOIMAGERY.ORTHOPHOTOS"
GEO_SOURCE = ROOT / "data/vision-lab/georef-paris-1878.json"
ATTRIBUTION = "© IGN BD ORTHO, Licence Ouverte / Etalab 2.0; local capture year not established"
MAX_RESPONSE_BYTES = 8_000_000


def wms_getmap_url(lat: float, lon: float, radius_ground_m: float = 400,
                   size: int = 1024) -> str:
    if not (-85 < lat < 85 and -180 < lon < 180):
        raise ValueError("Invalid WGS84 coordinates")
    if not (50 <= radius_ground_m <= 2000 and 256 <= size <= 2048):
        raise ValueError("Unexpected preview scale")
    # EPSG:3857 metre coordinates. Use radius/cos(latitude) so the
    # plotted ground radius remains approximately radius_ground_m.
    mx = EARTH * math.radians(lon)
    my = EARTH * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    d = radius_ground_m / math.cos(math.radians(lat))
    bbox = ",".join(format(v, ".2f") for v in (mx - d, my - d, mx + d, my + d))
    query = urlencode({
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": ORTHO_LAYER, "STYLES": "", "CRS": "EPSG:3857",
        "BBOX": bbox, "WIDTH": size, "HEIGHT": size, "FORMAT": "image/jpeg",
    })
    return WMS_ENDPOINT + "?" + query


def get_ortho(url: str) -> Image.Image:
    if not url.startswith(WMS_ENDPOINT + "?"):
        raise ValueError("Only the official IGN WMS endpoint is permitted")
    req = Request(url, headers={"User-Agent": "CityOnPaperResearch/0.1 (source-verification)"})
    with urlopen(req, timeout=30) as result:
        content_type = result.headers.get("Content-Type", "")
        if not content_type.lower().startswith("image/"):
            raise ValueError("IGN WMS returned a non-image payload: " + content_type)
        payload = result.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("IGN response too large for review-only mode")
    with Image.open(io.BytesIO(payload)) as image:
        if image.width < 256 or image.height < 256:
            raise ValueError("IGN image size is too small for review")
        return image.convert("RGB")


def render(source_dir: Path, destination: Path, fetch=get_ortho, pause=0.5,
           radius_ground_m: float = 400) -> dict:
    old = json.loads((source_dir / "review.json").read_text("utf-8"))
    geo = json.loads(GEO_SOURCE.read_text("utf-8"))
    if old["source"] != "https://www.loc.gov/item/2012586603/":
        raise ValueError("Expected the exact historic LoC Paris 1878 source")
    if len(old["points"]) != 6:
        raise ValueError("Expected exactly six previously validated research records")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_dir / "overview.png", destination / "overview.png")
    result = []
    for n, point in enumerate(old["points"], 1):
        name = point["name"]
        expected = next((g for g in geo["gcps"] if g["name"] == name), None)
        if expected is None:
            raise ValueError("Unexpected point: " + name)
        lat, lon = expected["lat"], expected["lon"]
        url = wms_getmap_url(lat, lon, radius_ground_m)
        ortho = fetch(url)
        if pause:
            time.sleep(pause)
        ortho = ortho.resize((SIDE, SIDE), Image.Resampling.LANCZOS)
        front = ortho.copy()
        marker(ImageDraw.Draw(front), SIDE / 2, SIDE / 2, "#197455")
        difference = ortho.copy()
        dx, dy = affine(expected["px"], expected["py"], geo)
        x, y = metric(lon, lat, geo)
        de, dn = dx - x, dy - y
        ex = SIDE / 2 + de / (2 * radius_ground_m) * SIDE
        ey = SIDE / 2 - dn / (2 * radius_ground_m) * SIDE
        painter = ImageDraw.Draw(difference)
        painter.line((SIDE / 2, SIDE / 2, ex, ey), fill="#b83c43", width=5)
        marker(painter, SIDE / 2, SIDE / 2, "#197455")
        marker(painter, ex, ey, "#b83c43", 7)

        filename = point["file"]
        with Image.open(source_dir / filename) as previous:
            page = previous.convert("RGB")
        page.paste(front, (20 + SIDE + 26, 85))
        page.paste(difference, (20 + 2 * (SIDE + 26), 85))
        d = ImageDraw.Draw(page)
        # Clear the placeholder's "satellite not provided" footer.
        d.rectangle((0, SIDE + 141, page.width, page.height), fill="#fffdf7")
        d.text((20, SIDE + 143), "Аэрофотосъёмка IGN BD ORTHO; дата участка не подтверждена",
               font=font(12), fill="#526272")
        page.save(destination / filename)
        result.append({
            **point,
            "modern_image": "official_IGN_aerial_orthophoto",
            "modern_image_wms_getmap": url,
            "modern_image_license": "Licence Ouverte Etalab 2.0",
            "imagery_capture_year": None,
            "human_review": "still_required",
            "georeferencing_verified": False,
        })
    report = {
        "schema": "city-on-paper/gcp-ign-visual-review/v1",
        "historical_source": old["source"],
        "modern_source": WMS_ENDPOINT,
        "modern_attribution": ATTRIBUTION,
        "all_sources_are_genuine": True,
        "independent_gcp_review": "NOT_DONE",
        "publication_status": "research_only",
        "records": result,
    }
    (destination / "review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    figures = "".join(
        '<figure><img src="' + p["file"] + '" alt="Фрагмент Парижа 1878 и аэрофото IGN">'
        '<figcaption>' + p["name"] + ": " + str(p["model_residual_m"]) +
        " м (остаток модели, не точность карты)</figcaption></figure>"
        for p in result
    )
    webpage = (
        "<!doctype html><html lang='ru'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Париж 1878 / IGN: визуальная проверка</title>"
        "<style>body{max-width:1100px;margin:auto;padding:20px;background:#f7f3ea;"
        "font:16px/1.5 system-ui}img{max-width:100%}figure{background:white;padding:10px}</style>"
        "<h1>Париж 1878 и аэрофотосъёмка IGN</h1>"
        "<p>Оригинальная карта LoC + официальная ортофотосъёмка IGN (Open Licence 2.0)."
        " Год снимка каждого участка ещё не установлен. Пиксели GCP нуждаются в проверке.</p>"
        "<p>Совпадение зелёного и красного маркера не подтверждает правильность исторического"
        " выбора точки: красный вектор показывает только остаток аффинной модели.</p>"
        "<figure><img src='overview.png' alt='15 исследовательских точек на оригинале'></figure>"
        + figures + "</html>"
    )
    (destination / "index.html").write_text(webpage, "utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--radius-m", type=float, default=400)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()
    if not 0 <= args.delay <= 15:
        parser.error("Delay must be between 0 and 15 seconds")
    report = render(args.source, args.out, pause=args.delay, radius_ground_m=args.radius_m)
    print(f"{len(report['records'])} sourced IGN comparisons at {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
