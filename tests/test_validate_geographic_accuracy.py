"""Validation is research-only: no inferred scale, silent LOO omissions or approvals."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "validate_geographic_accuracy", ROOT / "tools/validate_geographic_accuracy.py"
)
validator = importlib.util.module_from_spec(spec)
sys.modules["validate_geographic_accuracy"] = validator
spec.loader.exec_module(validator)


def fixture(tmp_path):
    points = [(100, 130), (500, 150), (750, 450), (350, 650),
              (120, 680), (900, 800), (850, 250), (330, 345)]
    sha_h = "1" * 64
    sha_r = "2" * 64
    h = [[1, 0, 10], [0, 1, -4], [0, 0, 1]]
    gt = [2.0, 0.0001, 0, 49.0, 0, -0.0001]
    candidate = {
        "schema_version": "city-on-paper.gcp-candidates.v1",
        "scientific_accuracy_verified": False,
        "status": "candidate_auto",
        "source": {"sha256": sha_h, "width": 1000, "height": 1000},
        "reference": {"sha256": sha_r, "georeferencing": {
            "crs": "EPSG:4326", "geotransform": gt}},
        "homography_original_pixels": h,
    }
    controls = {
        "schema_version": "city-on-paper.independent-gcp-controls.v1",
        "historic_sha256": sha_h, "reference_sha256": sha_r,
        "points": [{
            "id": str(i), "historic_pixel": [x, y],
            "longitude_latitude": [2.0 + (x + 10) * 0.0001,
                                   49.0 - (y - 4) * 0.0001],
            "reviewer": "Independent reviewer",
            "evidence_url": "https://museum.example/landmark/" + str(i),
            "historic_landmark_checked": True,
            "modern_position_checked": True,
            "independent_of_orb": True,
        } for i, (x, y) in enumerate(points)],
    }
    c = tmp_path / "candidate.json"
    p = tmp_path / "controls.json"
    c.write_text(json.dumps(candidate), encoding="utf-8")
    p.write_text(json.dumps(controls), encoding="utf-8")
    return c, p, candidate, controls


def test_real_research_paris_1878_recomputes_but_not_certifies():
    source = ROOT / "data/vision-lab/georef-paris-1878.json"
    data = validator.legacy_affine(source)
    assert data["landmarks"] == 15
    assert data["in_sample_rmse_meters"] == pytest.approx(25.94, abs=0.02)
    assert data["loo_rmse_meters"] == pytest.approx(34.90, abs=0.02)
    assert data["scientific_accuracy_verified"] is False
    assert data["approved_for_publication"] is False


def test_holdout_metric_is_zero_on_exact_independent_coordinates(tmp_path):
    c, p, _, _ = fixture(tmp_path)
    result = validator.validate_candidate(c, p)
    assert result["number_of_holdout_points"] == 8
    assert result["rmse_meters"] == pytest.approx(0, abs=1e-3)
    assert result["scientific_accuracy_verified"] is False
    assert result["approved_for_publication"] is False


def test_holdout_error_is_geodesic_not_guessed_pixel_scale(tmp_path):
    c, p, _, controls = fixture(tmp_path)
    controls["points"][0]["longitude_latitude"][0] += 0.001
    p.write_text(json.dumps(controls), encoding="utf-8")
    result = validator.validate_candidate(c, p)
    assert result["rmse_meters"] > 20
    assert result["approved_for_publication"] is False


def test_missing_evidence_causes_explicit_refusal(tmp_path):
    c, p, _, controls = fixture(tmp_path)
    controls["points"][0].pop("evidence_url")
    p.write_text(json.dumps(controls), encoding="utf-8")
    with pytest.raises(validator.ValidationError, match="independent review"):
        validator.validate_candidate(c, p)


def test_candidate_fails_on_missing_or_wrong_raster_sha(tmp_path):
    c, p, _, controls = fixture(tmp_path)
    controls["reference_sha256"] = "wrong"
    p.write_text(json.dumps(controls), encoding="utf-8")
    with pytest.raises(validator.ValidationError, match="reference_sha256"):
        validator.validate_candidate(c, p)


def test_candidate_fails_without_real_raster_georeferencing(tmp_path):
    c, p, cand, _ = fixture(tmp_path)
    cand["reference"]["georeferencing"] = None
    c.write_text(json.dumps(cand), encoding="utf-8")
    with pytest.raises(validator.ValidationError, match="CRS"):
        validator.validate_candidate(c, p)


def test_fewer_than_six_points_is_not_reported_as_pass(tmp_path):
    c, p, _, controls = fixture(tmp_path)
    controls["points"] = controls["points"][:5]
    p.write_text(json.dumps(controls), encoding="utf-8")
    with pytest.raises(validator.ValidationError, match="six"):
        validator.validate_candidate(c, p)


def test_singular_or_nonfinite_matrix_is_refused(tmp_path):
    c, p, cand, _ = fixture(tmp_path)
    cand["homography_original_pixels"] = np.zeros((3, 3)).tolist()
    c.write_text(json.dumps(cand), encoding="utf-8")
    with pytest.raises(validator.ValidationError, match="Invalid homography"):
        validator.validate_candidate(c, p)


def test_legacy_collinear_points_cannot_pass_loo(tmp_path):
    data = {
        "gcps": [{"name": str(i), "px": i * 10, "py": i * 20,
                  "lon": 2 + i * 0.01, "lat": 48 + i * 0.01}
                 for i in range(5)],
        "pixel_space": {"width": 500, "height": 500},
        "local_projection": {
            "lon0": 2.0, "lat0": 48.0, "R_m": 6378137.0},
    }
    p = tmp_path / "legacy.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(validator.ValidationError, match="degenerate"):
        validator.legacy_affine(p)


def test_cli_produces_research_only_json(tmp_path):
    source = ROOT / "data/vision-lab/georef-paris-1878.json"
    output = tmp_path / "audit.json"
    assert validator.main is not None
    import subprocess

    run = subprocess.run(
        [sys.executable, str(ROOT / "tools/validate_geographic_accuracy.py"),
         "--legacy-paris", str(source), "--output", str(output)],
        capture_output=True, text=True, check=False,
    )
    assert run.returncode == 0, run.stderr
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["assessment"] == "research_only"
    assert data["scientific_accuracy_verified"] is False
