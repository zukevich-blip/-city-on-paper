"""Parsing-only tests for tools/world/search_museums_benoist.py (no network; trimmed real API replies)."""
import json
from pathlib import Path

import pytest

from tools.world import search_museums_benoist as sm

FX = json.loads((Path(__file__).parent / "fixtures" / "museums_benoist.json").read_text("utf-8"))
LOC = json.loads((Path(__file__).parent / "fixtures" / "loc_items.json").read_text("utf-8"))


@pytest.mark.parametrize("name,bio,expected", [
    ("Benoist, Philippe, 1813-ca. 1905", None, "philippe-benoist"),
    ("Philippe (1813) Benoist", None, "philippe-benoist"),
    ("Dessiné par Ph. Benoist", None, "philippe-benoist"),
    ("Benoist, Félix (1818-1896). Auteur du texte", None, "felix-benoist"),
    ("Felix Benoist", None, "felix-benoist"),
    ("Benoist", "French, 1813-1905", "philippe-benoist"),
    ("Benoist, Philippe", "French, 1725-1800", "other"),
    ("Guillaume-Philippe Benoist", None, "other"),
    ("Benoist, Guillaume-Philippe", None, "other"),
    ("Antoine Benoist", None, "other"),
    ("Benoist, J.-L.", None, "other"),
    ("Marie-Guillemine Benoist", None, "other"),
    ("Written by Benoist Boullay", None, "other"),
    ("F. Benoist", None, "uncertain-benoist"),
    ("Benoist", None, "uncertain-benoist"),
    ("Jacottet, Jean", None, None),
])
def test_classify_artist(name, bio, expected):
    assert sm.classify_artist(name, bio)[0] == expected


def test_felix_and_philippe_never_merged():
    assert sm.pick_artist_id(["philippe-benoist", "felix-benoist"])[0] == "uncertain-benoist"
    assert sm.pick_artist_id(["philippe-benoist", "other"])[0] == "philippe-benoist"
    assert sm.pick_artist_id(["other"])[0] is None


@pytest.mark.parametrize("role,note,expected", [
    ("lithographer", None, "lithographer"), ("Lithographe", None, "lithographer"),
    ("Dessinateur du modèle", None, "designer"), ("Draftsman", None, "designer"),
    ("Printer", None, "printer"), ("imprimeur", None, "printer"), ("Publisher", None, "publisher"),
    ("Auteur du texte", None, "author_of_text"), ("engraver", None, "engraver"),
    ("artist", "after", "designer"), ("artist", None, "unspecified"), (None, None, "unspecified"),
])
def test_normalize_role(role, note, expected):
    assert sm.normalize_role(role, note) == expected


def test_rights_status_never_promotes_advisories():
    assert sm.rights_status_for("https://creativecommons.org/publicdomain/mark/1.0/") == "open_confirmed"
    assert sm.rights_status_for("http://creativecommons.org/licenses/by/4.0/") == "open_confirmed"
    assert sm.rights_status_for("CC0") == "open_confirmed"
    assert sm.rights_status_for("No known restrictions on publication.") == "rights_pending"
    assert sm.rights_status_for("No Copyright - United States (http://rightsstatements.org/vocab/NoC-US/1.0/)",
                                file_level=False) == "rights_pending"
    assert sm.rights_status_for("http://rightsstatements.org/vocab/NoC-OKLR/1.0/") == "link_only"
    assert sm.rights_status_for("http://rightsstatements.org/vocab/InC/1.0/") != "open_confirmed"
    assert sm.rights_status_for("http://creativecommons.org/licenses/by-nc-sa/4.0/") == "link_only"
    assert sm.rights_status_for(None) == "unknown"


def test_image_url_only_for_open_confirmed():
    rec = sm.make_record(record_id="x:1", participants=[sm.part("Philippe Benoist")], image_url="https://e/x.jpg",
                         image_width=10, image_height=20, rights_status="rights_pending")
    assert rec["image_url"] is None and rec["image_width"] is None
    rec = sm.make_record(record_id="x:2", participants=[sm.part("Philippe Benoist")], image_url="https://e/x.jpg",
                         image_width=10, image_height=20, rights_status="open_confirmed")
    assert rec["image_url"] == "https://e/x.jpg" and rec["image_width"] == 10


def test_series_not_taken_from_a_longer_title():
    assert sm.detect_series("Paris dans sa Splendeur (volume I)") == "Paris dans sa splendeur"
    assert sm.detect_series("Nouvelles Vues de Paris") is None
    assert sm.detect_series("Vues de Paris. Le Louvre") == "Vues de Paris"


