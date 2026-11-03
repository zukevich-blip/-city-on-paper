"""Release gates for source-verified CC0 museum artwork imagery."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from tools.curation.build_open_art_cache import validated_url, validated_photo_url

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/curation/cc0-gallery-20261103.json"
ATLAS = ROOT / "data/curation/era-journeys-20261102.json"


def test_41_individually_verified_open_museum_works():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    items = data["items"]
    assert len(items) == 41
    assert data["n"] == len(items)
    assert len({x["id"] for x in items}) == len(items)
    assert len({x["source_id"] for x in items}) == len(items)
    base = json.loads(ATLAS.read_text(encoding="utf-8"))
    assert set(x["id"] for x in items).isdisjoint(x["id"] for x in base["items"])
    for item in items:
        assert item["rights"] == "cc0"
        assert item["verified"] == "museum_api"
        assert item["license_url"] == "https://creativecommons.org/publicdomain/zero/1.0/"
        assert item["maker"] and item["date"] and item["title_original"]
        assert urlsplit(item["url"]).hostname == "clevelandart.org"
        assert urlsplit(item["source_api"]).hostname == "openaccess-api.clevelandart.org"
        assert urlsplit(validated_url(item)).hostname == "openaccess-cdn.clevelandart.org"
        assert item["image_large"].startswith("https://openaccess-cdn.clevelandart.org/")


def test_cc0_images_are_not_mixed_with_derived_then_now_photos():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert not any("compare" in x or "photo" in x for x in data["items"])
    assert all(x["era"] in {"17", "18", "19", "20"} for x in data["items"])
    assert {x["era"] for x in data["items"]} == {"17", "18", "19", "20"}
    assert {x["city"] for x in data["items"]} >= {"Париж", "Лондон", "Рим", "Амстердам", "Венеция", "Руан"}


@pytest.mark.parametrize("invalid", [
    "http://openaccess-cdn.clevelandart.org/1946.36.21/1946.36.21_web.jpg",
    "https://example.com/foo_web.jpg",
    "https://openaccess-cdn.clevelandart.org/1946.36.21/1946.36.21_print.jpg",
    "https://openaccess-cdn.clevelandart.org.evil.net/foo_web.jpg",
])
def test_asset_ingestor_blocks_unreviewed_urls(invalid):
    sample = json.loads(CATALOG.read_text(encoding="utf-8"))["items"][0]
    with pytest.raises(ValueError):
        validated_url({**sample, "image": invalid})


def test_public_atlas_links_both_sources_and_true_modern_photo():
    html = (ROOT / "journeys/index.html").read_text(encoding="utf-8")
    assert "cc0-gallery-20261103.json" in html
    assert "zoomDialog" in html
    assert "image_large" in html
    assert "data-route=\"london\"" in html
    assert "madeleine-photo-panoramax-38b6d262.jpg" in html
    assert "ракурсы различаются" in html.lower()
    assert "Cleveland Museum of Art" in html


def test_four_real_modern_photos_are_cc0_and_not_pretend_aligned():
    modern = json.loads((ROOT / "data/curation/modern-photos-cc0-20261103.json").read_text(encoding="utf-8"))
    historic = json.loads(CATALOG.read_text(encoding="utf-8"))
    available = {item["id"] for item in historic["items"]}
    assert len(modern["items"]) == 4
    for photo in modern["items"]:
        assert photo["rights"] == "cc0"
        assert photo["verified"] == "commons_api"
        assert photo["alignment"] == "not_evaluated"
        assert photo["historic_ref"] in available
        assert photo["date"].startswith("2024") or photo["date"].startswith("2025")
        assert photo["photographer"]
        assert urlsplit(photo["source_page"]).hostname == "commons.wikimedia.org"
        assert validated_photo_url(photo).startswith("https://thumb.wikimedia.org/")


def test_modern_image_ingestor_rejects_untrusted_host():
    modern = json.loads((ROOT / "data/curation/modern-photos-cc0-20261103.json").read_text(encoding="utf-8"))
    photo = modern["items"][0]
    with pytest.raises(ValueError):
        validated_photo_url({**photo, "image": "https://evil.invalid/commons/thumb/picture.jpg"})
    with pytest.raises(ValueError):
        validated_photo_url({**photo, "rights": "unknown"})
