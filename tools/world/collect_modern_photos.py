#!/usr/bin/env python3
"""Collect the newest openly licensed modern photographs around known places from Wikimedia Commons.

For every target (a landmark with a search centre) it asks the Commons geosearch for files within a radius,
reads their EXIF date, camera direction (GPSImgDirection) and licence from the file record and keeps only
files that are: JPEG, ≥ 1200 px wide, free licence (CC0 / public domain / CC BY / CC BY-SA), shot in or after 2012.
Nothing is invented: date, author, licence and direction come from the Commons record of the file.
A candidate is NOT an approved comparison: every record says ``needs_review`` until somebody checks, by eye,
that the photo shows the same building and how close its viewpoint is to the old print.

Polite: >= 1 s between calls, stops (``Blocked``) when the server keeps answering 429 instead of writing empty data.

Output: data/curation/modern-photo-candidates-v1.json
"""
from __future__ import annotations

import html
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "curation" / "modern-photo-candidates-v1.json"
API = "https://commons.wikimedia.org/w/api.php"
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
FREE = re.compile(r"^(cc0|public domain|pd\b|pd-|cc by(-sa)? [1-4]\.0|cc by(-sa)? 2\.[05])", re.I)
MIN_YEAR = 2012
MIN_WIDTH = 1200

# Search centres: public landmark coordinates (approximate, used only as a search centre).
_PLACES = [  # (id, name, lat, lon, search radius in metres)
    ("rome-pantheon-vasi", "Пантеон, Рим",
     41.89861, 12.47686, 160),
    ("madeleine-benoist-carnavalet", "Церковь Мадлен, Париж",
     48.87000, 2.32472, 160),
    ("paris-eiffel", "Эйфелева башня, Париж",
     48.85837, 2.29448, 400),
    ("florence-ponte-vecchio", "Понте-Веккьо, Флоренция",
     43.76798, 11.25317, 200),
    ("agra-taj-mahal", "Тадж-Махал, Агра",
     27.17500, 78.04210, 350),
    ("new-york-statue-of-liberty", "Статуя Свободы, Нью-Йорк",
     40.68925, -74.04450, 300),
    ("giza-great-sphinx", "Большой сфинкс, Гиза",
     29.97530, 31.13761, 200),
    ("naples-san-francesco-di-paola", "Сан-Франческо-ди-Паола, Неаполь",
     40.83658, 14.24886, 160),
    ("palais-royal-ph-benoist", "Пале-Рояль, Париж",
     48.86400, 2.33700, 200),
    ("notre-dame-paris", "Нотр-Дам, Париж",
     48.85296, 2.34998, 250),
    ("louvre-colonnade", "Колоннада Лувра, Париж",
     48.86000, 2.33800, 200),
    ("arc-de-triomphe", "Триумфальная арка, Париж",
     48.87380, 2.29500, 250),
    ("vendome-column", "Вандомская колонна, Париж",
     48.86750, 2.32940, 150),
    ("paris-pantheon", "Парижский Пантеон",
     48.84620, 2.34630, 200),
    ("rome-colosseum", "Колизей, Рим",
     41.89021, 12.49223, 300),
    ("venice-st-marks", "Собор Святого Марка, Венеция",
     45.43407, 12.33970, 250),
    ("florence-duomo", "Дуомо, Флоренция",
     43.77310, 11.25590, 250),
    ("saint-petersburg-admiralty", "Адмиралтейство, Санкт-Петербург",
     59.93710, 30.30850, 300),
    ("saint-petersburg-bronze-horseman", "Медный всадник, Санкт-Петербург",
     59.93640, 30.30220, 200),
    ("london-tower-bridge", "Тауэрский мост, Лондон",
     51.50550, -0.07540, 300),
    ("london-st-pauls", "Собор Святого Павла, Лондон",
     51.51380, -0.09840, 250),
    ("moscow-st-basil", "Храм Василия Блаженного, Москва",
     55.75250, 37.62310, 250),
    ("naples-castel-nuovo", "Кастель-Нуово, Неаполь",
     40.83950, 14.25280, 200),
]
TARGETS = [{"id": i, "name": n, "lat": la, "lon": lo, "radius": r} for i, n, la, lo, r in _PLACES]


class Blocked(RuntimeError):
    """The server keeps refusing (429): stop instead of recording empty results."""


def get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    delay = 5.0
    for _attempt in range(6):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)
            time.sleep(1.1)
            return data
        except urllib.error.HTTPError as err:
            if err.code in (429, 503):
                time.sleep(delay)
                delay = min(delay * 2, 90)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise Blocked(url)


