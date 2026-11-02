"""Integrity checks for the source-linked era journeys exhibit."""
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "data/curation/era-journeys-20261102.json"


def test_era_catalog_has_valid_and_unique_records():
    catalog = json.loads(ATLAS.read_text(encoding="utf-8"))
    records = catalog["items"]
    assert len(records) >= 15
    assert len({item["id"] for item in records}) == len(records)
    assert {item["era"] for item in records} == {"17", "18", "19", "20", "21"}
    assert all(item["name"] and item["maker"] and item["date"] for item in records)
    assert all(item["rights"] in catalog["rights_legend"] for item in records)
    assert all(item["source"] and urlsplit(item["url"]).scheme in {"https", "http"} for item in records)


def test_archive_images_are_local_and_original_compare_links_exist():
    catalog = json.loads(ATLAS.read_text(encoding="utf-8"))
    for item in catalog["items"]:
        if item.get("image"):
            assert not item["image"].startswith(("http", "//"))
            assert (ROOT / "journeys" / item["image"]).resolve().is_file(), item["id"]
            assert item["rights"] in {"no_known_restrictions", "licensed_photo"}
        if item.get("compare"):
            assert (ROOT / "journeys" / item["compare"].split("#", 1)[0]).resolve().is_file()
        if item["rights"] == "source_link":
            assert not item.get("image"), item["id"]


def test_atlas_explains_rights_and_is_reachable_from_home():
    page = (ROOT / "journeys/index.html").read_text(encoding="utf-8")
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "era-journeys-20261102.json" in page
    assert "Атлас времени" in page and "Тогда / Сейчас" in page
    assert "права" in page.lower() and "лиценз" in page.lower()
    assert 'href="journeys/"' in home
    assert 'data-era="17"' in page and 'data-era="21"' in page
