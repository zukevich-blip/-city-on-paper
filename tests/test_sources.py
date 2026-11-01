"""Offline tests: no network. Fixtures mirror real response shapes captured 2026-11-01."""
import json

import pytest

from tools.sources import connectors as c
from tools.sources.identity import benoist_hint


class FakeHttp:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get_json(self, provider, url, params=None, headers=None):
        self.calls.append((provider, url, params, headers))
        for key, value in self.routes.items():
            if key in url:
                return value
        raise c.ProviderError(provider, url, 404, "no fixture")


def test_redact_hides_keys():
    assert "secret" not in c.redact("https://x/?wskey=secret&q=1&api_key=abc")


@pytest.mark.parametrize("stmt,uri,expected", [
    ("Public domain", "", "open"),
    ("", "http://rightsstatements.org/vocab/InC/1.0/", "restricted"),
    ("", "http://rightsstatements.org/vocab/NoC-OKLR/1.0/", "restricted"),
    ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "open"),
    ("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0", "restricted"),
    ("", "", "unknown"),
])
def test_rights_category(stmt, uri, expected):
    assert c.rights_category(stmt, uri) == expected


def test_theme_tags_multilingual():
    assert "food_market" in c.theme_tags("Le Marché aux fleurs, Paris")
    assert "cafe_restaurant" in c.theme_tags("Bill of fare, Delmonico's restaurant")
    assert c.theme_tags("Portrait of a man") == []


def test_relevance_rejects_unrelated_hits():
    rec = c.record("artic", "AIC", 1, title="Self-Portrait", creator="Walter Shirlaw")
    assert not c.relevant(rec, "Benoist")
    rec2 = c.record("met", "Met", 2, title="Portrait", creator="Félix Benoist")
    assert c.relevant(rec2, "felix benoist", ("creator_display",))
    rec3 = c.record("europeana", "BnF", 3, title="[Benoist-Mechin]", creator="Anonyme")
    assert not c.relevant(rec3, "benoist", ("creator_display",))


def test_restricted_record_never_exposes_preview():
    rec = c.record("vam", "V&A", "O1", title="x", preview_url="https://img", rights_statement="In copyright")
    assert rec["rights_category"] == "restricted" and rec["preview_url"] == ""
    assert rec["published"] is False and rec["status"]["viewpoint"] == "not_checked"


def test_unknown_rights_never_exposes_preview():
    rec = c.record("loc", "Library of Congress", "L1", title="x",
                   preview_url="https://example.org/photo.jpg", rights_statement="Rights need item review",
                   rights_category="unknown")
    assert rec["preview_url"] == ""
    assert rec["rights_category"] == "unknown"
    assert rec["published"] is False


def test_artic_requires_header_and_maps_iiif():
    http = FakeHttp({"artic.edu": {"config": {"iiif_url": "https://www.artic.edu/iiif/2"}, "data": [
        {"id": 5, "title": "Market", "artist_display": "A", "is_public_domain": True, "image_id": "abc"},
        {"id": 6, "title": "Market", "artist_display": "B", "is_public_domain": False, "image_id": "def"}]}})
    out = c.artic(http, "market", 5)
    assert http.calls[0][3]["AIC-User-Agent"]
    assert out[0]["preview_url"].endswith("/abc/full/843,/0/default.jpg") and out[0]["rights_category"] == "open"
    assert out[1]["preview_url"] == "" and out[1]["rights_category"] == "restricted"


def test_europeana_uses_data_provider_as_institution(monkeypatch):
    monkeypatch.delenv("EUROPEANA_API_KEY", raising=False)
    http = FakeHttp({"europeana.eu": {"items": [{
        "id": "/9200518/ark__12148_btv1b1", "dataProvider": ["National Library of France"],
        "dcTitleLangAware": {"def": ["Vue de Wilna"]}, "dcCreator": ["Benoist, Philippe (1813-1905)"],
        "rights": ["http://rightsstatements.org/vocab/NoC-OKLR/1.0/"],
        "edmIsShownAt": ["http://gallica.bnf.fr/ark:/12148/btv1b1"], "guid": "https://www.europeana.eu/item/x?utm=1"}]}})
    (r,) = c.europeana(http, "Wilna", 5)
    assert r["institution"] == "National Library of France"
    assert r["source_url"].startswith("http://gallica.bnf.fr") and r["rights_category"] == "restricted"
    assert http.calls[0][2]["wskey"] == "api2demo"


