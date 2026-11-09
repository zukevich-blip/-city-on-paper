"""Numerical checks for guarded city-agnostic research map alignment."""
import pytest

from tools.maps.fit_city_gcps import compute


def valid_fixture():
    def pt(px, py):
        u, v = px / 1000, py / 1000
        return {
            "px": px, "py": py,
            "lon": 2.3 + 0.025 * u + 0.003 * v,
            "lat": 48.85 + 0.006 * u - 0.022 * v,
        }

    return {
        "city_id": "generic-historic-city",
        "map_id": "archival-print-1884",
        "image": {
            "width": 1000, "height": 800,
            "source_url": "https://www.loc.gov/item/example/",
        },
        "gcps": [
            pt(60, 50), pt(900, 40), pt(910, 700),
            pt(100, 740), pt(500, 420), pt(400, 150),
        ],
        "holdouts": [pt(230, 280), pt(730, 550)],
    }


def test_generic_geo_model_fits_affine_with_true_holdouts():
    result = compute(valid_fixture())
    assert result["city_id"] == "generic-historic-city"
    assert result["control_points_used"] == 6
    assert result["holdout_points_not_used_in_fit"] == 2
    assert result["internal_rms_m"] < 0.0001
    assert result["loo_rms_m"] < 0.0001
    assert result["holdout_rms_m"] < 0.0001
    assert result["independent_expert_review"] is False
    assert result["georeference_status"].startswith("research_only")


def test_no_fit_from_three_gcps_even_if_affine_would_interpolate():
    doc = valid_fixture()
    doc["gcps"] = doc["gcps"][:3]
    with pytest.raises(ValueError, match="at least 4"):
        compute(doc)


def test_degenerate_gcps_rejected():
    doc = valid_fixture()
    doc["gcps"] = [
        {"px": i * 100, "py": i * 100,
         "lon": 2.3 + i / 100, "lat": 48.85 + i / 100}
        for i in range(5)
    ]
    with pytest.raises(ValueError, match="Degenerate"):
        compute(doc)


def test_inaccurate_holdouts_are_reported_not_removed():
    doc = valid_fixture()
    doc["holdouts"][1]["lon"] += 0.001
    result = compute(doc)
    assert result["internal_rms_m"] < 0.0001
    assert result["holdout_rms_m"] > 30
    assert result["independent_expert_review"] is False


def test_dateline_or_large_geography_requires_gis_specialist():
    doc = valid_fixture()
    doc["gcps"][0]["lon"] = 170
    with pytest.raises(ValueError, match="large-area or dateline"):
        compute(doc)


def test_out_of_image_and_polar_coordinates_rejected():
    doc = valid_fixture()
    doc["gcps"][0]["py"] = 1500
    with pytest.raises(ValueError, match="outside archival raster"):
        compute(doc)
    doc = valid_fixture()
    doc["gcps"][0]["lat"] = 86
    with pytest.raises(ValueError, match="outside supported"):
        compute(doc)
