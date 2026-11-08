"""Offline review-renderer checks, using synthetic pixels and genuine stored GCP JSON."""
import json
import math
from pathlib import Path

import pytest
from PIL import Image

from tools.iiif.render_paris_gcp_review import affine, generate, metric, modern_crop

ROOT = Path(__file__).resolve().parents[1]
GEO = json.loads((ROOT / "data/vision-lab/georef-paris-1878.json").read_text("utf-8"))


def test_stored_affine_fit_can_be_recomputed_but_is_not_truth():
    p = GEO["gcps"][0]
    predicted = affine(p["px"], p["py"], GEO)
    actual = metric(p["lon"], p["lat"], GEO)
    residual = math.dist(predicted, actual)
    assert abs(residual - p["residual_affine_m"]) < 0.2
    assert residual > 20


def test_six_historic_panels_can_be_generated_without_synthetic_satellite(tmp_path):
    image = Image.new("RGB", (800, 580), "#d9c9b0")  # synthetic test raster, never publish
    report = generate(GEO, image, tmp_path)
    assert len(report["points"]) == 6
    assert report["publication_status"] == "research_only"
    assert report["modern_image"] == "NOT PROVIDED: diagram only"
    assert "не предоставлена" in (tmp_path / "index.html").read_text("utf-8")
    for i in range(1, 7):
        image_path = tmp_path / f"gcp-{i:02d}.png"
        assert image_path.is_file()
        with Image.open(image_path) as output:
            assert output.width > 1000 and output.height > 500
    assert (tmp_path / "overview.png").exists()
    assert (tmp_path / "review.json").exists()


def test_modern_raster_requires_attribution_and_bounds(tmp_path):
    image = Image.new("RGB", (40, 40))
    with pytest.raises(ValueError, match="together"):
        generate(GEO, image, tmp_path, modern=image)
    with pytest.raises(ValueError, match="attribution"):
        generate(GEO, image, tmp_path, modern=image, bounds=(2, 48, 3, 49))


def test_modern_image_requires_full_geographic_coverage():
    image = Image.new("RGB", (500, 500))
    with pytest.raises(ValueError, match="does not cover"):
        modern_crop(image, 2.34, 48.85, (2.339, 48.849, 2.341, 48.851), 600)
