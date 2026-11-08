"""Static checks and independent math for the Paris opt-in Leaflet raster overlay.

The map and pixels are research evidence, never survey-grade coordinates.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = json.loads((ROOT / "data/vision-lab/georef-paris-1878.json").read_text("utf-8"))
OVERLAY = json.loads((ROOT / "eras/data/paris-1878-research-overlay.json").read_text("utf-8"))


def _predicted_lonlat(px: float, py: float) -> tuple[float, float]:
    m = OVERLAY["model"]
    w, h = OVERLAY["image_width"], OVERLAY["image_height"]
    u = px / w
    v = py / h * OVERLAY["source_image_height"] / OVERLAY["source_image_width"]
    e = sum(c * basis for c, basis in zip(m["coef_x_east_m"], (1, u, v), strict=True))
    n = sum(c * basis for c, basis in zip(m["coef_y_north_m"], (1, u, v), strict=True))
    lat = m["lat0"] + math.degrees(n / m["earth_radius_m"])
    lon = m["lon0"] + math.degrees(
        e / (m["earth_radius_m"] * math.cos(math.radians(m["lat0"])))
    )
    return lon, lat


def test_paris_overlay_is_research_only_and_clips_to_gcps():
    assert OVERLAY["city_id"] == "paris"
    assert OVERLAY["scope"] == "research_only"
    assert OVERLAY["verification"] == "manual_GCP_review_required"
    assert OVERLAY["image"] == "img/loc-2012586603-paris-1878.jpg"
    assert OVERLAY["source_catalogue"] == "https://www.loc.gov/item/2012586603/"
    assert len(OVERLAY["mask_pixel_polygon"]) >= 3
    for x, y in OVERLAY["mask_pixel_polygon"]:
        assert 0 <= x <= ORIGINAL["pixel_space"]["width"]
        assert 0 <= y <= ORIGINAL["pixel_space"]["height"]


def test_15_points_are_exactly_from_existing_source_not_reinvented():
    assert len(OVERLAY["gcps"]) == len(ORIGINAL["gcps"]) == 15
    for actual, expected in zip(OVERLAY["gcps"], ORIGINAL["gcps"], strict=True):
        for key in ("name", "lat", "lon", "px", "py"):
            assert actual[key] == expected[key]
        assert actual["confidence"] == expected["pick_confidence"]
        assert actual["residual_affine_m"] == expected["residual_affine_m"]
        assert actual["source"] == expected["coord_source"]


def test_image_to_geographic_projection_reproduces_published_error():
    m = OVERLAY["model"]
    residuals = []
    for p in OVERLAY["gcps"]:
        x = p["px"] * OVERLAY["image_width"] / OVERLAY["source_image_width"]
        y = p["py"] * OVERLAY["image_height"] / OVERLAY["source_image_height"]
        lon, lat = _predicted_lonlat(x, y)
        dx = math.radians(lon - p["lon"]) * m["earth_radius_m"] * math.cos(
            math.radians(m["lat0"])
        )
        dy = math.radians(lat - p["lat"]) * m["earth_radius_m"]
        residuals.append(math.hypot(dx, dy))
    rms = math.sqrt(sum(x * x for x in residuals) / len(residuals))
    assert abs(rms - ORIGINAL["transforms"]["affine"]["rms_m"]) < 0.1
    assert 20 < rms < 40  # Not proof that historical points were picked correctly.


def test_own_paris_module_is_wired_into_existing_leaflet_map():
    index = (ROOT / "eras/index.html").read_text("utf-8")
    maps = (ROOT / "eras/maps.js").read_text("utf-8")
    module = (ROOT / "eras/historical-overlay.js").read_text("utf-8")
    assert 'src="historical-overlay.js"' in index
    assert 'src="maps.js"' in index
    assert index.index('src="historical-overlay.js"') < index.index('src="maps.js"')
    assert 'c.id === "paris"' in maps
    assert "window.HistoricalOverlay.mount(now, street, c.id)" in maps
    assert "cop-paris-affine" in module
    assert "latLngToLayerPoint" in module
    assert "clipPath = maskCss(data)" in module
    assert "data.verification !== \"manual_GCP_review_required\"" in module


def test_ign_is_labelled_as_aerial_not_openstreetmap_satellite():
    module = (ROOT / "eras/historical-overlay.js").read_text("utf-8")
    assert "https://data.geopf.fr/wmts" in module
    assert "ORTHOIMAGERY.ORTHOPHOTOS" in module
    assert "Licence Ouverte 2.0" in module
    assert "2024" not in module  # Date of actual tile acquisition remains unknown.
    assert "google.com/maps" not in module
    assert "satellite.openstreetmap" not in module

def test_historic_layer_mask_does_not_cover_unverified_insets():
    # The map has two decorative inset maps; never project the entire sheet.
    poly = OVERLAY["mask_pixel_polygon"]
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    assert min(xs) > 0
    assert min(ys) > 0
    assert max(xs) < OVERLAY["source_image_width"]
    assert max(ys) < OVERLAY["source_image_height"]
    area = abs(sum(
        x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(
            poly, poly[1:] + poly[:1], strict=True
        )
    )) / 2
    total = OVERLAY["source_image_width"] * OVERLAY["source_image_height"]
    assert 0.05 * total < area < 0.75 * total

