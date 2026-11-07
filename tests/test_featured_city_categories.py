"""Category memberships give stronger city evidence, but not invented rights."""
from tools.curation.build_world_graphics import normalize
from tools.curation.enrich_city_categories import CATEGORIES, api_category

FLORENCE = {
    "name": "Флоренция", "country": "Италия", "region": "Европа",
    "query": "Florence city lithograph",
}


def page(title="File:Telemaco Signorini acquaforte, Via degli Speziali, 1874.jpg"):
    return {
        "ns": 6, "pageid": 98001, "title": title,
        "imageinfo": [{
            "mime": "image/jpeg", "width": 2300, "height": 1500,
            "url": "https://upload.wikimedia.org/wikipedia/commons/1/13/art.jpg",
            "thumburl": (
                "https://thumb.wikimedia.org/wikipedia/commons/"
                "thumb/1/13/art.jpg/1000px-art.jpg"
            ),
            "descriptionurl": (
                "https://commons.wikimedia.org/wiki/"
                "File:Telemaco_Signorini_acquaforte_Via_degli_Speziali.jpg"
            ),
            "extmetadata": {
                "LicenseShortName": {"value": "Public domain"},
                "Copyrighted": {"value": "False"},
                "Artist": {"value": "Telemaco Signorini"},
            },
        }],
    }


def test_direct_category_membership_enables_florence_street_etching():
    record = page()
    assert normalize(record, FLORENCE) is None  # title lacks city name
    art, rank = normalize(record, FLORENCE, "Category:Mercato Vecchio (Florence) in art")
    assert art["city"] == "Флоренция"
    assert rank >= 3
    assert art["geography_confidence"] == "commons_category"
    assert art["rights"] == "public_domain_commons"
    assert art["source_id"] == record["title"]
    assert "Mercato_Vecchio_(Florence)" in art["category_source_url"]


def test_category_does_not_override_copyright_or_excluded_portrait():
    record = page()
    record["imageinfo"][0]["extmetadata"]["LicenseShortName"]["value"] = "Copyrighted"
    assert normalize(record, FLORENCE, "Category:Mercato Vecchio (Florence) in art") is None
    bad = page("File:Portrait of a Lady, Firenze.jpg")
    assert normalize(bad, FLORENCE, "Category:Mercato Vecchio (Florence) in art") is None


def test_preapproved_specific_art_categories_only():
    assert len(CATEGORIES) == 10
    assert ("Флоренция", "Mercato Vecchio (Florence) in art") in CATEGORIES
    assert ("Венеция", "Etchings of Venice") in CATEGORIES
    assert ("Неаполь", "Lithographs of Naples") in CATEGORIES
    try:
        api_category("Category:Unrelated copyrighted portraits")
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown category should be rejected before API call")
