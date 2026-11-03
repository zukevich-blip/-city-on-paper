"""Integration gates for Claude PR19 ornament and PR20 drawing workshop."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_trade_catalog_provenance_and_reuse_boundaries():
    j = json.loads((ROOT / "data/catalog/ornament-workshop-2026-11-02.json").read_text())
    assert len(j["sources"]) == 2
    assert len(j["records"]) == 14
    assert {r["source_id"] for r in j["records"]} == {"bakewell1887", "decorators124"}
    assert all(r["publish_image"] is False for r in j["records"])
    assert all(r["verified_pair"] is False for r in j["records"])
    assert len({r["id"] for r in j["records"]}) == 14
    assert all(r["pdf_page"] > 0 and r["source_url"].startswith("https://archive.org/") for r in j["records"])
    # 1964 catalog edition and 1900 candidate date must not be published as certain.
    src = next(s for s in j["sources"] if s["id"] == "decorators124")
    assert src["date"] is None


def test_bargue_historical_and_modern_edition_separated():
    j = json.loads((ROOT / "data/catalog/bargue-academy-2026-11-02.json").read_text())
    assert "2020" in j["book"]["publication"]
    assert j["historical_work"]["total_original_plates"] == 197
    assert j["lesson"]["no_original_plate_embedded"] is True
    page = (ROOT / "atelier/bargue/index.html").read_text()
    assert 'id="reference"' in page
    assert 'id="drawing"' in page
    assert 'id="save"' in page
    assert "<svg" in page
    assert "pdf_page" not in page


def test_public_navigation_to_both_educational_areas():
    html = (ROOT / "atelier/ornament/index.html").read_text()
    assert "ornament-workshop-2026-11-02.json" in html
    assert "Учебная схема, не скан" in html
    assert 'id="search"' in html and 'id="categoryFilter"' in html
    assert "innerHTML" not in html
    home = (ROOT / "index.html").read_text()
    assert "atelier/bargue/" in home and ("ornaments/" in home or "atelier/ornament/" in home)
    assert "Кабинет коллекционера" in home