def test_loc_item_is_advisory_not_cc0():
    rec = sm.parse_loc_item(LOC["loc_item_pga"])
    assert rec["record_id"] == "loc:2016652451"
    assert rec["artist_id"] == "philippe-benoist"
    assert rec["rights_status"] == "rights_pending" and "No known restrictions" in rec["rights_statement"]
    assert rec["image_url"] is None
    roles = {p["role_normalized"] for p in rec["participants"]}
    assert {"designer", "printer"} <= roles
    assert rec["record_url"] == "https://www.loc.gov/item/2016652451/"
    assert sm.parse_loc_item(LOC["loc_item_wdl"]) is None


def test_vam_after_note_is_designer_and_rights_unknown():
    rec = sm.parse_vam_record(FX["vam_record"])
    assert rec["artist_id"] == "philippe-benoist"
    assert rec["participants"][0]["role_as_stated"] == "artist (after)"
    assert rec["participants"][0]["role_normalized"] == "designer"
    assert rec["accession"] == "E.3933-1932"
    assert rec["record_url"] == "https://collections.vam.ac.uk/item/O743314/"
    assert rec["rights_status"] == "unknown" and rec["original_title"] is None  # V&A gives no title: stays null


def test_brown_item_series_plate_roles_and_noc_us():
    rec = sm.parse_brown_item(FX["brown_item"])
    assert rec["record_id"] == "brown:bdr:226258"
    assert rec["artist_id"] == "philippe-benoist"
    assert rec["series"] == "Paris dans sa splendeur" and rec["plate_number"] == "22"
    by = {p["name"].split(",")[0]: p["role_normalized"] for p in rec["participants"]}
    assert by["Benoist"] == "lithographer" and by["Charpentier"] == "publisher"
    assert rec["rights_status"] == "rights_pending"  # NoC-US advisory, not CC0
    assert rec["image_url"] is None
    assert rec["iiif_manifest"].endswith("/bdr:226258/manifest.json")


def test_met_parsing_and_forename_benoist_is_dropped():
    rec = sm.parse_met_object(FX["met_benoist"])
    assert rec["artist_id"] == "philippe-benoist" and rec["rights_status"] == "unknown"
    assert rec["image_url"] is None and rec["image_width"] is None
    assert any(p["role_normalized"] == "printer" for p in rec["participants"])
    assert rec["series"] is None  # 'Nouvelles Vues de Paris' is not the series 'Vues de Paris'
    assert sm.parse_met_object(FX["met_other_benoist"]) is None
    assert sm.parse_met_object({}) is None


def test_met_open_access_needs_public_domain_and_image():
    o = dict(FX["met_benoist"], isPublicDomain=True, primaryImage="https://images.metmuseum.org/x.jpg")
    rec = sm.parse_met_object(o)
    assert rec["rights_status"] == "open_confirmed" and rec["image_url"].endswith("x.jpg")
    assert rec["image_width"] is None  # the Met API gives no pixel sizes: never guessed


def test_nga_volume_names_both_brothers_without_merging_them():
    rows = FX["nga_constituent_rows"]
    ben = [r for r in rows if r["constituentid"] in ("3495", "3497")]
    rec = sm.parse_nga_row(FX["nga_object_row"], ben, FX["nga_names"], None, constituents=rows)
    assert rec["record_id"] == "nga:60903"
    assert rec["artist_id"] == "uncertain-benoist"
    assert rec["artist_ids_named"] == ["felix-benoist", "philippe-benoist"]
    assert rec["series"] == "Paris dans sa splendeur" and rec["object_type"] == "volume"
    assert rec["volume"] == "(1 of 3 volumes, 1981.69.5-7)"
    assert rec["image_url"] is None and rec["rights_status"] == "unknown"
    assert rec["record_url"] == "https://www.nga.gov/artworks/60903"
    assert any(p["role_normalized"] == "lithographer" for p in rec["participants"])


def test_nga_open_image_carries_real_pixels():
    rows = FX["nga_constituent_rows"]
    rec = sm.parse_nga_row(FX["nga_object_row"], rows, FX["nga_names"], FX["nga_open_image_row"], constituents=rows)
    assert rec["rights_status"] == "open_confirmed"
    assert (rec["image_width"], rec["image_height"]) == (3393, 4965)


def test_europeana_felix_designer_with_lithographer_and_noc_oklr():
    rec = sm.parse_europeana_item(FX["europeana_bnf_felix"])
    assert rec["artist_id"] == "felix-benoist"
    assert rec["participants"][0]["role_normalized"] == "designer"
    assert rec["rights_status"] == "link_only" and rec["image_url"] is None
    assert rec["verification_status"] == "search_hit_only"


def test_europeana_both_brothers_named_is_flagged_not_merged():
    rec = sm.parse_europeana_item(FX["europeana_hertziana"])
    assert rec["artist_id"] == "uncertain-benoist"
    assert rec["artist_ids_named"] == ["felix-benoist", "philippe-benoist"]
    assert rec["rights_status"] != "open_confirmed"
    assert "both" in rec["attribution_note"]


