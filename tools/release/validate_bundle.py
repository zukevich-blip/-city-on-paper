#!/usr/bin/env python3
"""Validate ACTUAL packaged City on Paper private preview, not only source checkout."""
from __future__ import annotations

import argparse
import json
import posixpath
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

PAGES = (
    "index.html", "salon/index.html", "closeup/index.html",
    "exhibitions/city-as-evidence/index.html", "discover/index.html",
    "journeys/index.html", "detective/index.html", "fieldwork/index.html",
    "printlab/index.html", "ideas/index.html", "studio/index.html",
    "ornaments/index.html", "atelier/bargue/index.html",
    "atelier/ornament/index.html", "poc/compare/index.html",
    "poc/compare/editor.html",
)
DATA = (
    "data/curation/cc0-gallery-20261103.json",
    "data/curation/close-reading-20261103.json",
    "data/curation/close-reading-benoist-20261103.json",
    "data/curation/era-journeys-20261102.json",
    "data/candidates/candidates-2026-11-01b.json",
    "poc/compare/pairs/index.json",
)


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src", "poster"} and value:
                self.urls.append((tag, key, value))


def resolve(page: str, raw: str) -> str | None:
    if not raw or "${" in raw or raw.startswith(("data:", "blob:", "mailto:", "tel:", "#", "javascript:")):
        return None
    parts = urlsplit(raw)
    if parts.scheme or parts.netloc:
        return None
    loc = unquote(parts.path)
    if not loc:
        return None
    if loc.startswith("/"):
        path = loc.lstrip("/")
    else:
        path = posixpath.normpath(posixpath.join(posixpath.dirname(page), loc))
    if loc.endswith("/"):
        path = posixpath.join(path, "index.html")
    if path == ".":
        path = "index.html"
    if path.startswith("../"):
        raise ValueError(f"path escapes bundle: {page}: {raw}")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    args = ap.parse_args()
    root = args.root.resolve()
    missing = [p for p in (*PAGES, *DATA, "README_RUN.txt", "art-cache-report.json") if not (root / p).is_file()]
    invalid_links = []
    for page in PAGES:
        f = root / page
        if not f.is_file():
            continue
        parser = LocalLinks()
        parser.feed(f.read_text(encoding="utf-8"))
        for tag, key, raw in parser.urls:
            target = resolve(page, raw)
            if target and not (root / target).is_file():
                invalid_links.append({"page": page, "element": tag, "attribute": key, "url": raw, "resolved": target})

    works = json.loads((root / DATA[0]).read_text(encoding="utf-8"))["items"]
    assert len(works) >= 41, "expected 41 curated Cleveland CC0 works"
    assert len({w["id"] for w in works}) == len(works), "duplicate artwork IDs"
    assert all(w["rights"] == "cc0" and w["url"].startswith("https://") for w in works)
    cached = 0
    for art in works:
        image = art["image"]
        page_rel = resolve("salon/index.html", image)
        if page_rel:
            if not (root / page_rel).is_file():
                missing.append("salon image: " + art["id"] + " -> " + page_rel)
            else:
                cached += 1

    loc = json.loads((root / DATA[2]).read_text(encoding="utf-8"))["records"]
    assert len(loc) == 2, "expected two source-linked Benoist historical prints"
    for art in loc:
        assert art["rights"] == "loc_no_known_restrictions", "LoC must not be relabelled CC0"
        assert "loc.gov" in art["url"]
        target = resolve("closeup/index.html", art["image"])
        if not target or not (root / target).is_file():
            missing.append("LoC art: " + art["id"])

    study = json.loads((root / DATA[1]).read_text(encoding="utf-8"))["lessons"]
    all_ids = {x["id"] for x in works} | {x["id"] for x in loc}
    assert all(x["id"] in all_ids and len(x["steps"]) == 3 for x in study)

    candidates = json.loads((root / DATA[4]).read_text(encoding="utf-8"))["items"]
    assert all(not x.get("published") for x in candidates), "unapproved research candidates must remain unpublished"
    assert all(not x.get("preview_url") for x in candidates if x["rights_category"] != "open")

    ex_html = (root / "exhibitions/city-as-evidence/index.html").read_text(encoding="utf-8")
    assert "imageUrl(" in ex_html and "../../" in ex_html, "nested exhibition cached artwork URL correction missing"

    cache = json.loads((root / "art-cache-report.json").read_text(encoding="utf-8"))
    photos_cached = cache.get("modern_photos_cached", 0)
    status = "PASS" if not missing and not invalid_links and cached >= 35 and photos_cached >= 2 else "FAIL"
    report = {
        "status": status,
        "page_count": len(PAGES),
        "source_cma_cc0_count": len(works),
        "local_cma_images": cached,
        "modern_photos_cached": photos_cached,
        "benoist_loc_not_cc0": len(loc),
        "guided_lessons": len(study),
        "unapproved_candidates": len(candidates),
        "independently_verified_exact_then_now_pairs": 0,
        "missing_files": missing,
        "broken_static_links": invalid_links,
        "note": "Source v7 export not in this build; exact viewpoint matches not independently certified.",
    }
    (root / "RELEASE_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if status != "PASS":
        raise SystemExit("Packaged preview failed its self-contained release audit")


if __name__ == "__main__":
    main()
