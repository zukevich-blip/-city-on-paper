"""The Book (book/): one spine for the museum. Static checks of the data it is built from."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODERN = re.compile(
    r"geograph|\bIMG_|\bDSC_?\d|panoramio|flickr|City of London School|\bsundial\b|\bcourtyard\b|war memorial",
    re.I,
)


def _atlas() -> dict:
    return json.loads((ROOT / "eras/data/atlas.json").read_text(encoding="utf-8"))


def test_book_page_has_static_heading_and_is_published() -> None:
    html = (ROOT / "book/index.html").read_text(encoding="utf-8")
    assert html.count("<h1") == 1 and 'id="book"' in html and "app.js" in html
    build = (ROOT / "tools/release/build_public_site.py").read_text(encoding="utf-8")
    assert '"book/index.html"' in build and '"book"' in build


def test_featured_plates_and_pairs_exist_and_are_real_prints() -> None:
    ed = json.loads((ROOT / "book/editorial.json").read_text(encoding="utf-8"))
    sites = {s["wid"]: s for c in _atlas()["cities"] for s in c.get("sites", [])}
    pairs = json.loads((ROOT / "poc/compare/pairs/index.json").read_text(encoding="utf-8"))
    assert len(ed["featured"]) >= 6
    for item in ed["featured"]:
        assert item.get("hook") and item["hook"].endswith(("?", ".")), item
        if "pair" in item:
            assert item["pair"] in pairs["places"], item
        else:
            site = sites[item["plate"]]
            assert site["image"] and not MODERN.search(site["title"]), item


def test_every_country_with_views_has_cities_and_no_modern_snapshots_in_book() -> None:
    atlas = _atlas()
    shown = [s for c in atlas["cities"] for s in c.get("sites", []) if s.get("image") and not MODERN.search(s["title"])]
    assert len(shown) >= 300
    assert all(s.get("wid") and s.get("lat") is not None for s in shown)
    # plate ids must be unique, they are used as page addresses
    assert len({s["wid"] for s in shown}) == len(shown)
