"""Offline tests: no network. Fixtures mirror real response shapes captured 2026-11-01."""
import json

import pytest

from tools.sources import connectors as c
from tools.sources.identity import benoist_hint


class FakeHttp:
    requests_made = cache_hits = 0

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
    ("Benoist, Antoine, 1632-1717 Artist.", "1704", "uncertain"),
    ("Benoist, Antoine, 1632-1717", "", "uncertain"),
    ("Antoine Benoist (1721-1770)", "1760", "antoine"),
    ("Eugène Cicéri", "1850", "not_benoist"),
])
def test_benoist_disambiguation(creator, date, hint):
    assert benoist_hint(creator, date)["hint"] == hint


@pytest.mark.parametrize("path", ["data/candidates/candidates-2026-11-01.json",
                                  "data/candidates/candidates-2026-11-01b.json"])
def test_committed_candidate_file_is_consistent(path):
    d = json.load(open(path, encoding="utf-8"))
    ids = [i["id"] for i in d["items"]]
    assert len(ids) == len(set(ids)) == d["counts"]["records"]
    assert all(i["published"] is False for i in d["items"])
    assert all(i["preview_url"] == "" for i in d["items"] if i["rights_category"] == "restricted")
    assert "wskey=api2demo" not in json.dumps(d)  # keys redacted / not stored
    ids_set = set(ids)
    assert all(x in ids_set for i in d["items"] for x in i.get("possible_duplicates", []))


# --------------------------------------------------------------------------- update 2 (consilium: sources)

LOC_FIX = json.load(open("tests/fixtures/loc_items.json", encoding="utf-8"))


@pytest.mark.parametrize("advisory,coll,expected", [
    ("No known restrictions on publication.", "", "open"),
    ("No known restrictions on publications. <p>If an image is displaying, you can download it", "", "open"),
    ("Rights status not evaluated. For general information see Copyright and Other Restrictions", "", "unknown"),
    ("Publication may be restricted. For information see ...", "", "restricted"),
    ("", "The Library of Congress is unaware of any copyright or other restrictions in the World Digital "
         "Library Collection.", "unknown"),
    ("", "The Library of Congress does not own rights to material in its collections.", "unknown"),
])
def test_loc_rights_classification(advisory, coll, expected):
    assert c.loc_rights(advisory, coll)[0] == expected


def test_loc_search_uses_embedded_rights_advisory():
    http = FakeHttp({"loc.gov/photos": {"results": [
        {"id": "http://www.loc.gov/item/2016652451/", "url": "https://www.loc.gov/item/2016652451/",
         "title": "Paris. Jardin du Palais Royal", "contributor": ["benoist, philippe"],
         "image_url": ["https://tile.loc.gov/x.jpg#h=1"], "item": LOC_FIX["loc_item_pga"]["item"]["item"]},
        {"id": "http://www.loc.gov/item/2021670758/", "url": "https://www.loc.gov/item/2021670758/",
         "title": "Portraits of the Royal Family", "contributor": ["benoist, antoine"], "image_url": []}]}})
    a, b = c.loc(http, "Benoist", 5)
    assert a["rights_category"] == "open" and a["rights_statement"].startswith("No known restrictions")
    assert "lc-repro:lc-dig-pga-14314" in a["identifiers"] and "lc-hdl:pga.14314" in a["identifiers"]
    assert b["rights_category"] == "unknown"


def test_resolve_loc_rights_from_item_json_fixture():
    recs = [c.record("loc", "Library of Congress", "2016652451", title="x"),
            c.record("loc", "Library of Congress", "2021670758", title="y"),
            c.record("loc", "Library of Congress", "999", title="z"),
            c.record("met", "Met", "1", title="not loc")]
    http = FakeHttp({"/item/2016652451/": LOC_FIX["loc_item_pga"], "/item/2021670758/": LOC_FIX["loc_item_wdl"]})
    stats = c.resolve_loc_rights(http, recs, max_requests=10)
    assert recs[0]["rights_category"] == "open" and recs[0]["rights_granularity"].startswith("per-item")
    assert recs[0]["creator_display"] == "Benoist, Philippe, 1813-approximately 1905, artist"
    assert recs[1]["rights_category"] == "unknown" and recs[1]["rights_statement"] == "no rights advisory on item"
    assert "World Digital Library" in recs[1]["rights_collection_note"]
    assert recs[2]["rights_category"] == "unknown" and recs[2]["rights_check_errors"]
    assert stats == {"checked": 3, "resolved": 1, "still_unknown": 1, "errors": 1, "skipped_budget": 0}
    assert all(call[2] == {"fo": "json", "at": "item"} for call in http.calls)


