#!/usr/bin/env python3
"""Reproducible candidate harvest -> JSON + CSV + provider error log.

Example (no keys required; Europeana uses its public demo key unless
EUROPEANA_API_KEY is set, Smithsonian uses DEMO_KEY unless SI_API_KEY is set):

    python3 -m tools.sources.harvest --plan tools/sources/queries.json \
        --out data/candidates/candidates-2026-11-01 --cache .cache/sources

Output records are *candidates*: not approved, not published, no image bytes.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from tools.sources.connectors import (
    MATCH_FIELDS,
    PROVIDERS,
    SCHEMA_ID,
    Http,
    ProviderError,
    excluded,
    merge,
    relevant,
    resolve_loc_rights,
)
from tools.sources.identity import benoist_hint

CSV_FIELDS = ["id", "provider", "institution", "object_number", "title", "creator_display", "date_display",
              "medium", "place_display", "theme_tags", "rights_category", "rights_statement", "rights_uri",
              "source_url", "iiif_manifest", "preview_url", "search_queries", "possible_duplicates",
              "identifiers", "commons_category"]


def run(plan: dict, http: Http) -> dict:
    items, errors, dropped, dropped_homonym = [], [], Counter(), Counter()
    attempts = []
    for job in plan["jobs"]:
        query, limit = job["query"], int(job.get("limit", 10))
        for provider in job["providers"]:
            fn = PROVIDERS[provider]
            try:
                got = fn(http, query, limit)
            except ProviderError as exc:
                errors.append({**exc.as_dict(), "query": query})
                attempts.append({"provider": provider, "query": query, "ok": False, "kept": 0})
                print(f"  ! {provider:<11} {query!r}: {exc}", file=sys.stderr)
                continue
            kept = 0
            for rec in got:
                if not relevant(rec, job.get("match", query), tuple(job.get("match_in", MATCH_FIELDS))):
                    dropped[provider] += 1
                    continue
                if job.get("exclude") and excluded(rec, job["exclude"]):
                    dropped_homonym[provider] += 1
                    continue
                rec["search_queries"] = [query]
                items.append(rec)
                kept += 1
            attempts.append({"provider": provider, "query": query, "ok": True,
                             "returned": len(got), "kept": kept})
            print(f"  . {provider:<11} {query!r}: {len(got)} returned, {kept} kept", file=sys.stderr)
    items = merge(items)
    loc_stats = resolve_loc_rights(http, items, int(plan.get("loc_rights_max_requests", 80)))
    for i in items:
        if "benoist" in i["creator_display"].lower():
            i["benoist_identity_hint"] = benoist_hint(i["creator_display"], i["date_display"])
        elif "benoist" in (i.get("commons_category") or "").lower():
            # in a Benoist category but the file itself names no Benoist: never inherit the attribution
            i["benoist_identity_hint"] = {"hint": "category_only_not_attribution",
                                          "reason": f"file is in {i['commons_category']} but its Artist "
                                                    "field names no Benoist"}
    return {
        "schema": SCHEMA_ID, "published": False,
        "note": "Search results only. Not approved images. Attribution/licence/geo/viewpoint need human review.",
        "counts": {
            "records": len(items),
            "by_institution": dict(Counter(i["institution"] for i in items).most_common()),
            "by_provider": dict(Counter(i["provider"] for i in items)),
            "by_rights_category": dict(Counter(i["rights_category"] for i in items)),
            "by_theme": dict(Counter(t for i in items for t in i["theme_tags"])),
            "benoist_hints": dict(
                Counter(i["benoist_identity_hint"]["hint"] for i in items if "benoist_identity_hint" in i)
            ),
            "dropped_as_irrelevant": dict(dropped),
            "dropped_as_homonym_place": dict(dropped_homonym),
            "loc_rights_resolution": loc_stats,
            "records_with_possible_duplicates": sum(1 for i in items if i["possible_duplicates"]),
            "duplicate_evidence": dict(Counter(
                v.split(" ")[0] for i in items for v in i.get("duplicate_evidence", {}).values())),
            "requests_made": http.requests_made, "cache_hits": http.cache_hits,
        },
        "attempts": attempts, "errors": errors, "items": items,
    }


def write(result: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", "utf-8")
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for i in result["items"]:
            w.writerow({**i, **{k: "; ".join(i.get(k) or []) for k in
                                ("theme_tags", "search_queries", "possible_duplicates", "identifiers")}})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path, help="output path without extension")
    ap.add_argument("--cache", type=Path, default=Path(".cache/sources"))
    ap.add_argument("--budget", type=int, default=400)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--offline", action="store_true", help="use cached responses only")
    a = ap.parse_args(argv)
    if a.delay < 0.5 or not 1 <= a.budget <= 1000:
        ap.error("delay >= 0.5 s and 1 <= budget <= 1000")
    plan = json.loads(a.plan.read_text("utf-8"))
    http = Http(cache_dir=a.cache, budget=a.budget, delay=a.delay, offline=a.offline)
    result = run(plan, http)
    write(result, a.out)
    c = result["counts"]
    print(f"{c['records']} candidate records from {len(c['by_institution'])} institutions; "
          f"{len(result['errors'])} provider errors; {c['requests_made']} requests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
