"""Parsing-only tests for tools/world/search_other_authors.py (no network, inline fixtures)."""
# ruff: noqa: E501

from tools.world import search_other_authors as oa


def test_match_author_exact_forms_and_exclusions():
    assert (
        oa.match_author(["Giovanni Battista Piranesi (Italian, 1720-1778)"])[0]["slug"] == "giovanni-battista-piranesi"
    )
    assert oa.match_author(["Francesco Piranesi (Italian, 1758-1810)"]) is None
    assert oa.match_author(["Bernardo Bellotto, called Canaletto"])[0]["slug"] == "bernardo-bellotto"
    assert oa.match_author(["Canaletto"])[0]["slug"] == "canaletto"
    assert (
        oa.match_author(["Chapuy, Nicolas Marie Joseph (1790-1858). Dessinateur"])[0]["slug"]
        == "nicolas-marie-joseph-chapuy"
    )
    assert oa.match_author(["Eugène Cicéri"])[0]["slug"] == "eugene-ciceri"
    assert oa.match_author(["Pierre-Luc-Charles Cicéri"]) is None


def test_benois_never_confused_with_benoist():
    assert oa.match_author(["Benoist, Philippe (1813-1905)"]) is None
    assert oa.match_author(["Benoist, Félix"]) is None
    assert oa.match_author(["Alexandre Benois"])[0]["slug"] == "alexandre-benois"
    assert oa.match_author(["Benois, Albert"])[0]["slug"] == "albert-benois"
    assert oa.match_author(["Alexandre Benoist"]) is None


def test_detect_geo_is_literal():
    assert oa.detect_geo("Vue du Panthéon, Paris")[0] == "Paris"
    city, place, conf = oa.detect_geo("Veduta del Colosseo, Roma")
    assert (city, conf) == ("Rome", "building") and place.lower() == "colosseo"
    assert oa.detect_geo("Untitled landscape") == (None, None, "unknown")


def test_open_by_statement_does_not_accept_no_known_restrictions():
    assert oa.open_by_statement("https://creativecommons.org/publicdomain/zero/1.0/")
    assert oa.open_by_statement("http://creativecommons.org/publicdomain/mark/1.0/")
    assert oa.open_by_statement("https://creativecommons.org/licenses/by-sa/4.0/")
    assert not oa.open_by_statement("https://creativecommons.org/licenses/by-nc/4.0/")
    assert not oa.open_by_statement("No known restrictions on publication")
    assert not oa.open_by_statement("http://rightsstatements.org/vocab/InC/1.0/")
    assert not oa.open_by_statement(None)


CLEVELAND = {
    "id": 161941,
    "accession_number": "2001.19",
    "share_license_status": "CC0",
    "title": "The Temple of Isis at Pompeii",
    "creation_date": "1788",
    "technique": "etching",
    "type": "Print",
    "culture": ["Italy"],
    "url": "https://clevelandart.org/art/2001.19",
    "state_of_the_work": "state I/II",
    "creators": [
        {"description": "Francesco Piranesi (Italian, 1758-1810)", "role": "etched by"},
        {"description": "Giovanni Battista Piranesi (Italian, 1720-1778)", "role": "designed by"},
    ],
    "images": {
        "print": {
            "url": "https://openaccess-cdn.clevelandart.org/2001.19/2001.19_print.jpg",
            "width": "3400",
            "height": "2470",
        }
    },
}


def test_parse_cleveland_open_with_size_and_geo():
    r = oa.parse_cleveland(CLEVELAND)
    assert r["artist_id"] == "giovanni-battista-piranesi" and r["author_name"].startswith("Giovanni")
    assert r["rights_status"] == "open_confirmed" and (r["image_width"], r["image_height"]) == (3400, 2470)
    assert r["city"] == "Pompeii" and r["place"].lower() == "temple of isis"
    assert (
        r["participants"][1]["role_normalized"] == "designer" and r["participants"][0]["role_normalized"] == "engraver"
    )
    assert r["accession"] == "2001.19" and r["record_url"].endswith("/2001.19")


def test_non_cc0_drops_image_url():
    item = dict(CLEVELAND, share_license_status="Copyrighted")
    r = oa.parse_cleveland(item)
    assert r["rights_status"] == "rights_pending" and r["image_url"] is None and r["image_width"] is None


