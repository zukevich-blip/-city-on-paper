"""Deterministic negative and positive tests; synthetic registration != real accuracy."""
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gcp = load_module("automated_gcp", "automated_gcp.py")
integration = load_module("integration_check", "integration_check.py")


def make_test_images(tmp_path):
    rng = np.random.default_rng(13579)
    image = np.full((850, 1100), 246, np.uint8)
    for i in range(110):
        x, y = rng.integers(50, 1050), rng.integers(50, 800)
        c = int(rng.integers(0, 190))
        cv2.circle(image, (int(x), int(y)), int(rng.integers(5, 16)), c, 2)
        if i % 3 == 0:
            cv2.line(image, (int(x), int(y)),
                     (int(x + rng.integers(-25, 26)), int(y + rng.integers(-25, 26))), c, 3)
    cv2.putText(image, "PARIS 1870", (110, 130), cv2.FONT_HERSHEY_COMPLEX, 2.0, 25, 4)
    matrix = cv2.getRotationMatrix2D((550, 425), 3.5, 0.97)
    matrix[:, 2] += [13, -9]
    target = cv2.warpAffine(image, matrix, (1100, 850), borderValue=255)
    historic = tmp_path / "source.png"
    reference = tmp_path / "reference.png"
    assert cv2.imwrite(str(historic), image)
    assert cv2.imwrite(str(reference), target)
    return historic, reference


def test_pixel_correspondence_never_accepted_as_surveyed(tmp_path):
    historic, reference = make_test_images(tmp_path)
    out = tmp_path / "deep" / "pair.json"
    data = gcp.run(historic, reference, out, max_dimension=1200)
    assert out.exists()
    assert data["status"] == "candidate_auto", data["metrics"]
    assert len(data["gcp_pairs"]) >= 12
    assert data["residual_rmse_meters"] is None
    assert data["review_required"] is True
    assert data["scientific_accuracy_verified"] is False
    assert all(p["status"] == "unverified_machine_match" for p in data["gcp_pairs"])
    assert data["metrics"]["rmse_reference_pixels"] < 4


def test_georeferenced_residual_is_explicitly_not_accuracy(tmp_path):
    historic, reference = make_test_images(tmp_path)
    georef = tmp_path / "reference-georef.json"
    georef.write_text(json.dumps({"crs": "EPSG:32631", "geotransform":
                                   [450000, 0.8, 0, 5410000, 0, -0.8]}))
    data = gcp.run(historic, reference, tmp_path / "out.json", georef_path=georef)
    assert data["status"] == "candidate_auto", data["metrics"]
    assert 0 <= data["residual_rmse_meters"] < 10
    assert all(len(p["longitude_latitude"]) == 2 for p in data["gcp_pairs"])
    assert data["scientific_accuracy_verified"] is False


def test_no_features_fails_and_writes_fail_status(tmp_path):
    a = np.full((500, 500), 255, np.uint8)
    p1, p2 = tmp_path / "one.png", tmp_path / "two.png"
    cv2.imwrite(str(p1), a)
    cv2.imwrite(str(p2), a)
    data = gcp.run(p1, p2, tmp_path / "failed.json")
    assert data["status"] == "auto_fail"
    assert data["gcp_pairs"] == []
    assert data["residual_rmse_meters"] is None


def test_invalid_georef_rejected(tmp_path):
    historic, reference = make_test_images(tmp_path)
    file = tmp_path / "georef.json"
    file.write_text(json.dumps({"crs": "EPSG:4326", "geotransform": [0, 0, 0, 0, 0, 0]}))
    with pytest.raises(gcp.GeoreferenceError, match="Singular"):
        gcp.run(historic, reference, tmp_path / "out.json", georef_path=file)


def test_bad_catalog_never_silently_passes(tmp_path):
    root = tmp_path / "public"
    root.mkdir()
    (root / "index.html").write_text("<html></html>")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps([{"image_url": "images/absent.jpg"}]))
    result = integration.validate_catalog(catalog, root)
    assert result["errors"]
    assert result["verified_local_assets"] == 0
    catalog.write_text(json.dumps([{"image_url": "https://museum.example/asset.jpg"}]))
    result = integration.validate_catalog(catalog, root)
    assert result["external_urls_unverified"] == 1
    assert result["verified_local_assets"] == 0


def test_candidate_validator_rejects_unearned_verified_status(tmp_path):
    folder = tmp_path / "cand"
    folder.mkdir()
    (folder / "test.json").write_text(json.dumps({
        "schema_version": "city-on-paper.gcp-candidates.v1", "status": "verified_auto",
        "review_required": False, "scientific_accuracy_verified": True, "gcp_pairs": []}))
    assert integration.validate_gcp_dir(folder)["errors"]


def test_site_auditor_missing_fails_closed(tmp_path):
    public = tmp_path / "public"
    public.mkdir()
    (public / "index.html").write_text("<html></html>")
    result = integration.check(public, tmp_path / "nonexistent-auditor.py")
    assert result["status"] == "FAIL"
    assert result["errors"]


def test_valid_site_only_passes_scoped(tmp_path):
    public = tmp_path / "public"
    public.mkdir()
    (public / "index.html").write_text("<html></html>")
    auditor = tmp_path / "audit.py"
    auditor.write_text("def check_site(root):\n    return {'broken_local_references': 0, 'html_pages': 1}\n")
    result = integration.check(public, auditor)
    assert result["status"] == "PASS_SCOPED"
    assert any("External HTTP" in x for x in result["not_checked"])


def test_resizing_preserves_full_resolution_pixel_coordinates(tmp_path):
    historic, reference = make_test_images(tmp_path)
    data = gcp.run(historic, reference, tmp_path / "resized.json", max_dimension=400)
    assert data["status"] == "candidate_auto"
    assert data["source"]["width"] == 1100
    assert data["method"]["max_dimension"] == 400
    assert len(data["source"]["sha256"]) == 64
    assert all(0 <= p["source_pixel"][0] <= 1100 and 0 <= p["source_pixel"][1] <= 850
               for p in data["gcp_pairs"])


def test_candidate_with_real_absent_iiif_context_is_not_allmaps_annotation(tmp_path):
    historic, reference = make_test_images(tmp_path)
    data = gcp.run(historic, reference, tmp_path / "out.json")
    assert "motivation" not in data
    assert "target" not in data
    assert "review_required" in data and data["review_required"]
