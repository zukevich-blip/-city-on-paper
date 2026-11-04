"""Offline regression tests for museum archive API normalization and rights gating."""
from tools.curation.expand_open_archives import make_cma, score, tier, year_to_era


def demo_record(rights: str = "CC0") -> dict:
    return {
        "share_license_status": rights, "accession_number": "1922.225",
        "title": "View of the City of Rome", "technique": "etching",
        "images": {
            "web": {"url": "https://openaccess-cdn.clevelandart.org/1922.225/1922.225_web.jpg",
                    "width": "1200"},
            "print": {"url": "https://openaccess-cdn.clevelandart.org/1922.225/1922.225_print.jpg",
                      "width": "3200"},
        },
        "creators": [{"description": "Giovanni Battista Piranesi"}],
        "url": "https://www.clevelandart.org/art/1922.225",
        "creation_date": "1740", "creation_date_earliest": 1740,
    }


def test_source_and_rights_validation():
    item, relevance = make_cma(demo_record(), "Рим", "Rome")
    assert item["rights"] == "cc0"
    assert item["verified"] == "museum_api"
    assert item["selection"] == "machine_selected_title_relevance"
    assert item["url"].startswith("https://")
    assert item["quality_tier"] == "высокое"
    assert item["era"] == "18"
    assert relevance >= 4
    assert make_cma(demo_record("Copyrighted"), "Рим", "Rome") is None
    assert make_cma(demo_record("Other"), "Рим", "Rome") is None


def test_relevance_does_not_include_unrelated_portraits():
    assert score("Portrait of a Lady", "oil painting", "Paris") < 0
    assert score("City Market in Paris", "color lithograph", "Paris") > 4
    assert score("Vase with ornaments", "ceramic", "Venice") < 0


def test_fidelity_classification_is_explicit():
    assert tier(3300) == "высокое"
    assert tier(1200) == "экранное"
    assert tier(400) == "разрешение не определено"
    assert tier(None, True) == "есть оригинал"
    assert year_to_era(1860) == "19"
    assert year_to_era(None) == ""