AIC = {
    "id": 19,
    "title": "View of Ponte Lugano on the Anio, from Views of Rome",
    "artist_title": "Giovanni Battista Piranesi",
    "artist_display": "Giovanni Battista Piranesi (Italian, 1720-1778)\npublished by Francesco (Italian, 1758-1810) and Pietro Piranesi",
    "date_display": "1763",
    "medium_display": "Etching",
    "is_public_domain": True,
    "image_id": "7f5429b5-a966-ccbe-1ce3-7f131e96bf87",
    "thumbnail": {"width": 3000, "height": 2056},
    "main_reference_number": "1887.252",
    "place_of_origin": "Italy",
    "series_titles": ["Views of Rome"],
}


def test_parse_aic():
    r = oa.parse_aic(AIC)
    assert r["rights_status"] == "open_confirmed" and r["image_url"].endswith("/full/843,/0/default.jpg")
    assert (r["image_width"], r["image_height"]) == (3000, 2056)
    assert r["participants"][1]["role_normalized"] == "publisher"
    assert r["record_url"] == "https://www.artic.edu/artworks/19"
    r2 = oa.parse_aic(dict(AIC, is_public_domain=False))
    assert r2["rights_status"] == "link_only" and r2["image_url"] is None


def test_parse_met_public_domain_flag():
    obj = {
        "objectID": 1,
        "isPublicDomain": True,
        "primaryImage": "https://images.metmuseum.org/x.jpg",
        "artistDisplayName": "Canaletto",
        "artistRole": "Artist",
        "title": "Il Canal Grande, Venezia",
        "objectDate": "1740",
        "medium": "Etching",
        "accessionNumber": "1.2",
        "classification": "Prints",
        "objectURL": "https://www.metmuseum.org/art/collection/search/1",
        "constituents": [],
    }
    r = oa.parse_met(obj)
    assert r["artist_id"] == "canaletto" and r["rights_status"] == "open_confirmed" and r["image_width"] is None
    assert r["city"] == "Venice"
    assert oa.parse_met(dict(obj, isPublicDomain=False))["image_url"] is None


RIJKS = {
    "id": "https://id.rijksmuseum.nl/200110404",
    "identified_by": [
        {
            "type": "Identifier",
            "classified_as": [{"id": "http://vocab.getty.edu/aat/300312355"}],
            "content": "RP-T-1940-589",
        },
        {
            "type": "Name",
            "classified_as": [{"id": "http://vocab.getty.edu/aat/300404670"}],
            "content": "Romeinse ruïnes",
            "language": [{"id": "http://vocab.getty.edu/aat/300388256"}],
        },
    ],
    "classified_as": [{"notation": [{"@language": "en", "@value": "drawing"}]}],
    "made_of": [{"notation": [{"@language": "en", "@value": "paper"}, "papier"]}],
    "produced_by": {
        "part": [
            {
                "carried_out_by": [{"notation": [{"@language": "en", "@value": "Giovanni Battista Piranesi"}]}],
                "referred_to_by": [
                    {
                        "content": "draftsman (artist): Giovanni Battista Piranesi",
                        "language": [{"id": "http://vocab.getty.edu/aat/300388277"}],
                    }
                ],
            }
        ],
        "timespan": {"identified_by": [{"content": "c. 1760"}]},
    },
    "subject_of": [
        {
            "digitally_carried_by": [
                {
                    "access_point": [{"id": "https://iiif.micr.io/bJcmA/full/max/0/default.jpg"}],
                    "referred_to_by": [{"content": "https://creativecommons.org/publicdomain/mark/1.0/"}],
                }
            ]
        },
        {
            "digitally_carried_by": [
                {
                    "access_point": [{"id": "https://www.rijksmuseum.nl/nl/collectie/object/RP-T-1940-589--x"}],
                    "format": "text/html",
                }
            ]
        },
    ],
}


def test_parse_rijks_tolerates_string_notations_and_reads_pdm():
    r = oa.parse_rijks(RIJKS)
    assert r["accession"] == "RP-T-1940-589" and r["original_title"] == "Romeinse ruïnes"
    assert r["object_type"] == "drawing" and r["date_as_stated"] == "c. 1760"
    assert (
        r["participants"][0]["role_as_stated"] == "draftsman (artist)"
        and r["participants"][0]["role_normalized"] == "designer"
    )
    assert r["rights_status"] == "open_confirmed" and r["image_url"].startswith("https://iiif.micr.io/")
    assert r["record_url"].startswith("https://www.rijksmuseum.nl/")