def test_met_non_public_domain_keeps_metadata_only():
    http = FakeHttp({"/v1.1/search": {"objectIDs": [1]}, "/v1/objects/1": {
        "title": "View", "artistDisplayName": "Antoine Benoist", "isPublicDomain": False,
        "primaryImageSmall": "https://img"}})
    (r,) = c.met(http, "Benoist", 3)
    assert r["preview_url"] == "" and r["rights_category"] == "restricted"


def test_merge_dedups_ids_and_flags_cross_provider_duplicates():
    a = c.record("loc", "LoC", 1, title="Paris. La Madeleine", creator="Benoist", date="1845")
    b = c.record("commons", "Commons", 9, title="Paris. La Madeleine", creator="Benoist", date="1845")
    a["search_queries"], b["search_queries"] = ["q1"], ["q2"]
    a2 = dict(a, search_queries=["q3"])
    out = c.merge([a, b, a2])
    assert len(out) == 2
    assert out[0]["search_queries"] == ["q1", "q3"]
    assert out[0]["possible_duplicates"] == ["commons:9"]


def test_offline_http_without_cache_is_an_error(tmp_path):
    http = c.Http(cache_dir=tmp_path, offline=True)
    with pytest.raises(c.ProviderError):
        http.get_json("x", "https://example.org/a")


def test_http_cache_roundtrip(tmp_path):
    http = c.Http(cache_dir=tmp_path, offline=True)
    url = "https://example.org/a?q=1"
    path = http._cache_path(url)
    path.write_text(json.dumps({"ok": 1}))
    assert http.get_json("x", "https://example.org/a", {"q": 1}) == {"ok": 1}
    assert http.cache_hits == 1


@pytest.mark.parametrize("creator,date,hint", [
    ("Félix Benoist (1818-1896)", "1865", "felix"),
    ("Benoist, Philippe (1813-1905). Dessinateur", "1842", "philippe"),
    ("Guillaume Philippe Benoist", "1771", "guillaume_philippe"),
    ("P. Benoist ; Artist ; French, 18th century", "1760", "uncertain"),
    ("Philippe (1813) Benoist; Félix Benoist", "1865", "felix+philippe"),
    ("Benoist, Ch.", "1870", "unresolved_other_benoist"),
    ("Eugène Cicéri", "1850", "not_benoist"),
    ("Benoist, Antoine", "1704", "antoine_royal"),
    ("Benoist, Antoine", "1690", "antoine_royal"),
    ("Antoine Benoist (1632–1717)", "", "antoine_royal"),
    ("Antoine Benoist ; French 1721–1770", "", "antoine"),
    ("Antoine Benoist (prentmaker)", "", "uncertain"),
])
def test_benoist_disambiguation(creator, date, hint):
    assert benoist_hint(creator, date)["hint"] == hint


def test_committed_candidate_file_is_consistent():
    d = json.load(open("data/candidates/candidates-2026-11-01.json", encoding="utf-8"))
    ids = [i["id"] for i in d["items"]]
    assert len(ids) == len(set(ids)) == d["counts"]["records"]
    assert all(i["published"] is False for i in d["items"])
    assert all(i["preview_url"] == "" for i in d["items"] if i["rights_category"] == "restricted")
    assert "wskey=api2demo" not in json.dumps(d)  # keys redacted / not stored

def test_antoines_cannot_be_auto_conflated():
    d = json.load(open("data/candidates/candidates-2026-11-01.json", encoding="utf-8"))
    by_id = {item["id"]: item for item in d["items"]}
    assert by_id["loc:2021670758"]["benoist_identity_hint"]["candidates"][0]["wikidata"] == "Q2853671"
    assert by_id["loc:2021670757"]["benoist_identity_hint"]["candidates"][0]["wikidata"] == "Q2853671"
    assert by_id["met:695277"]["benoist_identity_hint"]["candidates"][0]["wikidata"] == "Q18526511"
    assert by_id["rijksmuseum:200156702"]["benoist_identity_hint"]["hint"] == "uncertain"
