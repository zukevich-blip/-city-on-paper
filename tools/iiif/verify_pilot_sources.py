#!/usr/bin/env python3
"""Recheck known LoC IIIF endpoints without publishing or downloading images.

Reads curated exact URLs, not guessed identifiers. Standard-library only.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from tools.iiif.audit_manifest import audit

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "data/research/iiif-pilot-3-works-paris-20261109.json"
MAX_BYTES = 3_000_000
ALLOWED_HOSTS = {"www.loc.gov", "tile.loc.gov"}


def fetch_json(url: str) -> dict:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only specific official LoC https hosts are permitted")
    if not (parts.path.endswith("/manifest.json") or parts.path.endswith("/info.json")):
        raise ValueError("Only known Manifest and Image API info.json endpoints are permitted")
    request = Request(url, headers={"User-Agent": "CityOnPaperResearch/0.1 (IIIF source verifier)"})
    with urlopen(request, timeout=15) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Response exceeds metadata size limit")
    result = json.loads(data)
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result


def verify(catalog: dict, fetch=fetch_json) -> dict:
    """Build a non-publishing verification report; preserve mismatches."""
    records: list[dict] = []
    targets = [*catalog["records"], catalog["map"]]
    for record in targets:
        item = {"record_id": record["record_id"], "status": "unchecked"}
        try:
            manifest = fetch(record["iiif_manifest_url"])
            if (manifest.get("id") or manifest.get("@id")) != record["iiif_manifest_url"]:
                raise ValueError("Manifest self-id does not match the official source URL")
            details = audit(manifest)
            count = details["canvas_count"]
            item.update({
                "status": "checked",
                "manifest_url": details["manifest_url"],
                "canvas_count": count,
                "canvas_count_matches_catalog": count == record.get(
                    "iiif_manifest_canvas_count", record.get("canvas_count")
                ),
                "image_service_ids_from_manifest": details["image_service_ids"],
                "manifest_warnings": details["warnings"],
            })
            if record is catalog["map"]:
                info = fetch(record["iiif_image_info_url"])
                actual = (info.get("width"), info.get("height"))
                item["image_info_matches_catalog"] = (
                    info.get("@id") == record["iiif_image_service_url"]
                    and actual == (record["source_width"], record["source_height"])
                )
                item["image_dimensions"] = actual
        except (HTTPError, URLError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            item.update(status="error", error=f"{type(exc).__name__}: {str(exc)[:400]}")
        records.append(item)
    return {
        "schema": "city-on-paper/iiif-source-verification/v1",
        "publication_status": "never_auto_publish",
        "records": records,
        "all_expected_counts_match": all(
            x.get("status") == "checked" and x.get("canvas_count_matches_catalog")
            and x.get("image_info_matches_catalog", True) for x in records
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, help="Optional JSON report destination")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between LoC requests")
    args = parser.parse_args()
    if not 0 <= args.delay <= 60:
        parser.error("--delay must be between 0 and 60 seconds")
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))

    def throttled_fetch(url: str) -> dict:
        if args.delay:
            time.sleep(args.delay)
        return fetch_json(url)

    report = verify(catalog, fetch=throttled_fetch)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
