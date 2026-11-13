"""Deterministic City on Paper agent pilot.

Safe, dependency-free evidence collector. Not a claim to invoke LLM agents.
Live requests are limited to three official sources and never scrape image bytes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCES = {
    "loc_benoist_madeleine": {
        "url": "https://www.loc.gov/pictures/item/2016652452/",
        "rights_note": "No known restrictions; NOT CC0",
        "issuer": "Library of Congress",
    },
    "aic_florence_pontevecchio": {
        "url": "https://www.artic.edu/artworks/194443",
        "rights_note": "Check the individual object's rights before reuse",
        "issuer": "Art Institute of Chicago",
    },
    "aic_naples_santalucia": {
        "url": "https://www.artic.edu/artworks/27086",
        "rights_note": "Check the individual object's rights before reuse",
        "issuer": "Art Institute of Chicago",
    },
}
DISPLAY = [
    "index.html",
    "cities/index.html",
    "atlas/index.html",
    "stories/index.html",
    "stories/paris-on-paper/index.html",
    "experience/index.html",
]

def checked_remote(url: str) -> dict:
    """Evidence of URL reachability, NOT provenance or art authentication."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "City-on-Paper-source-health/1.0 (museum QA)"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=7) as response:
            response.read(1024)
            return {"status": "http_accessible", "http_status": response.status}
    except urllib.error.HTTPError as exc:
        return {"status": "needs_review", "http_status": exc.code}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status": "unknown_network", "error_type": type(exc).__name__}

def audit(root: pathlib.Path, live_sources: bool = False) -> dict:
    root = root.resolve()
    missing = [x for x in DISPLAY if not (root / x).is_file()]
    referenced = {}
    all_text = ""
    for file in DISPLAY:
        p = root / file
        if not p.is_file():
            continue
        body = p.read_text(encoding="utf-8")
        all_text += body + "\n"
        referenced[file] = {
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "engraving_layer": "engraving.css" in body,
            "museum_theme": 'class="cop-engraved"' in body,
            "html_title": (re.search(r"<title>([^<]+)</title>", body) or [None, None])[1],
        }

    source_results = {}
    for key, entry in SOURCES.items():
        source_results[key] = {
            **entry,
            "linked_from_page": (
                entry["url"] in all_text
                or entry["url"].replace("/pictures/item/", "/item/") in all_text
            ),
            "reachability": checked_remote(entry["url"]) if live_sources else {
                "status": "not_checked_offline"
            },
        }

    city_data = root / "data/curation/world-cities-v1.json"
    try:
        raw = json.loads(city_data.read_text(encoding="utf-8"))
        count = len(raw.get("cities", []))
    except (OSError, json.JSONDecodeError, AttributeError):
        count = None
    quality_gates = {
        "six_editorial_pages_present": not missing,
        "six_pages_have_engraving_design": all(
            x["engraving_layer"] and x["museum_theme"] for x in referenced.values()
        ) and not missing,
        "official_sources_referenced": all(
            x["linked_from_page"] for x in source_results.values()
        ),
        "research_seed_count_is_not_verified_artworks": count is not None,
        "original_rights_not_auto_cc0": "No known restrictions; NOT CC0"
        in source_results["loc_benoist_madeleine"]["rights_note"],
    }
    return {
        "schema": "city-on-paper-agent-pilot/v1",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "meaning": "Read-only deterministic QA report; not an autonomous LLM consensus",
        "missing": missing,
        "city_seed_names": count,
        "pages": referenced,
        "official_sources": source_results,
        "quality_gates": quality_gates,
        "passed": all(quality_gates.values()),
        "recommended_roles": [
            {"agent": "GitHub CI", "task": "test/code/ZIP integrity", "status": "executing"},
            {"agent": "Exa", "task": "find museum object records", "status": "connected"},
            {"agent": "Firecrawl", "task": "find official institutional API documentation", "status": "connected"},
            {"agent": "Lovable", "task": "visual prototype only", "status": "independent_run"},
            {"agent": "Ruflo", "task": "isolated sandbox evaluation before integration", "status": "not_installed"},
            {"agent": "Gemini/Antigravity", "task": "additional code reviewer", "status": "awaiting_external_link"},
        ],
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--live-sources", action="store_true")
    args = parser.parse_args()
    report = audit(args.root, args.live_sources)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PASS={report['passed']} seed_names={report['city_seed_names']}, "
          f"pages={len(report['pages'])}, sources={len(report['official_sources'])}")
    if not report["passed"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
