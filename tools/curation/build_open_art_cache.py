#!/usr/bin/env python3
"""Build a portable visual collection from curator-approved Cleveland Museum CC0 records.

No unreviewed sources. The metadata stays source-first and is never overwritten in the repo.
Network failure preserves the official image link instead of manufacturing a thumbnail.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "data/curation/cc0-gallery-20261103.json"
MAX_BYTES = 6 * 1024 * 1024
HOST = "openaccess-cdn.clevelandart.org"


def validated_url(item: dict) -> str:
    """Reject arbitrary network hosts and non-CC0 catalog metadata before downloading."""
    if item.get("rights") != "cc0" or item.get("verified") != "museum_api":
        raise ValueError(f"non-open license or unreviewed record: {item.get('id')}")
    url = item["image"]
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != HOST or not parsed.path.endswith("_web.jpg"):
        raise ValueError(f"unexpected remote image URL: {url}")
    if not item.get("source_id") or item.get("source") != "The Cleveland Museum of Art":
        raise ValueError(f"unverified holding: {item.get('id')}")
    return url


def fetch(item: dict, directory: Path) -> tuple[str, str | None, str]:
    url = validated_url(item)
    filename = item["id"] + ".jpg"
    dest = directory / filename
    if dest.exists() and dest.stat().st_size > 1000:
        return item["id"], filename, "cache"
    try:
        req = Request(url, headers={"User-Agent": "CityOnPaper/1.0 (+curatorial source: https://clevelandart.org/open-access)"})
        with urlopen(req, timeout=18) as resp:
            if resp.status != 200:
                raise OSError(f"HTTP {resp.status}")
            data = resp.read(MAX_BYTES + 1)
        if not (1000 < len(data) < MAX_BYTES and data.startswith(bytes((0xFF, 0xD8, 0xFF)))):
            raise ValueError(f"invalid JPEG, {len(data)} bytes")
        dest.write_bytes(data)
        return item["id"], filename, "downloaded"
    except (OSError, ValueError, TimeoutError) as exc:
        return item["id"], None, f"not_cached: {exc}"


def build(out: Path, workers: int) -> dict:
    source = json.loads(CATALOG.read_text(encoding="utf-8"))
    items = source["items"]
    target = out / "assets/art/cc0"
    target.mkdir(parents=True, exist_ok=True)
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, item, target): item["id"] for item in items}
        for fut in as_completed(futures):
            identity, filename, status = fut.result()
            results[identity] = {"file": filename, "status": status}
    manifest = json.loads(json.dumps(source))
    local_map = {}
    for item in manifest["items"]:
        result = results[item["id"]]
        if result["file"]:
            original = item["image"]
            item["image_remote"] = original
            item["image"] = "../assets/art/cc0/" + result["file"]
            local_map[original] = "../assets/art/cc0/" + result["file"]
    target_data = out / "data/curation"
    target_data.mkdir(parents=True, exist_ok=True)
    (target_data / CATALOG.name).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    index = out / "journeys/index.html"
    if index.exists():
        html = index.read_text(encoding="utf-8")
        # Only image src attributes change. Museum source / full-size links remain intact.
        for remote, local in local_map.items():
            html = html.replace(f'src="{remote}"', f'src="{local}"')
        index.write_text(html, encoding="utf-8")
    summary = {
        "source": "Cleveland Museum of Art, CC0 image dataset",
        "total": len(items),
        "cached": len(local_map),
        "remote_fallback": len(items) - len(local_map),
        "bytes": sum(p.stat().st_size for p in target.glob("*.jpg")),
        "failed": [
            {"id": key, **value}
            for key, value in sorted(results.items())
            if value["file"] is None
        ],
    }
    (out / "art-cache-report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    summary = build(args.out, min(max(1, args.workers), 12))
    print(json.dumps(summary, ensure_ascii=False))
    # The public page is allowed to link to remote verified images when museum/CDN is down.


if __name__ == "__main__":
    main()
