#!/usr/bin/env python3
"""Audit the grain and evidence status of world-city records in the built museum."""
from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

FILES = {
    "atlas": "eras/data/atlas.json",
    "seed": "data/curation/world-cities-v1.json",
    "detailed": "eras/data/eras.json",
    "commons": "data/curation/world-graphic-archive-v1.json",
    "museum": "data/curation/museum-expansion-v1.json",
    "modern": "data/curation/modern-city-photography-v1.json",
}


def norm(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())


def https(url: str | None) -> bool:
    parsed = urlsplit(url or "")
    return parsed.scheme == "https" and bool(parsed.hostname)


def blank(name: str, country: str = "", region: str = "", seed: bool = False) -> dict:
    return {
        "name": name, "country": country, "region": region,
        "type": "city" if seed else "unclassified",
        "seed": seed, "atlas": False, "atlas_kind": None,
        "atlas_works": 0, "atlas_open_images": 0,
        "commons_candidates": 0, "museum_candidates": 0,
        "modern_candidates": 0, "detail_images": 0,
        "country_conflict": False, "source_examples": [],
    }


def build(root: Path) -> dict:
    sources = {}
    for key, relative in FILES.items():
        file = root / relative
        if not file.is_file():
            raise FileNotFoundError(f"Required museum data missing: {relative}")
        sources[key] = json.loads(file.read_text(encoding="utf-8"))
    records = {}
    for city in sources["seed"]["cities"]:
        key = norm(city["name"])
        if key in records:
            raise ValueError(f"Repeated seed city name: {city['name']}")
        records[key] = blank(city["name"], city.get("country", ""),
                             city.get("region", ""), True)

    for place in sources["atlas"]["cities"]:
        key = norm(place["name"])
        row = records.setdefault(key, blank(place["name"], place.get("country", "")))
        if row["country"] and place.get("country") and norm(row["country"]) != norm(place["country"]):
            row["country_conflict"] = True
        kind = place.get("kind")
        if not row["seed"]:
            row["type"] = (
                "city" if kind in {"city", "town"} else
                "place" if kind in {"monument", "landscape"} else "unclassified"
            )
        row["atlas"] = True
        row["atlas_kind"] = kind
        works = place.get("works", [])
        row["atlas_works"] += len(works)
        row["atlas_open_images"] += sum(
            work.get("rights_class") == "open" and https(work.get("url"))
            and bool(work.get("image")) for work in works
        )
        for work in works:
            url = work.get("url")
            if len(row["source_examples"]) >= 3:
                break
            if https(url) and all(existing["url"] != url for existing in row["source_examples"]):
                row["source_examples"].append({
                    "title": (work.get("title") or "Архивная запись")[:160],
                    "url": url, "review": "candidate",
                })

    for city in sources["detailed"]["cities"]:
        row = records.get(norm(city["name"]))
        if row:
            row["detail_images"] = sum(
                img.get("rights_class") == "open" and bool(img.get("file"))
                and https(img.get("object_url"))
                for place in city.get("places", [])
                for img in place.get("images", [])
            )

    orphan = Counter()
    for group, field in (
        ("commons", "commons_candidates"),
        ("museum", "museum_candidates"),
        ("modern", "modern_candidates"),
    ):
        for item in sources[group]["items"]:
            row = records.get(norm(item.get("city")))
            if row is None:
                orphan[group] += 1
                continue
            row[field] += 1
            url = item.get("url")
            if len(row["source_examples"]) < 3 and https(url) and all(
                existing["url"] != url for existing in row["source_examples"]
            ):
                row["source_examples"].append({
                    "title": (item.get("name") or item.get("title_original") or "Кандидат")[:160],
                    "url": url, "review": "machine_candidate",
                })

    rows = sorted(records.values(), key=lambda row: norm(row["name"]))
    for row in rows:
        count = sum(row[field] for field in (
            "atlas_works", "commons_candidates", "museum_candidates", "modern_candidates",
        ))
        row["candidate_records"] = count
        row["status"] = (
            "detailed" if row["detail_images"] > 0 else
            "candidate" if count > 0 else "seed_only"
        )

    return {
        "version": "2026-11-10",
        "grain": "mixed geographic names; country-linked IDs not yet fully normalized",
        "warning": "Source record, open license, and machine-selected candidate are not curator approval.",
        "source_files": FILES,
        "summary": {
            "seed_cities": len(sources["seed"]["cities"]),
            "atlas_geo_entries": len(sources["atlas"]["cities"]),
            "combined_names": len(rows),
            "name_overlap": len(sources["seed"]["cities"]) + len(sources["atlas"]["cities"]) - len(rows),
            "atlas_with_work": sum(bool(x.get("works")) for x in sources["atlas"]["cities"]),
            "atlas_work_references": sum(len(x.get("works", [])) for x in sources["atlas"]["cities"]),
            "atlas_open_image_references": sum(x["atlas_open_images"] for x in rows),
            "detailed_names": sum(x["status"] == "detailed" for x in rows),
            "names_with_candidates_or_detail": sum(x["status"] != "seed_only" for x in rows),
            "unfilled_names": sum(x["status"] == "seed_only" for x in rows),
            "orphan_candidate_rows": dict(orphan),
            "source_candidate_rows": {
                key: len(sources[key]["items"]) for key in ("commons", "museum", "modern")
            },
            "type_counts": dict(Counter(x["type"] for x in rows)),
        },
        "entries": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    report = build(root)
    output = args.out or root / "data/coverage/world-coverage-20261110.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    csv_path = output.with_suffix(".csv")
    fields = [
        "name", "country", "region", "type", "status", "seed", "atlas",
        "atlas_works", "atlas_open_images", "commons_candidates",
        "museum_candidates", "modern_candidates", "detail_images", "country_conflict",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["entries"])
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Coverage audit: {output} + {csv_path}")


if __name__ == "__main__":
    main()