def test_europeana_title_roles_split_felix_designer_and_philippe_lithographer():
    rec = sm.parse_europeana_item(FX["europeana_text_only_felix"])
    by = {p["name"]: p["role_normalized"] for p in rec["participants"]}
    assert by["Ph. Benoist"] == "lithographer"
    assert rec["artist_ids_named"] == ["felix-benoist", "philippe-benoist"]
    assert rec["rights_status"] == "open_confirmed"  # CC BY 4.0 on the item
    assert rec["record_url"].startswith("https://wellcomecollection.org/works/")


def test_rijks_guillaume_philippe_is_excluded():
    d = FX["rijks_guillaume_philippe"]
    assert sm.parse_rijks_object(d["object"], d["people"]) is None


def test_ulan_labels_are_classified():
    out = sm.parse_ulan(FX["getty_ulan"])
    ids = {o["ulan_uri"].rsplit("/", 1)[1]: o["artist_id"] for o in out}
    assert ids == {"500009717": "philippe-benoist", "500104203": "felix-benoist", "500071766": "other"}


def test_bot_wall_detection():
    assert "Cloudflare" in sm.looks_blocked(429, {"cf-mitigated": "challenge"}, b"<title>Just a moment...</title>")
    assert "AWS WAF" in sm.looks_blocked(202, {"x-amzn-waf-action": "challenge"}, b"")
    assert sm.looks_blocked(200, {}, b'{"ok": true}') is None


def test_search_page_parsers():
    assert sm.parse_met_search({"total": 3, "objectIDs": [1, 2, 3]}) == (3, [1, 2, 3])
    assert sm.parse_met_search({"total": 0, "objectIDs": None}) == (0, [])
    payload = {"info": {"record_count": 54, "pages": 2}, "records": [{"systemNumber": "O1"}, {"systemNumber": "O2"}]}
    assert sm.parse_vam_search(payload) == (54, 2, ["O1", "O2"])
    assert sm.parse_brown_hits({"response": {"docs": [{"pid": "bdr:1"}, {}]}}) == ["bdr:1"]


def test_known_matching_and_duplicate_hint():
    a = sm.make_record(record_id="vam:O1", participants=[sm.part("Philippe Benoist")],
                       institution="Victoria and Albert", accession="E.1-1932", record_url="https://collections.vam.ac.uk/item/O1/",
                       original_title="Place de la Concorde [dessin] / Ph. Benoist")
    b = sm.make_record(record_id="x:2", participants=[sm.part("Philippe Benoist")], institution="Elsewhere",
                       accession="Z", record_url="https://example.org/2", original_title="Place de la Concorde")
    known = {"urls": {"collections.vam.ac.uk/item/o1": "benoist-harvest-v1"}, "accs": {}, "hints": set(), "ids": {}}
    sm.mark_known(a, known)
    sm.mark_known(b, known)
    assert a["known"] and a["known_in"] == "benoist-harvest-v1" and a["known_match"] == "record_url"
    assert not b["known"]
    assert a["duplicate_hint"] == b["duplicate_hint"] == "place de la concorde||"


def test_assemble_counts_new_unique_and_keeps_schema_keys():
    def rec(rid, title, who="Philippe Benoist"):
        return sm.make_record(record_id=rid, participants=[sm.part(who, "lithographer")], original_title=title,
                              institution="I", accession=rid, record_url=f"https://e/{rid}")

    known = {"urls": {"e/a:1": "benoist-harvest-v1"}, "accs": {}, "hints": set(), "ids": {}}
    cov = sm.new_cov()
    cov["hits"] = 5
    per = {"nga": ([rec("a:1", "Old"), rec("a:2", "Fresh"), rec("a:3", "Fresh")], cov),
           "met": ([rec("b:1", "Other", "Félix Benoist")], sm.new_cov())}
    doc = sm.assemble(per, known)
    assert doc["version"] == 1 and doc["source"] == "museums-multi"
    for k in ("queries", "pages_walked", "hits_total_reported_by_source", "records_kept", "blocked", "notes"):
        assert k in doc["coverage"]
    nga = doc["coverage"]["per_source"]["nga"]
    assert (nga["kept"], nga["known"], nga["new"], nga["new_unique_compositions"]) == (3, 1, 2, 1)
    assert doc["coverage"]["per_source"]["met"]["felix_only"] == 1
    assert doc["coverage"]["totals"]["new_unique_compositions"] == 2
    required = {"record_id", "artist_id", "participants", "original_title", "series", "plate_number", "volume", "city",
                "place", "country", "geo_confidence", "date_as_stated", "technique_as_stated", "object_type",
                "institution", "accession", "record_url", "iiif_manifest", "image_url", "image_width", "image_height",
                "rights_statement", "rights_status", "duplicate_hint", "impression_note", "verification_status",
                "attribution_confidence", "attribution_note"}
    assert required <= set(doc["records"][0])