def strip_html(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def parse_when(value: str | None) -> str | None:
    """Return an ISO date from an EXIF-like value, or None when it is missing or not a real photo date."""
    m = re.search(r"(\d{4})[-:/.](\d{1,2})[-:/.](\d{1,2})", strip_html(value))
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def rational(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*(?:/\s*(\d+(?:\.\d+)?))?\s*", str(value))
    if not m:
        return None
    num, den = float(m.group(1)), float(m.group(2) or 1)
    return num / den if den else None


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def candidate_from_page(page: dict, target: dict) -> dict | None:
    """Turn one Commons page (geosearch + imageinfo) into a candidate record, or None if it does not qualify."""
    infos = page.get("imageinfo") or []
    coords = page.get("coordinates") or []
    if not infos or not coords:
        return None
    info, c = infos[0], coords[0]
    if info.get("mime") != "image/jpeg" or int(info.get("width") or 0) < MIN_WIDTH:
        return None
    meta = info.get("extmetadata") or {}
    licence = strip_html((meta.get("LicenseShortName") or {}).get("value"))
    if not FREE.match(licence):
        return None
    taken = parse_when((meta.get("DateTimeOriginal") or {}).get("value"))
    if not taken or int(taken[:4]) < MIN_YEAR:
        return None
    exif = {m.get("name"): m.get("value") for m in (info.get("metadata") or []) if isinstance(m, dict)}
    heading = rational(exif.get("GPSImgDirection"))
    if heading is not None and not 0 <= heading <= 360:
        heading = None
    lat, lon = float(c["lat"]), float(c["lon"])
    dist = distance_m(lat, lon, target["lat"], target["lon"])
    to_target = bearing(lat, lon, target["lat"], target["lon"])
    return {
        "file": page.get("title"),
        "page_url": info.get("descriptionurl"),
        "image_url": info.get("url"),
        "thumb_url": info.get("thumburl"),
        "width": int(info.get("width") or 0),
        "height": int(info.get("height") or 0),
        "taken": taken,
        "author": strip_html((meta.get("Artist") or {}).get("value")) or None,
        "licence": licence,
        "licence_url": strip_html((meta.get("LicenseUrl") or {}).get("value")) or None,
        "camera": {"lat": round(lat, 6), "lon": round(lon, 6), "heading_deg": heading,
                   "distance_to_target_m": round(dist), "bearing_to_target_deg": round(to_target),
                   "heading_error_deg": round(angle_diff(heading, to_target)) if heading is not None else None},
        "needs_review": True,
    }


def rank_key(c: dict) -> tuple:
    err = c["camera"]["heading_error_deg"]
    return (c["taken"], 1 if err is not None and err <= 35 else 0, c["width"])


def collect(target: dict, limit: int = 10) -> list[dict]:
    data = get({"action": "query", "generator": "geosearch", "ggscoord": f"{target['lat']}|{target['lon']}",
                "ggsradius": target["radius"], "ggsnamespace": 6, "ggslimit": 100,
                "prop": "coordinates|imageinfo", "coprop": "type", "iiprop": "url|extmetadata|size|mime|metadata",
                "iiurlwidth": 1280})
    pages = (data.get("query") or {}).get("pages") or []
    found = [c for c in (candidate_from_page(p, target) for p in pages) if c]
    found.sort(key=rank_key, reverse=True)
    return found[:limit]


def main(argv: list[str]) -> int:
    only = set(argv[1:])
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"targets": {}}
    targets = {}
    for t in TARGETS:
        if only and t["id"] not in only:
            targets[t["id"]] = existing.get("targets", {}).get(t["id"])
            continue
        try:
            cands = collect(t)
        except Blocked:
            print("blocked by 429, stopping without overwriting existing data", file=sys.stderr)
            return 2
        targets[t["id"]] = {"name": t["name"], "search_centre": [t["lat"], t["lon"]], "radius_m": t["radius"],
                            "candidates": cands}
        print(f"{t['id']}: {len(cands)} candidates", flush=True)
    targets = {k: v for k, v in targets.items() if v}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "version": 1, "source": "Wikimedia Commons geosearch", "min_year": MIN_YEAR, "min_width": MIN_WIDTH,
        "note": "Кандидаты, не подтверждённые сравнения. Дата, автор, лицензия и направление взяты из записи файла.",
        "targets": targets}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
