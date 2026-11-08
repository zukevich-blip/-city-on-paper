"""Guard the three-item evidence pilot and the existing Paris GCPs (no network)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "data" / "research"
CATALOG = json.loads((RESEARCH / "iiif-pilot-3-works-paris-20261109.json").read_text("utf-8"))
GEO = json.loads((ROOT / "data/vision-lab/georef-paris-1878.json").read_text("utf-8"))
ANNOTATION = json.loads((RESEARCH / "paris-1878-georeference-draft.json").read_text("utf-8"))


def test_three_real_catalog_records_have_unique_source_ids_and_no_fictional_zoom():
    records = CATALOG["records"]
    assert {r["record_id"] for r in records} == {
        "loc-2016652452", "loc-2016652451", "loc-2013650023"
    }
    for record in records:
        identifier = record["record_id"].removeprefix("loc-")
        assert record["item_url"] == f"https://www.loc.gov/item/{identifier}/"
        assert record["iiif_manifest_url"] == record["item_url"] + "manifest.json"
        assert record["iiif_manifest_canvas_count"] == 0
        assert record["iiif_image_service_url"] is None
        assert record["fallback_url"] == record["item_url"]
        assert record["publication_status"] == "research_only"
        assert record["artist_viewpoint"] is None
        assert record["rights_class"] != "CC0"
        assert "not_cc0" in record["rights_class"]
        assert "legal_review" in record["rights_review_status"]


def test_map_source_is_a_real_image_service_not_a_fabricated_city_api():
    record = CATALOG["map"]
    source = ANNOTATION["target"]["source"]
    assert record["item_url"] == "https://www.loc.gov/item/2012586603/"
    assert record["iiif_image_service_url"] == GEO["iiif_service"] == source["id"]
    assert source["type"] == "ImageService2"
    assert (source["width"], source["height"]) == (15705, 11378)
    assert record["canvas_count"] == 1
    assert record["publication_status"] == "research_only"


def test_georeference_uses_exact_existing_pixel_and_wgs84_pairs():
    pairs = ANNOTATION["body"]["features"]
    gcps = GEO["gcps"]
    assert len(pairs) == len(gcps) >= 6
    assert ANNOTATION["motivation"] == "georeferencing"
    assert ANNOTATION["body"]["transformation"] == {
        "type": "polynomial", "options": {"order": 1}
    }
    for feature, gcp in zip(pairs, gcps):
        assert feature["properties"]["resourceCoords"] == [gcp["px"], gcp["py"]]
        assert feature["geometry"] == {
            "type": "Point", "coordinates": [gcp["lon"], gcp["lat"]]
        }
        assert feature["properties"]["confidence"] in {"high", "medium", "low"}
        x, y = feature["properties"]["resourceCoords"]
        assert 0 <= x <= 15705
        assert 0 <= y <= 11378


def test_approximate_mask_stays_within_source_and_is_not_a_fake_full_image():
    value = ANNOTATION["target"]["selector"]["value"]
    assert ANNOTATION["target"]["selector"]["type"] == "SvgSelector"
    assert value.startswith("<svg") and "<polygon points=" in value
    points = re.search(r'points="([^"]+)"', value).group(1).split()
    assert len(points) >= 3
    for point in points:
        x, y = map(int, point.split(","))
        assert 0 <= x <= 15705 and 0 <= y <= 11378
    assert CATALOG["map"]["annotation_status"].startswith("draft")


def test_reported_residuals_are_explicitly_not_independently_verified():
    record = CATALOG["map"]
    assert record["affine_rms_m_reported_in_source"] == GEO["transforms"]["affine"]["rms_m"]
    assert record["affine_leave_one_out_rms_m_reported_in_source"] == (
        GEO["transforms"]["affine"]["loo_rms_m"]
    )
    assert "not independently verified" in record["annotation_status"]
