"""Offline tests for legally sourced French IGN orthophoto review requests."""
import json
import math
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PIL import Image

from tools.iiif.render_ign_ortho_review import (
    ATTRIBUTION,
    ORTHO_LAYER,
    WMS_ENDPOINT,
    render,
    wms_getmap_url,
)
from tools.iiif.render_paris_gcp_review import generate

ROOT = Path(__file__).resolve().parents[1]
GEO = json.loads((ROOT / "data/vision-lab/georef-paris-1878.json").read_text("utf-8"))


def test_official_wms_url_preserves_projection_and_unambiguous_licence():
    url = wms_getmap_url(48.87378, 2.29504)
    parsed = urlsplit(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    assert url.startswith(WMS_ENDPOINT + "?")
    assert query["REQUEST"] == ["GetMap"]
    assert query["LAYERS"] == [ORTHO_LAYER]
    assert query["CRS"] == ["EPSG:3857"]
    assert query["VERSION"] == ["1.3.0"]
    assert query["FORMAT"] == ["image/jpeg"]
    assert query["WIDTH"] == ["1024"]
    assert query["HEIGHT"] == ["1024"]
    assert "Etalab 2.0" in ATTRIBUTION
    # WMS BBOX defines projected metres, not an arbitrary JPEG pixel index.
    west, south, east, north = map(float, query["BBOX"][0].split(","))
    assert west < east and south < north
    assert math.isclose(east - west, north - south, rel_tol=0, abs_tol=0.02)


def test_render_mocked_photo_keeps_uncertainty_and_six_sources(tmp_path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    generate(GEO, Image.new("RGB", (800, 580), "#d9c9b0"), source_dir)
    count = []

    def synthetic_fetch(url):
        count.append(url)
        return Image.new("RGB", (1024, 1024), "#aab3bc")  # test fixture ONLY

    report = render(source_dir, output_dir, fetch=synthetic_fetch, pause=0)
    assert len(count) == len(report["records"]) == 6
    assert report["publication_status"] == "research_only"
    assert report["independent_gcp_review"] == "NOT_DONE"
    assert "capture year" in report["modern_attribution"]
    for record in report["records"]:
        assert record["human_review"] == "still_required"
        assert record["georeferencing_verified"] is False
        assert record["imagery_capture_year"] is None
        assert record["modern_image_wms_getmap"].startswith(WMS_ENDPOINT + "?")
        assert (output_dir / record["file"]).is_file()
    assert (output_dir / "index.html").exists()
    assert (output_dir / "overview.png").exists()
