#!/usr/bin/env python3
"""PRIVATE_RESEARCH tier: fetch images whose public rights are NOT confirmed, for the owner's personal research only.

Run this on your own computer, never in CI. Files go to ``private-archive/`` which is git-ignored, excluded from the
release allowlist and refused by the public-boundary tests. A private copy is not a licence to republish: nothing from
here may be committed, put on GitHub Pages, in a public ZIP or in an Actions artifact.

Usage: python3 tools/private/fetch_private_archive.py [--limit N] [--source europeana] [--dry-run]
Reads data/research/benoist/*.json (records with image_url and rights_status != open_confirmed).
Polite (>= 1.2 s between requests), no authentication or CAPTCHA bypass: any non-200 is logged and skipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "data" / "research" / "benoist"
VAULT = ROOT / "private-archive"
UA = "CityOnPaperResearch/0.9 (private, non-commercial research; github.com/zukevich-blip/-city-on-paper)"
SKIP_STATUSES = {"open_confirmed"}  # these belong to the public museum, not to the private cache


def in_ci(env: dict[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return bool(env.get("CI") or env.get("GITHUB_ACTIONS"))


def safe_name(record_id: str, url: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", record_id)[:80]
    return f"{stem}-{hashlib.sha1(url.encode()).hexdigest()[:8]}.jpg"


def wanted(records: list[dict]) -> list[dict]:
    return [r for r in records if r.get("image_url") and r.get("rights_status") not in SKIP_STATUSES]


def load_records() -> list[dict]:
    out: list[dict] = []
    for f in sorted(RESEARCH.glob("*.json")):
        out.extend(json.loads(f.read_text(encoding="utf-8")).get("records", []))
    return out


def target_path(name: str) -> Path:
    path = (VAULT / "images" / name).resolve()
    if not path.is_relative_to(VAULT.resolve()):
        raise ValueError("refusing to write outside private-archive/")
    return path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--source")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if in_ci():
        print("refusing to run in CI: the private archive is local-only", file=sys.stderr)
        return 2
    todo = [r for r in wanted(load_records()) if not args.source or r["record_id"].startswith(args.source)][
        : args.limit
    ]
    index_path = VAULT / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    for r in todo:
        name = safe_name(r["record_id"], r["image_url"])
        if args.dry_run:
            print("would fetch", r["record_id"], r["image_url"])
            continue
        dest = target_path(name)
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            req = urllib.request.Request(r["image_url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                dest.write_bytes(resp.read())
            index[r["record_id"]] = {
                "file": f"images/{name}",
                "source_url": r["record_url"],
                "rights_status": r.get("rights_status"),
            }
        except Exception as exc:  # noqa: BLE001 - logged, never hidden
            print("skip", r["record_id"], str(exc)[:100], file=sys.stderr)
        time.sleep(1.2)
    if not args.dry_run:
        VAULT.mkdir(exist_ok=True)
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(todo), "records considered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
