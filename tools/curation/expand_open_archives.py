#!/usr/bin/env python3
"""Build one rights-checked, image-backed research shelf from museum APIs.

The 41 hand-curated Cleveland works remain the core. Automatic candidates below are
separate and visibly labelled: museum-confirmed facts, machine-selected relevance.
No credentials, no copying commercial aggregators, no unlicensed image mirroring.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

BASE = "https://openaccess-api.clevelandart.org/api/artworks/"
AIC = "https://api.artic.edu/api/v1/artworks/search"
MET = "https://collectionapi.metmuseum.org/public/collection/v1.1/search"
CITIES = (
    ("Париж", "Paris"), ("Венеция", "Venice"), ("Рим", "Rome"),
    ("Флоренция", "Florence"), ("Лондон", "London"),
    ("Амстердам", "Amsterdam"), ("Неаполь", "Naples"),
    ("Стамбул", "Constantinople"), ("Нью-Йорк", "New York"),
    ("Прага", "Prague"), ("Москва", "Moscow"),
    ("Санкт-Петербург", "Saint Petersburg"), ("Лиссабон", "Lisbon"),
    ("Париж", "Notre Dame"), ("Венеция", "Grand Canal"),
    ("Рим", "Colosseum"), ("Лондон", "Westminster"),
    ("Париж", "Montmartre"), ("город", "Cityscape"),
    ("город", "Architecture"), ("город", "Street Scene"),
    ("городская жизнь", "Market"), ("город", "Bridge"),
    ("город", "Cathedral"), ("город", "Urban"),
)
AIC_TERMS = ("Paris", "Venice", "Rome", "Florence", "London", "architecture", "cityscape", "street", "market")
MET_TERMS = ("Venice", "Rome", "Paris", "Florence", "lithograph", "architecture", "cityscape")
ART = re.compile(
    r"\b(view|city|town|street|avenue|boulevard|square|piazza|market|cafe|café|"
    r"bridge|canal|quay|harbo[u]?r|port|cathedral|church|basilica|temple|"
    r"palace|castle|ruin|arc[h]|gate|tower|fort|gardens?|park|"
    r"colonnade|facade|façade|architecture|interior|promenade|"
    r"panorama|landscape|river|london|paris|venice|venezia|rome|roma|"
    r"florence|firenze|amsterdam|naples|prague|istanbul|constantinople|"
    r"moscow|petersburg|montmartre|seine|grand canal|notre.dame|"
    r"rue|place|pont|halles|st[.]? mark)\b", re.I)
BAD = re.compile(r"\b(portrait|bust|head|earrings?|vase|plate|jar|"
                 r"still life|nude|costume|coat|dress|coin|"
                 r"ring|ornament|decorative pattern|animal)\b", re.I)
GRAPHICS = re.compile(r"print|lithograph|engraving|etching|drawing|watercolor|"
                      r"watercolour|aquatint|woodcut|photograph|daguerreotype|"
                      r"albumen|collotype|pastel|ink|mezzotint|engraved", re.I)
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
UA = "CityOnPaper/2.0 (art archive research; official APIs; no credentials)"


def json_get(url: str, *, timeout: int = 22) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "openaccess-api.clevelandart.org", "api.artic.edu", "collectionapi.metmuseum.org"
    }:
        raise ValueError("Unapproved museum API origin")
    with urlopen(Request(url, headers={"User-Agent": UA, "Accept": "application/json"}), timeout=timeout) as response:
        if response.status != 200:
            raise ValueError(f"Unexpected response {response.status}")
        raw = response.read(5_000_001)
    if len(raw) > 5_000_000:
        raise ValueError("Oversize API payload")
    return json.loads(raw)


def url_with(url: str, params: dict) -> str:
    return url + "?" + urlencode(params)


def tier(width: int | None, full: bool = False) -> str:
    if width and width >= 2500:
        return "высокое"
    if full:
        return "есть оригинал"
    if width and width >= 900:
        return "экранное"
    return "разрешение не определено"


def year_to_era(value) -> str:
    try:
        y = int(value)
        if 1450 <= y < 2100:
            return str((y - 1) // 100 + 1)
    except (ValueError, TypeError):
        pass
    return ""


def score(title: str, technique: str, query: str) -> int:
    t = title.lower()
    if not ART.search(t) or BAD.search(t):
        return -10
    pts = 2
    if query.lower() in t:
        pts += 5
    if GRAPHICS.search(technique):
        pts += 4
    keywords = ("view", "city", "street", "canal", "boulevard", "market", "bridge", "palace", "ruin", "cathedral")
    if any(x in t for x in keywords):
        pts += 3
    return pts


def make_cma(a: dict, city: str, query: str) -> tuple[dict, int] | None:
    if a.get("share_license_status", "").upper() != "CC0":
        return None
    pic = a.get("images") or {}
    web = pic.get("web") or {}
    pr = pic.get("print") or {}
    if not web.get("url") or not a.get("accession_number"):
        return None
    title = (a.get("title") or "").strip()
    medium = a.get("technique") or a.get("type") or ""
    rating = score(title, medium, query)
    if rating < 0:
        return None
    web_url = web["url"]
    if not web_url.startswith("https://openaccess-cdn.clevelandart.org/") or not web_url.endswith("_web.jpg"):
        return None
    print_url = pr.get("url") or web_url
    if not print_url.startswith("https://openaccess-cdn.clevelandart.org/"):
        print_url = web_url
    width = int(pr.get("width") or web.get("width") or 0)
    artists = "; ".join(c.get("description", "") for c in a.get("creators", [])[:3] if c.get("description"))
    acc = a["accession_number"]
    return {
        "id": "cma-expand-" + acc.replace(".", "-"),
        "city": city, "era": year_to_era(a.get("creation_date_earliest")),
        "date": str(a.get("creation_date") or ""),
        "name": title, "title_original": a.get("title_in_original_language") or title,
        "maker": artists or "Автор не установлен",
        "medium": medium, "image": web_url, "image_large": print_url,
        "width_original": width or None, "quality_tier": tier(width, bool(pr)),
        "source": "The Cleveland Museum of Art", "source_id": acc,
        "url": a.get("url") or "https://www.clevelandart.org/art/" + acc,
        "source_api": "https://openaccess-api.clevelandart.org/api/artworks/" + acc,
        "license_url": CC0, "rights": "cc0", "verified": "museum_api",
        "selection": "machine_selected_title_relevance", "note": "",
        "theme": "Город и архитектура",
        "checked": date.today().isoformat(), "provider": "cleveland",
    }, rating + (2 if width >= 2500 else 0)


def collect_cma(max_items: int) -> tuple[list[dict], list[str]]:
    selected: dict[str, tuple[dict, int]] = {}
    errors = []
    for city, query in CITIES:
        req = url_with(BASE, {"q": query, "has_image": 1, "cc0": "", "limit": 100, "skip": 0})
        try:
            j = json_get(req)
            data = j.get("data", [])
            for a in data:
                rec = make_cma(a, city, query)
                if not rec:
                    continue
                item, pts = rec
                if item["id"] not in selected or selected[item["id"]][1] < pts:
                    selected[item["id"]] = (item, pts)
        except (ValueError, OSError, KeyError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append("CMA " + query + ": " + str(exc)[:140])
    # Round-robin cities to prevent one metropolis or one keyword dominating the gallery.
    per_city: dict[str, list[tuple[dict, int]]] = {}
    for record in selected.values():
        per_city.setdefault(record[0]["city"], []).append(record)
    for group in per_city.values():
        group.sort(key=lambda z: (-z[1], z[0]["id"]))
    result = []
    while len(result) < max_items and any(per_city.values()):
        for c in per_city:
            if per_city[c] and len(result) < max_items:
                result.append(per_city[c].pop(0)[0])
    return result, errors


def collect_aic(max_items: int) -> tuple[list[dict], list[str]]:
    found = {}
    errors = []
    fields = ("id,title,artist_title,date_display,date_start,artwork_type_title,"
              "medium_display,image_id,is_public_domain,api_link")
    for query in AIC_TERMS:
        url = url_with(AIC, {"q": query, "query[term][is_public_domain]": "true", "limit": 100, "fields": fields})
        try:
            j = json_get(url)
            for a in j.get("data", []):
                if a.get("is_public_domain") is not True or not a.get("image_id"):
                    continue
                t = str(a.get("title") or "")
                technique = str(a.get("medium_display") or a.get("artwork_type_title") or "")
                if score(t, technique, query) < 0:
                    continue
                ident = str(a["id"])
                imgid = str(a["image_id"])
                if not re.fullmatch(r"[\w-]{12,80}", imgid):
                    continue
                img = "https://www.artic.edu/iiif/2/" + imgid + "/full/843,/0/default.jpg"
                large = "https://www.artic.edu/iiif/2/" + imgid + "/full/1686,/0/default.jpg"
                found["aic-" + ident] = {
                    "id": "aic-" + ident,
                    "city": next((loc for loc, q in CITIES if q.lower() in t.lower()), "Города мира"),
                    "era": year_to_era(a.get("date_start")), "date": a.get("date_display") or "",
                    "name": t, "title_original": t, "maker": a.get("artist_title") or "Автор не установлен",
                    "medium": technique, "image": img, "image_large": large,
                    "quality_tier": "IIIF · доступно увеличение", "width_original": None,
                    "source": "Art Institute of Chicago", "source_id": ident,
                    "url": "https://www.artic.edu/artworks/" + ident,
                    "license_url": "https://www.artic.edu/open-access/open-access-images",
                    "rights": "cc0", "verified": "museum_api", "selection": "machine_selected_title_relevance",
                    "note": "", "theme": "Города и повседневная жизнь", "checked": date.today().isoformat(),
                    "provider": "aic", "delivery": "museum_iiif_hotlink",
                }
        except (OSError, ValueError, KeyError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append("AIC " + query + ": " + str(exc)[:140])
        time.sleep(1.05)  # AIC asks not to parallelise scraping / >1 request per second.
    return list(found.values())[:max_items], errors


def collect_met(max_items: int) -> tuple[list[dict], list[str]]:
    errors = []
    ids = []
    for query in MET_TERMS:
        url = url_with(MET, {"q": query, "hasImages": "true", "isPublicDomain": "true", "limit": 35, "offset": 0})
        try:
            for key in (json_get(url).get("objectIDs") or []):
                if key not in ids:
                    ids.append(key)
        except (ValueError, OSError, KeyError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append("Met search " + query + ": " + str(exc)[:140])
    result = []
    for objid in ids[:max_items * 3]:
        if len(result) >= max_items:
            break
        try:
            a = json_get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{int(objid)}")
            if not a.get("isPublicDomain") or not a.get("primaryImageSmall"):
                continue
            title = str(a.get("title") or "").strip()
            med = str(a.get("medium") or "")
            if score(title, med, "city") < 0:
                continue
            img = a["primaryImageSmall"]
            large = a.get("primaryImage") or img
            if urlsplit(img).hostname != "images.metmuseum.org" or urlsplit(large).hostname != "images.metmuseum.org":
                continue
            ident = str(a["objectID"])
            result.append({
                "id": "met-" + ident,
                "city": next((loc for loc, q in CITIES if q.lower() in title.lower()), "Города мира"),
                "era": year_to_era(a.get("objectBeginDate")), "date": a.get("objectDate") or "",
                "name": title, "title_original": title, "maker": a.get("artistDisplayName") or "Автор не установлен",
                "medium": med, "image": img, "image_large": large,
                "width_original": None, "quality_tier": "разрешение не измерено",
                "source": "The Metropolitan Museum of Art", "source_id": ident,
                "url": a.get("objectURL") or "https://www.metmuseum.org/art/collection/search/" + ident,
                "license_url": "https://www.metmuseum.org/policies/image-resources",
                "rights": "cc0", "verified": "museum_api", "selection": "machine_selected_title_relevance",
                "note": "", "theme": "Города и архитектура",
                "checked": date.today().isoformat(), "provider": "met",
                "delivery": "museum_original_hotlink",
            })
        except (ValueError, OSError, TimeoutError, json.JSONDecodeError, TypeError) as exc:
            errors.append("Met object " + str(objid) + ": " + str(exc)[:90])
        time.sleep(0.18)
    return result, errors


def cache_cma(records: list[dict], out: Path, cap: int) -> dict:
    dest = out / "assets/art/expansion"
    dest.mkdir(parents=True, exist_ok=True)
    report = {"attempted": 0, "cached": 0, "failed": []}
    try:
        from PIL import Image, ImageOps
    except ImportError:
        report["failed"].append("Pillow missing: use museum URLs")
        return report
    for a in records[:cap]:
        url = a["image"]
        if urlsplit(url).hostname != "openaccess-cdn.clevelandart.org":
            continue
        report["attempted"] += 1
        filename = a["id"] + ".jpg"
        filepath = dest / filename
        try:
            with urlopen(Request(url, headers={"User-Agent": UA}), timeout=12) as response:
                raw = response.read(5_000_001)
            if len(raw) < 1000 or len(raw) > 5_000_000 or not raw.startswith(b"\xff\xd8\xff"):
                raise ValueError("bad/oversize JPEG")
            with Image.open(io.BytesIO(raw)) as orig:
                orig.load()
                if orig.width < 400 or orig.height < 300:
                    raise ValueError("image too small")
                pic = ImageOps.exif_transpose(orig).convert("RGB")
                pic.thumbnail((1024, 1024))
                pic.save(filepath, "JPEG", quality=82, optimize=True)
            a["image_remote"] = url
            a["image"] = "../assets/art/expansion/" + filename
            a["local_preview_width"] = pic.width
            report["cached"] += 1
        except (OSError, TimeoutError, ValueError) as exc:
            report["failed"].append(a["id"] + ": " + str(exc)[:100])
    return report


def build(out: Path, cma: int, aic: int, met: int, cache_limit: int) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    c, ce = collect_cma(cma)
    a, ae = collect_aic(aic)
    m, me = collect_met(met)
    cc = cache_cma(c, out, cache_limit)
    items = c + a + m
    assert len({x["id"] for x in items}) == len(items)
    path = out / "data/curation/museum-expansion-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": date.today().isoformat(),
        "scope": "API-verified rights; algorithmically selected visual candidates, NOT curator approved.",
        "data_quality": "official museum metadata; uneven image resolution is disclosed",
        "rights_note": (
            "All expansion images are from API records explicitly tagged CC0/public domain. "
            "No restricted items."
        ),
        "items": items,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "generated_on": date.today().isoformat(),
        "total": len(items), "by_institution": dict(Counter(x["source"] for x in items)),
        "by_city": dict(Counter(x["city"] for x in items)),
        "cma_cached": cc["cached"], "cma_attempted": cc["attempted"],
        "image_cache_failures": cc["failed"][:20],
        "source_errors": (ce + ae + me)[:40],
        "not_curator_approved": True,
    }
    (out / "museum-expansion-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cma", type=int, default=220)
    p.add_argument("--aic", type=int, default=110)
    p.add_argument("--met", type=int, default=60)
    p.add_argument("--cache", type=int, default=180)
    args = p.parse_args()
    report = build(args.out, args.cma, args.aic, args.met, args.cache)
    print(json.dumps(report, ensure_ascii=False))
    if report["total"] < 60:
        raise SystemExit("Not enough rights-cleared images to claim archive expansion: fail closed")


if __name__ == "__main__":
    main()