def test_resolve_loc_rights_respects_budget():
    recs = [c.record("loc", "LoC", str(i), title="t") for i in range(5)]
    stats = c.resolve_loc_rights(FakeHttp({}), recs, max_requests=2)
    assert stats["checked"] == 2 and stats["skipped_budget"] == 3


def test_lc_identifiers_from_commons_text():
    text = ("Paris. Jardin du Palais Royal. Library of Congress Prints and Photographs Division, "
            "reproduction number LC-DIG-pga-14314; http://hdl.loc.gov/loc.pnp/pga.14314 "
            "https://www.loc.gov/pictures/item/2016652451/ and LC-USZC4-1234")
    ids = c.lc_identifiers(text)
    assert ids == ["lc-repro:lc-dig-pga-14314", "lc-repro:lc-uszc4-1234", "lc-hdl:pga.14314", "lccn:2016652451"]
    assert c.lc_identifiers("Bibliothèque nationale de France, btv1b1") == []


def _commons_page(pageid, title, artist, desc="", credit="", index=1):
    return {"pageid": pageid, "title": f"File:{title}", "index": index, "imageinfo": [{
        "descriptionurl": f"https://commons.wikimedia.org/wiki/File:{title}", "width": 10, "height": 10,
        "thumburl": "https://upload.wikimedia.org/t.jpg",
        "extmetadata": {"Artist": {"value": artist}, "ImageDescription": {"value": desc},
                        "Credit": {"value": credit}, "LicenseShortName": {"value": "Public domain"}}}]}


def test_commons_category_paginates_and_marks_category_not_attribution():
    pages = [
        {"continue": {"gcmcontinue": "file|next", "continue": "gcmcontinue||"},
         "query": {"pages": {"1": _commons_page(1, "Nantes.jpg", "Félix Benoist")}}},
        {"query": {"pages": {"2": _commons_page(2, "Vue.jpg", "Guillaume Philippe Benoist")}}},
    ]

    class PagedHttp(FakeHttp):
        def get_json(self, provider, url, params=None, headers=None):
            self.calls.append((provider, url, params, headers))
            return pages[len(self.calls) - 1]

    http = PagedHttp({})
    out = c.commons_category(http, "Philippe Benoist", 10)
    assert [r["source_id"] for r in out] == ["1", "2"]
    assert http.calls[0][2]["gcmtitle"] == "Category:Philippe Benoist" and http.calls[0][2]["gcmnamespace"] == 6
    assert http.calls[1][2]["gcmcontinue"] == "file|next"
    assert all(r["category_is_not_attribution"] and r["commons_category"] == "Category:Philippe Benoist"
               for r in out)


def test_category_membership_never_becomes_philippe_attribution():
    from tools.sources import harvest
    cat = {"query": {"pages": {
        "1": _commons_page(1, "Gravure.jpg", "Guillaume Philippe Benoist", index=1),
        "2": _commons_page(2, "Unknown.jpg", "Anonyme", index=2),
        "3": _commons_page(3, "Wilna.jpg", "Philippe Benoist (1813-1905)", index=3)}}}
    http = FakeHttp({"commons.wikimedia.org": cat})
    plan = {"loc_rights_max_requests": 0,
            "jobs": [{"query": "Category:Philippe Benoist", "match": "", "providers": ["commons_category"]}]}
    res = harvest.run(plan, http)
    hints = {i["source_id"]: i["benoist_identity_hint"]["hint"] for i in res["items"]}
    assert hints == {"1": "guillaume_philippe", "2": "category_only_not_attribution", "3": "philippe"}


def test_merge_links_loc_and_commons_by_reproduction_number():
    lo = c.record("loc", "LoC", "2016652451", title="Paris. Jardin du Palais Royal", creator="benoist, philippe",
                  date="[between 1845 and 1860]")
    lo["identifiers"] = ["lccn:2016652451", "lc-repro:lc-dig-pga-14314"]
    co = c.record("commons", "Commons", 77, title="Jardin du Palais-Royal, Paris (LOC)", creator="Unknown",
                  date="1850")
    co["identifiers"] = c.lc_identifiers("LC-DIG-pga-14314")
    other = c.record("commons", "Commons", 78, title="Rue de Rivoli", creator="Anonyme")
    out = {r["id"]: r for r in c.merge([lo, co, other])}
    assert out["loc:2016652451"]["possible_duplicates"] == ["commons:77"]
    assert out["commons:77"]["duplicate_evidence"]["loc:2016652451"].startswith("identifier lc-repro:")
    assert out["commons:78"]["possible_duplicates"] == []
    assert out["loc:2016652451"]["dedup_group"] == out["commons:77"]["dedup_group"]


