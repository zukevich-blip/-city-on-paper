#!/usr/bin/env python3
"""Licensed contemporary city-photo discovery via Wikimedia Commons file records.

Date of file upload is NOT assumed to be the date of the photograph. No alleged
same-viewpoint historic/modern pairs are created by this discovery pipeline.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

API = "https://commons.wikimedia.org/w/api.php"
UA = "CityOnPaperMuseum/1.0 (single image credit per asset; https://github.com/zukevich-blip/-city-on-paper)"
QUERIES = (
    ("Париж", "Paris Notre Dame cathedral photo"),
    ("Париж", "Paris Madeleine church exterior"),
    ("Париж", "Paris Louvre courtyard photograph"),
    ("Париж", "Paris Les Halles 2020 photograph"),
    ("Венеция", "Venice Grand Canal 2020"),
    ("Венеция", "Piazza San Marco Venice photograph"),
    ("Рим", "Rome Colosseum 2020"),
    ("Рим", "Pantheon Rome facade photo"),
    ("Флоренция", "Ponte Vecchio Florence 2020"),
    ("Флоренция", "Florence Duomo square photograph"),
    ("Лондон", "London Westminster Bridge Thames"),
    ("Амстердам", "Amsterdam canals city photography"),
    ("Прага", "Prague Charles bridge 2020 photo"),
    ("Стамбул", "Istanbul Hagia Sophia exterior photo"),
    ("Нью-Йорк", "New York Brooklyn Bridge city photograph"),
    ("Санкт-Петербург", "Saint Petersburg Palace Square photo"),
    ("Москва", "Moscow Red Square 2020 photo"),
)
ALLOWED = {
    "CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
}
ANCIENT = re.compile(r"(?<!\d)(?:1[0-8]\d\d|19[0-6]\d)(?!\d)")
IMAGE = re.compile(r"\.(jpe?g)$", re.I)


def clean(value: str, limit: int = 180) -> str:
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    value = html.unescape(value)
    return " ".join(value.split())[:limit]


def meta(extra: dict, key: str) -> str:
    value = extra.get(key) or {}
    return str(value.get("value", "")) if isinstance(value, dict) else ""


def parse_photo(page: dict, city: str, query: str) -> dict | None:
    if page.get("ns") != 6 or not IMAGE.search(page.get("title", "")):
        return None
    ii = (page.get("imageinfo") or [{}])[0]
    if ii.get("mime") != "image/jpeg" or int(ii.get("width") or 0) < 1600:
        return None
    extra = ii.get("extmetadata") or {}
    label = clean(meta(extra, "LicenseShortName"), 60)
    license_url = meta(extra, "LicenseUrl")
    if label not in ALLOWED:
        return None
    # License URLs may have http/www aliases; canonical licence remains fixed by code.
    if license_url and not license_url.startswith(("https://creativecommons.org/", "http://creativecommons.org/")):
        return None
    title = page["title"]
    if ANCIENT.search(title):
        return None
    url = ii.get("thumburl") or ii.get("url") or ""
    full = ii.get("url") or url
    if not all(urlsplit(x).scheme == "https" and urlsplit(x).hostname == "upload.wikimedia.org"
               for x in (url, full)):
        return None
    source_url = ii.get("descriptionurl") or ""
    if not source_url.startswith("https://commons.wikimedia.org/wiki/File:"):
        return None
    artist = clean(meta(extra, "Artist"), 250) or clean(ii.get("user") or "", 100)
    if not artist:
        return None
    name = title.removeprefix("File:").rsplit(".", 1)[0].replace("_", " ")
    ident = str(page.get("pageid") or "")
    if not ident.isdigit():
        return None
    return {
        "id": "commons-photo-" + ident, "city": city, "name": name,
        "description": clean(meta(extra, "ImageDescription"), 250),
        "image": url, "image_large": full,
        "original_width": int(ii["width"]), "original_height": int(ii["height"]),
        "quality_tier": "высокое" if ii["width"] >= 3000 else "достаточное",
        "maker": artist, "rights": label, "license_url": ALLOWED[label],
        "url": source_url, "source": "Wikimedia Commons", "source_id": title,
        "verified": "commons_api_extmetadata", "selection": "machine_selected_by_search",
        "date_taken": "не установлена",
        "uploaded_at": str(ii.get("timestamp") or ""),
        "search_subject": query, "checked": date.today().isoformat(),
        "can_exact_overlay": False,
        "notice": "Ракурс с историческим листом не проверен. Дата загрузки не равна дате съёмки.",
    }


def search(query: str) -> dict:
    args = {
        "action": "query", "format": "json", "formatversion": 2,
        "generator": "search", "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 20,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata|user|timestamp",
        "iiurlwidth": 1100,
    }
    req = Request(API + "?" + urlencode(args), headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=22) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Oversize Commons response")
    return json.loads(raw)


def build(out: Path, per_query: int = 4, max_items: int = 68) -> dict:
    picked = {}
    warnings = []
    for city, phrase in QUERIES:
        try:
            result = search(phrase)
            candidates = []
            for pg in (result.get("query") or {}).get("pages", []):
                item = parse_photo(pg, city, phrase)
                if item:
                    candidates.append(item)
            candidates.sort(key=lambda a: (a["quality_tier"] != "высокое", -a["original_width"], a["id"]))
            for candidate in candidates[:per_query]:
                if len(picked) < max_items:
                    picked.setdefault(candidate["id"], candidate)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            warnings.append(phrase + ": " + str(exc)[:120])
        time.sleep(0.7)
    folder = out / "data/curation"
    folder.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": date.today().isoformat(),
        "scope": "Wikimedia Commons API verified free licenses; photographer attribution on each image",
        "warning": ("Automatically discovered photographs; camera angle and shooting "
                    "date are NOT independently checked."),
        "items": list(picked.values()),
    }
    (folder / "modern-city-photography-v1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = {"visible_images": len(picked), "cities": len({x["city"] for x in picked.values()}),
              "issues": warnings, "rights_verified_by_metadata": True,
              "not_matched_to_historical_viewpoints": True}
    (out / "modern-photo-discovery-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.out)
