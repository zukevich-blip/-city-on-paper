#!/usr/bin/env python3
"""Add rights-checked historic city art from Commons' named thematic categories.

Category membership is preserved as evidence of the subject. It is not proof
that every image is a lithograph or that attribution/date have been verified.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tools.curation.build_world_graphics import API, USER_AGENT, normalize

CATEGORIES = (
    ("Флоренция", "Mercato Vecchio (Florence) in art"),
    ("Флоренция", "Firenze 10 acqueforti di Wilhelm Taubert"),
    ("Флоренция", "Ponte Vecchio in art"),
    ("Венеция", "Prints of Venice"),
    ("Венеция", "Etchings of Venice"),
    ("Венеция", "Lithographs of Venice"),
    ("Неаполь", "Lithographs of Naples"),
    ("Рим", "Prints of Rome"),
    ("Париж", "Lithographs of Paris"),
    ("Париж", "Prints of Paris"),
)


def api_category(category: str) -> dict:
    approved = {"Category:" + name for _, name in CATEGORIES}
    if category not in approved:
        raise ValueError("Unapproved category")
    args = {
        "action": "query", "format": "json", "formatversion": "2",
        "generator": "categorymembers", "gcmtitle": category,
        "gcmtype": "file", "gcmlimit": 50, "maxlag": 5,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 1000,
    }
    req = Request(
        API + "?" + urlencode(args),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urlopen(req, timeout=19) as response:
        raw = response.read(3_000_001)
    if len(raw) > 3_000_000:
        raise ValueError("Oversize category response")
    return json.loads(raw)


def build(out: Path, seed: Path, budget: int = 10, max_seconds: int = 210) -> dict:
    folder = out / "data/curation"
    manifest = folder / "world-graphic-archive-v1.json"
    progress = folder / "world-graphic-progress-v1.json"
    if not manifest.exists():
        raise FileNotFoundError("World graphics base manifest must be built first")
    catalog = json.loads(manifest.read_text(encoding="utf-8"))
    items = {a["id"]: a for a in catalog.get("items", [])}
    region_seed = {
        c["name"]: c for c in json.loads(seed.read_text(encoding="utf-8"))["cities"]
    }
    if progress.exists():
        state = json.loads(progress.read_text(encoding="utf-8"))
    else:
        state = {"version": 2, "completed_cities": [], "completed_categories": []}
    if state.get("version") != 2:
        state = {"version": 2, "completed_cities": [], "completed_categories": []}
    processed = set(state.get("completed_categories", []))
    attempts = 0
    created = 0
    issues = []
    throttled = False
    beginning = time.monotonic()
    for city_name, name in CATEGORIES:
        category = "Category:" + name
        if category in processed or attempts >= budget:
            continue
        if time.monotonic() - beginning > max_seconds:
            break
        attempts += 1
        try:
            response = api_category(category)
            candidates = []
            for page in (response.get("query") or {}).get("pages", []):
                result = normalize(page, region_seed[city_name], category)
                if result is not None:
                    candidates.append(result)
            candidates.sort(key=lambda x: (-x[1], x[0]["id"]))
            for work, _ in candidates[:30]:
                if work["id"] not in items:
                    items[work["id"]] = work
                    created += 1
            # This marks the first direct 50 files from the category as covered.
            # A continuation cursor will be needed for very large categories.
            processed.add(category)
        except HTTPError as exc:
            issues.append({"category": category, "code": exc.code})
            if exc.code in {429, 503}:
                throttled = True
                break
        except (OSError, ValueError, TimeoutError, json.JSONDecodeError) as exc:
            issues.append({"category": category, "error": str(exc)[:130]})
        time.sleep(1.2)

    works = sorted(items.values(), key=lambda a: (a["region"], a["country"], a["city"], a["name"]))
    catalog["items"] = works
    catalog["version"] = date.today().isoformat()
    catalog["category_discovery"] = (
        "Historical city subject categories verified by Commons API. Individual "
        "image licenses remain separately checked; editor review pending."
    )
    manifest.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state["completed_categories"] = sorted(processed)
    progress.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "attempted_categories": attempts,
        "completed_categories": len(processed),
        "new_work_count": created,
        "total_world_prints": len(works),
        "city_counts": dict(Counter(a["city"] for a in works)),
        "category_geography_entries": sum(
            a.get("geography_confidence") == "commons_category" for a in works
        ),
        "rate_limited": throttled,
        "issues": issues,
    }
    (out / "featured-cities-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--cities", type=Path, default=Path("data/curation/world-cities-v1.json")
    )
    parser.add_argument("--budget", type=int, default=10)
    args = parser.parse_args()
    build(args.out, args.cities, budget=max(0, min(args.budget, len(CATEGORIES))))


if __name__ == "__main__":
    main()