def test_merge_links_by_title_and_creator_surname():
    lo = c.record("loc", "LoC", "1", title="Paris. Jardin du Palais Royal",
                  creator="Benoist, Philippe, 1813-approximately 1905, artist", date="[between 1845 and 1860]")
    co = c.record("commons", "Commons", 2, title="Paris - Jardin du Palais Royal",
                  creator="Philippe Benoist (1813–1905)", date="1850")
    gp = c.record("commons", "Commons", 3, title="Paris - Jardin du Palais Royal", creator="Jacottet", date="1850")
    out = {r["id"]: r for r in c.merge([lo, co, gp])}
    assert out["loc:1"]["possible_duplicates"] == ["commons:2"]
    assert out["commons:2"]["duplicate_evidence"]["loc:1"].startswith("title+surname")
    assert c.creator_surname("Benoist, Philippe, 1813-approximately 1905, artist") == "benoist"
    assert c.creator_surname("Philippe Benoist (1813–1905)") == "benoist"
    assert c.title_surname_key(c.record("x", "x", 1, title="View", creator="A. Smith")) == ""


# --------------------------------------------------------------------------- review fixes (b413124)

@pytest.mark.parametrize("stmt,uri,expected", [
    ("CC-BY-NC-SA-4.0", "", "restricted"),
    ("CC-BY-SA-4.0", "https://creativecommons.org/licenses/by-sa/4.0/", "open"),
    ("etalab-2.0", "", "open"),
    ("InC", "", "restricted"),
    ("InC-EDU", "", "restricted"),
    ("Attribution-NonCommercial", "", "restricted"),
])
def test_rights_category_review_cases(stmt, uri, expected):
    assert c.rights_category(stmt, uri) == expected


def test_panoramax_nc_licence_is_not_open():
    feat = lambda i, lic: {"id": i, "geometry": {"coordinates": [2.3, 48.8]},  # noqa: E731
                           "properties": {"license": lic, "datetime": "2025-01-01"}, "links": []}
    http = FakeHttp({"panoramax": {"features": [feat("a", "CC-BY-NC-SA-4.0"), feat("b", "CC-BY-SA-4.0")]}})
    a, b = c.panoramax(http, "2.3,48.8,2.31,48.81", 2)
    assert a["rights_category"] == "restricted" and a["preview_url"] == ""
    assert b["rights_category"] == "open"


def test_cache_never_stores_api_keys(tmp_path, monkeypatch):
    body = json.dumps({"apikey": "SECRET123", "items": [{"guid": "https://x/?wskey=SECRET123&a=1"},
                                                       {"guid": "https://x/i?utm_medium=api&utm_campaign=SECRET123"}]}).encode()

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return body

    monkeypatch.setattr(c, "urlopen", lambda req, timeout: Resp())
    http = c.Http(cache_dir=tmp_path, delay=0)
    http.get_json("europeana", "https://api.europeana.eu/x", {"wskey": "SECRET123"})
    cached = "".join(f.read_text() for f in tmp_path.iterdir())
    assert "SECRET123" not in cached and "apikey" not in cached


def test_long_retry_after_is_not_waited(monkeypatch):
    from email.message import Message
    from urllib.error import HTTPError
    hdrs = Message()
    hdrs["Retry-After"] = "120"

    def boom(req, timeout):
        raise HTTPError(req.full_url, 429, "Too Many Requests", hdrs, None)

    monkeypatch.setattr(c, "urlopen", boom)
    monkeypatch.setattr(c.time, "sleep", lambda s: pytest.fail("must not sleep for a long Retry-After"))
    http = c.Http(delay=0)
    with pytest.raises(c.ProviderError) as e:
        http.get_json("commons", "https://commons.wikimedia.org/w/api.php")
    assert e.value.status == 429 and http.requests_made == 1


def test_homonym_place_guard():
    fl = c.record("loc", "LoC", 1, title="St. Petersburg Yacht Club, St. Petersburg, Fla.",
                  place="florida; united states; saint petersburg")
    ru = c.record("loc", "LoC", 2, title="Bird's-eye view of St. Petersburg", place="russia; saint petersburg")
    assert c.excluded(fl, ["florida", "fla"]) and not c.excluded(ru, ["florida", "fla"])


def test_bare_title_is_not_duplicate_evidence():
    a = c.record("europeana", "X", 1, title="Istanbul")
    b = c.record("europeana", "Y", 2, title="Istanbul")
    assert all(r["possible_duplicates"] == [] for r in c.merge([a, b]))
