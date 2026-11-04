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


def test_historic_prints_are_not_labeled_contemporary_photographs():
    old = fixture()
    old["title"] = "File:Gezicht op La Madeleine te Parijs RP-F-00-3983.jpg"
    old["imageinfo"][0]["extmetadata"]["DateTimeOriginal"]["value"] = "ca. 1875 - ca. 1900"
    assert parse_photo(old, "Париж", "La Madeleine") is None
    old = fixture()
    old["title"] = "File:View of the Cathedral in 1890.jpg"
    old["imageinfo"][0]["extmetadata"]["DateTimeOriginal"]["value"] = "1889"
    assert parse_photo(old, "Париж", "cathedral") is None


def test_cross_city_milan_result_not_mislabeled_florence():
    wrong = fixture()
    wrong["title"] = "File:Milano-Piazza del Duomo photo.jpg"
    assert parse_photo(wrong, "Флоренция", "Florence Cathedral") is None