def test_parse_europeana_requires_stated_open_rights():
    item = {
        "id": "/9200518/ark__12148_btv1b1",
        "dcCreator": ["Chapuy, Nicolas Marie Joseph (1790-1858). Dessinateur"],
        "title": ["Roquemaure : [dessin] / Chapuy"],
        "dataProvider": ["National Library of France"],
        "rights": ["http://creativecommons.org/publicdomain/mark/1.0/"],
        "edmIsShownBy": ["https://gallica.bnf.fr/x.jpg"],
        "year": ["1840"],
    }
    r = oa.parse_europeana(item)
    assert r["artist_id"] == "nicolas-marie-joseph-chapuy" and r["rights_status"] == "open_confirmed"
    assert r["record_url"] == "https://www.europeana.eu/item/9200518/ark__12148_btv1b1"
    assert r["participants"][0]["role_normalized"] == "designer"
    r2 = oa.parse_europeana(dict(item, rights=["http://rightsstatements.org/vocab/InC/1.0/"]))
    assert r2["rights_status"] == "rights_pending" and r2["image_url"] is None


def test_parse_loc_never_open():
    item = {
        "pk": "2019634775",
        "title": "View of Paris",
        "creator": "Boys, Thomas Shotter, 1803-1874, artist",
        "links": {"item": "https://www.loc.gov/pictures/item/2019634775/"},
        "created_published_date": "1839",
        "call_number": "X",
        "medium": "lithograph",
    }
    r = oa.parse_loc(item)
    assert r["artist_id"] == "thomas-shotter-boys" and r["rights_status"] == "rights_pending" and r["image_url"] is None
    assert "NOT CC0" in r["rights_statement"]
    assert oa.parse_loc({"pk": "1", "title": "Chapuy Asylum", "creator": None, "links": {}}) is None


def test_parse_commons_license():
    page = {
        "pageid": 5,
        "title": "File:X.jpg",
        "imageinfo": [
            {
                "url": "https://upload.wikimedia.org/x.jpg",
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:X.jpg",
                "width": 4000,
                "height": 3000,
                "extmetadata": {
                    "Artist": {"value": "<a>Charles Meryon</a>"},
                    "LicenseShortName": {"value": "Public domain"},
                    "ObjectName": {"value": "Le Stryge"},
                },
            }
        ],
    }
    r = oa.parse_commons(page)
    assert r["artist_id"] == "charles-meryon" and r["rights_status"] == "open_confirmed" and r["image_width"] == 4000
    page["imageinfo"][0]["extmetadata"]["LicenseShortName"]["value"] = "CC BY-NC 4.0"
    assert oa.parse_commons(page)["rights_status"] == "rights_pending"


def test_duplicate_hint_groups_impressions():
    a = oa.duplicate_hint("The Pantheon, Plate 12", "Vedute", None, "x")
    b = oa.duplicate_hint("the pantheon", "Vedute", None, "x")
    assert a == b


def test_in_period_keeps_unknown_dates_and_drops_modern():
    assert oa.in_period(None) and oa.in_period("1763") and not oa.in_period("1975")


def test_geo_does_not_misread_petersburg_or_imprint():
    assert oa.detect_geo("View of Sadovaya Street in St. Petersburg")[1] is None
    rec = oa.base_record("europeana", "x", oa.AUTHOR_BY_SLUG["nicolas-marie-joseph-chapuy"])
    rec["original_title"] = "Cadix : place de la Constitution / dessiné par Chapuy ; imp. Lemercier à Paris"
    oa.apply_geo(rec)
    assert rec["city"] is None and rec["geo_confidence"] == "unknown"
    rec2 = oa.base_record("aic", "y", oa.AUTHOR_BY_SLUG["charles-meryon"])
    rec2["original_title"] = "The Vampire"
    rec2["series"] = "Eaux-fortes sur Paris"
    oa.apply_geo(rec2)
    assert (rec2["city"], rec2["geo_basis"], rec2["geo_confidence"]) == ("Paris", "series", "city")
