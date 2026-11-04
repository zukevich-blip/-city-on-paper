"""Offline fixture checks for Commons metadata; attribution must survive hotlinking."""
from tools.curation.build_modern_city_photos import parse_photo


def fixture():
    return {
        "pageid": 2997824, "ns": 6,
        "title": "File:Notre Dame Paris front facade lower.jpg",
        "imageinfo": [{
            "mime": "image/jpeg", "width": 3880, "height": 2097,
            "thumburl": (
                "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/42/"
                "Notre_Dame_Paris_front_facade_lower.jpg/1280px-photo.jpg"
            ),
            "url": "https://upload.wikimedia.org/wikipedia/commons/4/42/Notre_Dame_Paris_front_facade_lower.jpg",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Notre_Dame_Paris_front_facade_lower.jpg",
            "user": "Benh",
            "extmetadata": {
                "LicenseShortName": {"value": "CC BY-SA 3.0"},
                "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/3.0"},
                "Artist": {"value": "Benh LIEU SONG"},
                "DateTimeOriginal": {"value": "2007-10-28"},
            },
        }],
    }


def test_real_commons_style_thumbnail_host_and_author():
    pic = parse_photo(fixture(), "Париж", "Notre Dame Paris")
    assert pic is not None
    assert pic["rights"] == "CC BY-SA 3.0"
    assert pic["maker"] == "Benh LIEU SONG"
    assert pic["date_taken"] == "2007-10-28"
    assert pic["quality_tier"] == "высокое"
    assert pic["can_exact_overlay"] is False
    assert pic["image"].startswith("https://thumb.wikimedia.org/")
    assert pic["license_url"] == "https://creativecommons.org/licenses/by-sa/3.0/"


def test_reject_unsafe_or_missing_license():
    page = fixture()
    page["imageinfo"][0]["extmetadata"]["LicenseShortName"]["value"] = "All rights reserved"
    assert parse_photo(page, "Париж", "Notre Dame") is None
    page = fixture()
    page["imageinfo"][0]["thumburl"] = "https://untrusted.example/pic.jpg"
    assert parse_photo(page, "Париж", "Notre Dame") is None
