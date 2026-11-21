"""Offline checks for the Commons modern-photo collector: parsing, filters and ranking (no network)."""
from __future__ import annotations

from tools.world import collect_modern_photos as cm

TARGET = {"id": "t", "name": "t", "lat": 41.89861, "lon": 12.47686, "radius": 160}


def page(title="File:A.jpg", **over):
    base = {
        "title": title,
        "coordinates": [{"lat": 41.8990, "lon": 12.4770}],
        "imageinfo": [{
            "mime": "image/jpeg", "width": 4000, "height": 3000, "url": "https://upload.example/a.jpg",
            "thumburl": "https://upload.example/t.jpg", "descriptionurl": "https://commons.example/File:A.jpg",
            "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"}, "Artist": {"value": "<a href='x'>Ann</a>"},
                            "DateTimeOriginal": {"value": "2025-03-03 14:22:11"}},
            "metadata": [{"name": "GPSImgDirection", "value": "18000/100"}],
        }],
    }
    base.update(over)
    return base


def test_accepts_free_recent_jpeg_with_direction():
    c = cm.candidate_from_page(page(), TARGET)
    assert c and c["taken"] == "2025-03-03" and c["author"] == "Ann" and c["licence"] == "CC BY-SA 4.0"
    assert c["camera"]["heading_deg"] == 180.0
    assert c["needs_review"] is True
    assert 0 <= c["camera"]["bearing_to_target_deg"] <= 360


def test_rejects_non_free_old_small_or_missing_date():
    for mutate in (
        lambda p: p["imageinfo"][0]["extmetadata"].update(LicenseShortName={"value": "All rights reserved"}),
        lambda p: p["imageinfo"][0]["extmetadata"].update(DateTimeOriginal={"value": "2009-01-01 10:00:00"}),
        lambda p: p["imageinfo"][0]["extmetadata"].pop("DateTimeOriginal"),
        lambda p: p["imageinfo"][0].update(width=800),
        lambda p: p["imageinfo"][0].update(mime="image/png"),
        lambda p: p.update(coordinates=[]),
    ):
        p = page()
        mutate(p)
        assert cm.candidate_from_page(p, TARGET) is None


def test_missing_direction_is_kept_as_unknown():
    p = page()
    p["imageinfo"][0]["metadata"] = []
    c = cm.candidate_from_page(p, TARGET)
    assert c and c["camera"]["heading_deg"] is None and c["camera"]["heading_error_deg"] is None


def test_ranking_prefers_newest_then_facing_target():
    old = cm.candidate_from_page(page(), TARGET)
    p = page()
    p["imageinfo"][0]["extmetadata"]["DateTimeOriginal"] = {"value": "2026-05-01 09:00:00"}
    new = cm.candidate_from_page(p, TARGET)
    assert sorted([old, new], key=cm.rank_key, reverse=True)[0] is new


def test_geometry_helpers():
    assert cm.angle_diff(350, 10) == 20
    assert round(cm.bearing(0, 0, 1, 0)) == 0 and round(cm.bearing(0, 0, 0, 1)) == 90
    assert cm.rational("18000/100") == 180.0 and cm.rational("abc") is None
    assert cm.parse_when("2025:03:03 14:22:11") == "2025-03-03" and cm.parse_when("0000-00-00") is None


def test_targets_are_unique_and_have_coordinates():
    ids = [t["id"] for t in cm.TARGETS]
    assert len(ids) == len(set(ids))
    assert all(-90 <= t["lat"] <= 90 and -180 <= t["lon"] <= 180 and t["radius"] <= 1000 for t in cm.TARGETS)
