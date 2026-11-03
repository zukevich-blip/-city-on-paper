"""New museum rooms: validate historical bibliography and prevent unlicensed image publication."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_catalogs_preserve_rights_and_original_sources():
    d=json.loads((ROOT/"data/catalog/ornament-workshop-2026-11-02.json").read_text(encoding="utf-8"))
    assert len(d["records"])==14
    assert len(d["sources"])==2
    assert any(x["date"] is None for x in d["sources"])
    assert all(x["original"].startswith("https://archive.org/") for x in d["sources"])
    assert all(x["publish_image"] is False for x in d["records"])
    assert all(x["verified_pair"] is False for x in d["records"])
    for record in d["records"]:
        assert record["source_id"] in {s["id"] for s in d["sources"]}
        assert record["source_url"].startswith("https://archive.org/")


def test_drawing_lesson_does_not_redistribute_recent_russian_scans():
    d=json.loads((ROOT/"data/catalog/bargue-academy-2026-11-02.json").read_text(encoding="utf-8"))
    assert d["book"]["publication"].endswith("2020")
    assert "not licensed" in d["book"]["rights"]
    html=(ROOT/"atelier/bargue/index.html").read_text(encoding="utf-8")
    assert 'id="drawing"' in html and 'id="reference"' in html
    assert "localStorage" in html
    assert not any(ext in html.lower() for ext in [".pdf", "data:application/pdf"])


def test_gallery_and_studio_are_navigable_and_built():
    for path in ["ornaments/index.html","atelier/bargue/index.html","studio/index.html","journeys/index.html"]:
        assert (ROOT/path).is_file()
    home=(ROOT/"index.html").read_text(encoding="utf-8")
    assert 'href="ornaments/"' in home
    assert 'href="atelier/bargue/"' in home
    ornaments=(ROOT/"ornaments/index.html").read_text(encoding="utf-8")
    assert "ornament-workshop-2026-11-02.json" in ornaments
    assert "../atelier/bargue/" in ornaments
