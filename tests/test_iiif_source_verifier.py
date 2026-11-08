"""No-network verification tests for source changes and prohibited URLs."""
import pytest

from tools.iiif.verify_pilot_sources import fetch_json, verify


def test_rejects_untrusted_url_before_network():
    with pytest.raises(ValueError):
        fetch_json("https://example.org/item/2016652452/manifest.json")
    with pytest.raises(ValueError):
        fetch_json("http://www.loc.gov/item/2016652452/manifest.json")
    with pytest.raises(ValueError):
        fetch_json("https://www.loc.gov/item/2016652452/?fo=json")


def test_detects_manifest_without_canvas_and_checks_real_map_dimensions():
    art_url = "https://www.loc.gov/item/2016652452/manifest.json"
    map_url = "https://www.loc.gov/item/2012586603/manifest.json"
    info_url = "https://tile.loc.gov/image-services/iiif/known/info.json"
    catalog = {
        "records": [{"record_id": "loc-art", "iiif_manifest_url": art_url,
                     "iiif_manifest_canvas_count": 0}],
        "map": {"record_id": "loc-map", "iiif_manifest_url": map_url,
                "iiif_image_info_url": info_url, "iiif_image_service_url": info_url.removesuffix("/info.json"),
                "canvas_count": 1, "source_width": 15705, "source_height": 11378},
    }
    def response(url):
        if url == art_url:
            return {"@id": art_url, "@type": "sc:Manifest", "label": "Original print"}
        if url == map_url:
            return {"@id": map_url, "@type": "sc:Manifest", "label": "Paris map",
                    "sequences": [{"canvases": [{"images": []}]}]}
        if url == info_url:
            return {"@id": info_url.removesuffix("/info.json"), "width": 15705, "height": 11378}
        raise AssertionError("Unexpected URL")

    report = verify(catalog, fetch=response)
    assert report["all_expected_counts_match"]
    assert report["publication_status"] == "never_auto_publish"
    assert report["records"][0]["canvas_count"] == 0
    assert report["records"][1]["image_info_matches_catalog"]


def test_detects_metadata_drift_without_automatically_publishing():
    url = "https://www.loc.gov/item/1/manifest.json"
    catalog = {
        "records": [{"record_id": "one", "iiif_manifest_url": url,
                     "iiif_manifest_canvas_count": 0}],
        "map": {"record_id": "two", "iiif_manifest_url": url,
                "iiif_image_info_url": "https://tile.loc.gov/iiif/1/info.json",
                "iiif_image_service_url": "https://tile.loc.gov/iiif/1",
                "canvas_count": 1, "source_width": 100, "source_height": 100},
    }

    def response(value):
        if value.endswith("/manifest.json"):
            return {"@id": url, "@type": "sc:Manifest", "label": "Changed"}
        return {"@id": "https://tile.loc.gov/iiif/1", "width": 100, "height": 100}

    report = verify(catalog, fetch=response)
    assert not report["all_expected_counts_match"]
    assert report["records"][1]["canvas_count_matches_catalog"] is False
    assert report["publication_status"] == "never_auto_publish"
