#!/usr/bin/env python3
"""Audit atlas cities against the existing global discovery seed without network.

No city or artwork is called 'verified' because a search query or an atlas
marker exists. The output is a research staging registry, NOT published canon.
Do not replace the upstream hand-curated atlas, research files or city IDs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "eras/data/atlas.json"
SEED = ROOT / "data/curation/world-cities-v1.json"
SOURCES = {
    "commons": {
        "url": "https://commons.wikimedia.org/w/api.php",
        "access": "open_api",
        "integration": "tools/curation/build_world_graphics.py",
        "requires_throttle": True,
    },
    "loc": {
        "url": "https://www.loc.gov/search/?fo=json",
        "access": "open_api",
        "integration": "planned_adapter",
        "requires_throttle": True,
    },
    "cleveland": {
        "url": "https://openaccess-api.clevelandart.org/api/artworks/",
        "access": "open_api",
        "integration": "tools/curation/expand_open_archives.py",
        "requires_throttle": True,
    },
    "artic": {
        "url": "https://api.artic.edu/api/v1/artworks/search",
        "access": "open_api",
        "integration": "tools/curation/expand_open_archives.py",
        "requires_throttle": True,
    },
    "met": {
        "url": "https://collectionapi.metmuseum.org/public/collection/v1.1/search",
        "access": "open_api",
        "integration": "tools/curation/expand_open_archives.py",
        "requires_throttle": True,
    },
    "europeana": {
        "url": "https://www.europeana.eu/en/how-to-register-for-and-manage-an-api-key",
        "access": "api_key_required",
        "integration": "not_enabled",
        "requires_throttle": True,
    },
}


def normalize(value: str) -> str:
    """Stable identity match, intentionally conservative about historical aliases."""
    text = unicodedata.normalize("NFKC", str(value)).casefold().replace("ё", "е")
    return re.sub(r"\s+", " ", text).strip()


def city_key(row: dict) -> tuple[str, str]:
    return normalize(row.get("name", "")), normalize(row.get("country", ""))


def slug_for_candidate(row: dict) -> str:
    # A provisional stable import key, NOT a geo ID; aliases need curation.
    value = "|".join(city_key(row)).encode("utf-8")
    return "unresolved-" + hashlib.sha256(value).hexdigest()[:12]


def meaningful_url(item: dict) -> str | None:
    url = item.get("url")
    if not isinstance(url, str):
        return None
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.netloc:
        return None
    return url.split("#", 1)[0]


def audit(atlas: dict, seed: dict) -> tuple[dict, dict, dict]:
    atlas_cities = atlas["cities"]
    search_cities = seed["cities"]
    if len(atlas_cities) != len({str(x["id"]) for x in atlas_cities}):
        raise ValueError("Atlas has duplicate city IDs; stop before building registry")
    if not all(city_key(x)[0] and city_key(x)[1] for x in atlas_cities + search_cities):
        raise ValueError("City name and country must be nonempty")

    by_identity: dict[tuple[str, str], dict] = {}
    ambiguous: list[dict] = []
    record_works: dict[str, set[str]] = {}
    all_refs: Counter[str] = Counter()
    for a in atlas_cities:
        key = city_key(a)
        if key in by_identity:
            # Never merge same-name candidate geometries by guess.
            ambiguous.append({
                "name": a["name"], "country": a["country"],
                "duplicate_ids": [by_identity[key]["city_id"], a["id"]],
                "review": "distinct_places_or_duplicate_atlas_rows",
            })
            continue
        refs = [url for w in a.get("works", []) if (url := meaningful_url(w))]
        record_works[a["id"]] = set(refs)
        all_refs.update(refs)
        coords_ok = (
            isinstance(a.get("lat"), (float, int)) and not isinstance(a.get("lat"), bool)
            and isinstance(a.get("lon"), (float, int)) and not isinstance(a.get("lon"), bool)
            and -90 <= a["lat"] <= 90 and -180 <= a["lon"] <= 180
        )
        by_identity[key] = {
            "city_id": a["id"], "name": a["name"],
            "name_original": a.get("name_orig"),
            "country": a["country"], "region": a.get("area"),
            "lat": a["lat"] if coords_ok else None,
            "lon": a["lon"] if coords_ok else None,
            "coordinates_source": a.get("coord_source"),
            "catalog_status": "existing_atlas",
            "review_status": "unverified_for_global_registry",
            "place_type_review": (
                "review_city_vs_site" if "(" in a["name"] or ")" in a["name"] else "unreviewed"
            ),
            "works_listed": len(a.get("works", [])),
            "unique_source_urls": len(record_works[a["id"]]),
            "discovery_query": None,
            "research_source": "eras/data/atlas.json",
        }

    by_seed: dict[tuple[str, str], dict] = {}
    duplicate_seed: list[dict] = []
    for x in search_cities:
        key = city_key(x)
        if key in by_seed:
            duplicate_seed.append({"name": x["name"], "country": x["country"]})
            continue
        by_seed[key] = x
        if key in by_identity:
            by_identity[key]["discovery_query"] = x.get("query")
        else:
            by_identity[key] = {
                "city_id": slug_for_candidate(x),
                "name": x["name"], "name_original": None,
                "country": x["country"], "region": x.get("region"),
                "lat": None, "lon": None, "coordinates_source": None,
                "catalog_status": "seed_candidate_only",
                "review_status": "awaiting_place_identity_and_sources",
                "place_type_review": "unreviewed",
                "works_listed": 0, "unique_source_urls": 0,
                "discovery_query": x.get("query"),
                "research_source": "data/curation/world-cities-v1.json",
            }

    entries = sorted(by_identity.values(), key=lambda x: (
        x["catalog_status"] != "existing_atlas", normalize(x["country"]),
        normalize(x["name"])))
    queue = []
    for x in entries:
        if x["catalog_status"] == "seed_candidate_only" or x["discovery_query"]:
            query = x["discovery_query"] or (str(x["name_original"] or x["name"]) + " city lithograph")
            queue.append({
                "city_id": x["city_id"], "name": x["name"],
                "country": x["country"], "query": query,
                "scope": "unverified_discovery_query",
                "status": "queued_not_fetched",
                "recommended_adapter": "commons",
            })

    duplicates_in_works = [
        {"url": url, "occurrences": count} for url, count in all_refs.items() if count > 1
    ]
    region_counts = Counter(x.get("region") or "unspecified" for x in entries)
    report = {
        "schema": "city-on-paper/global-city-audit/v1",
        "generated": date.today().isoformat(),
        "origin": {"atlas": "eras/data/atlas.json",
                   "seed": "data/curation/world-cities-v1.json"},
        "scope_note": "Research coverage audit; name+country exact normalized match is NOT full entity resolution.",
        "counts": {
            "atlas_entries": len(atlas_cities),
            "atlas_distinct_name_country": sum(x["catalog_status"] == "existing_atlas" for x in entries),
            "seed_entries": len(search_cities),
            "seed_distinct_name_country": len(by_seed),
            "matched_name_country": sum(x["catalog_status"] == "existing_atlas" and x["discovery_query"] is not None for x in entries),
            "seed_not_in_atlas": sum(x["catalog_status"] == "seed_candidate_only" for x in entries),
            "combined_candidate_records": len(entries),
            "atlas_works_listed": sum(len(a.get("works", [])) for a in atlas_cities),
            "atlas_works_with_valid_source_url": sum(all_refs.values()),
            "atlas_distinct_source_urls": len(all_refs),
            "source_urls_appearing_multiple_times": len(duplicates_in_works),
            "source_url_repeat_occurrences": sum(x["occurrences"] - 1 for x in duplicates_in_works),
            "queue_not_fetched": len(queue),
            "atlas_names_needing_place_type_review": sum(
                x["place_type_review"] == "review_city_vs_site" for x in entries),
            "atlas_invalid_or_missing_coordinates": sum(
                x["catalog_status"] == "existing_atlas" and x["lat"] is None for x in entries),
            "atlas_duplicate_name_country_entries": len(ambiguous),
            "seed_duplicate_name_country_entries": len(duplicate_seed),
        },
        "regional_candidate_counts": dict(sorted(region_counts.items())),
        "warnings": [
            "One atlas entry can be a building, locality or city; never equate item count with verified cities.",
            "Multiple catalog entries may refer to one artwork; source URL duplicates need review, not blind deletion.",
            "Seed records have no confirmed geographic coordinates or artworks.",
            "Historical multilingual names and homonyms are not merged automatically.",
            "Source URLs alone do not verify attribution, license, availability, IIIF, or HD pixels.",
        ],
        "ambiguous_atlas_name_country": ambiguous[:100],
        "duplicate_seed_name_country": duplicate_seed[:100],
        "repeated_work_urls_sample": sorted(
            duplicates_in_works, key=lambda x: (-x["occurrences"], x["url"]))[:30],
        "sources": SOURCES,
    }
    registry = {
        "schema": "city-on-paper/global-city-registry-draft/v1",
        "generated": date.today().isoformat(),
        "publication_status": "research_only_do_not_publish_as_verified_cities",
        "entity_resolution": "normalized_name_and_country_only",
        "cities": entries,
    }
    discovery = {
        "schema": "city-on-paper/global-discovery-queue/v1",
        "generated": date.today().isoformat(),
        "queued_not_fetched": True,
        "network_calls": 0,
        "items": queue,
    }
    return registry, report, discovery


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas", type=Path, default=ATLAS)
    parser.add_argument("--seed", type=Path, default=SEED)
    parser.add_argument("--out", type=Path, default=Path("/tmp/city-global-audit"))
    args = parser.parse_args()
    atlas = json.loads(args.atlas.read_text("utf-8"))
    seed = json.loads(args.seed.read_text("utf-8"))
    registry, report, queue = audit(atlas, seed)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("global-city-registry-draft.json", registry),
        ("global-city-audit-report.json", report),
        ("global-discovery-queue.json", queue),
    ):
        (args.out / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
