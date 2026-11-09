"""Validate map-source shelf and international source evidence without promoting map candidates."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_shelf_has_only_source_identified_city_maps():
    content = json.loads((ROOT / "eras/data/map-evidence.json").read_text("utf-8"))
    items = content["items"]
    assert {"paris", "london", "rim"} <= {x["city_id"] for x in items}
    assert content["publication_status"] == "source_evidence_only_not_georeferenced"
    for item in items:
        assert item["status"] == "catalogue_source_checked"
        assert item["object_url"].startswith("https://www.loc.gov/item/")
        assert item["georeferencing_status"] in (
            "research_affine_not_independently_verified", "not_attempted"
        )
        assert item["image_api_status"] != "unconditionally_verified_HD"


def test_worldwide_research_sources_distinguish_flat_and_perspective():
    content = json.loads(
        (ROOT / "data/research/global-city-historic-map-evidence-20261109.json")
        .read_text("utf-8")
    )
    items = content["items"]
    assert len(items) >= 7
    assert all(x["manual_landmark_validation"] is False for x in items)
    assert all(x["source_url"].startswith("https://www.loc.gov/item/") for x in items)
    perspective = [x for x in items if "perspective" in x["map_type"]]
    assert perspective
    assert all(x["georeferencing_status"] == "not_applicable_as_plan" for x in perspective)
    assert any(x["city"] == "Токио (Эдо)" for x in items)
    assert any(x["city"] == "Рио-де-Жанейро" for x in items)
    assert all(x["atlas_id"] is None for x in items if x["city"] == "Токио (Эдо)")


def test_global_research_shelf_wired_to_original_atlas_not_standalone_replacement():
    page = (ROOT / "eras/index.html").read_text("utf-8")
    atlas = (ROOT / "eras/atlas.js").read_text("utf-8")
    viewer = (ROOT / "eras/cartography.js").read_text("utf-8")
    assert 'src="cartography.js"' in page
    assert 'id="historicCartography"' in atlas
    assert "CityHistoricCartography.mount" in atlas
    assert 'fetch("data/map-evidence.json")' in viewer
    assert 'https://www.loc.gov/maps/?q=' in viewer
