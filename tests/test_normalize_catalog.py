"""Data quality and provenance tests for the pilot normalized museum catalog."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from tools.normalize_catalog import (
    API,
    DeferredRemote,
    _record,
    city_index,
    collect,
    enrich_catalog,
    fold,
    main,
    normalize,
    report,
    stable_id,
    valid_coords,
    wikidata_claims,
)


def rec(index: int, *, title: str = "Paris", accession: str = "1963.84",
        url: str = "https://museum.example/art/1963.84",
        qid: str | None = None, city: str = "Париж",
        country: str = "Франция") -> dict:
    return _record(
        "test.json", index, {}, title=title,
        institution="Cleveland Museum of Art", accession=accession,
        url=url, city=city, country=country, maker="Artist",
        date="1850", rights="cc0", qid=qid,
    )


def seed() -> list[dict]:
    return [{
        "name": "Париж", "country": "Франция", "region": "Европа",
        "wikidata_claim": "Q90", "geonames_claim": "2988507",
        "latitude_claim": None, "longitude_claim": None,
        "source": "test.json", "source_index": 0,
    }]


def test_real_curated_files_are_read_without_network() -> None:
    repo = Path(__file__).resolve().parents[1]
    records, cities, warnings = collect(repo)
    assert len(cities) == 150
    assert len(records) >= 41
    assert not any("not a JSON object" in warning for warning in warnings)
    assert any(r["accession"] == "1963.84" for r in records)
    c = normalize(records, cities)
    assert c["schema"] == "city-on-paper/normalized-catalog/v1"
    assert c["works"]
    assert len({w["id"] for w in c["works"]}) == len(c["works"])
    assert all(w["rights"]["reuse_approved_by_this_pipeline"] is False
               for w in c["works"])


def test_exact_holding_duplicates_merge_but_distinct_holdings_do_not() -> None:
    inputs = [
        rec(0),
        rec(1, title="Paris — another spelling"),
        rec(2, title="Paris", accession="1963.85", url="https://museum.example/art/1963.85"),
    ]
    catalog = normalize(inputs, seed())
    assert len(catalog["works"]) == 2
    assert len(catalog["review_queue"]["exact_duplicates"]) == 1
    assert any(c["type"] == "conflicting_titles_same_holding"
               for c in catalog["review_queue"]["conflicts"])


def test_qid_is_suggestion_not_automatic_merge() -> None:
    catalog = normalize([
        rec(0, qid="Q12418"),
        rec(1, accession="other", url="https://museum.example/art/other", qid="Q12418"),
    ], seed())
    assert len(catalog["works"]) == 2
    suggestions = catalog["review_queue"]["possible_duplicates"]
    assert any(s["reason"] == "wikidata" and s["match_key"] == "Q12418"
               for s in suggestions)


def test_homonym_without_country_is_ambiguous() -> None:
    cities = seed() + [{
        **seed()[0], "name": "Париж", "country": "США", "geonames_claim": None,
    }]
    _, by_name = city_index(cities)
    assert len(by_name[fold("Париж")]) == 2
    catalog = normalize([rec(0, country="")], cities)
    assert catalog["works"][0]["depiction"]["status"] == "ambiguous"


def test_city_without_coordinates_is_not_validated() -> None:
    catalog = normalize([rec(0)], seed())
    assert catalog["cities"][0]["geonames_status"] == "location_pending"
    assert catalog["works"][0]["depiction"]["status"] == "linked_to_seed_not_verified"


def test_wikidata_properties_have_distinct_meanings() -> None:
    def item(qid: str) -> dict:
        return {"mainsnak": {"snaktype": "value",
                             "datavalue": {"value": {"id": qid}}}}

    def point(value: str) -> dict:
        return {"mainsnak": {"snaktype": "value", "datavalue": {
            "value": {"time": value, "precision": 9, "calendarmodel": "Q1985727"}}}}

    entity = {"id": "Q12418", "claims": {
        "P170": [item("Q762")], "P50": [item("Q123")],
        "P571": [point("+1503-01-01T00:00:00Z")],
        "P577": [point("+1506-01-01T00:00:00Z")],
        "P585": [point("+2020-01-01T00:00:00Z")],
    }}
    extracted = wikidata_claims(entity)
    assert extracted["creators_p170"] == ["Q762"]
    assert extracted["authors_p50"] == ["Q123"]
    assert extracted["inception_p571"][0]["precision"] == 9
    assert extracted["publication_p577"][0]["time"].startswith("+1506")
    assert extracted["point_in_time_p585"][0]["time"].startswith("+2020")


def test_no_publication_grant_from_wikidata_fixture(tmp_path: Path) -> None:
    catalog = normalize([rec(0, qid="Q12418")], seed())

    class FakeApi:
        def get(self, url, params):
            if "wikidata" in url:
                return {"entities": {"Q12418": {
                    "id": "Q12418", "claims": {"P170": [{
                        "mainsnak": {"snaktype": "value", "datavalue": {
                            "value": {"id": "Q762"}}},
                    }]},
                }}}
            return {"geonameId": 2988507, "lat": 48.85, "lng": 2.35}

    status = enrich_catalog(
        catalog, FakeApi(), enable_wikidata=True, enable_geonames=True,
        geonames_user="test-account",
    )
    assert status["wikidata_checked"] == 1
    assert status["geonames_checked"] == 1
    assert catalog["works"][0]["wikidata_status"] == "metadata_retrieved_not_verified"
    assert catalog["works"][0]["wikidata_metadata"]["creators_p170"] == ["Q762"]
    assert catalog["works"][0]["rights"]["reuse_approved_by_this_pipeline"] is False


def test_retry_after_is_respected_and_deferred(tmp_path: Path, monkeypatch) -> None:
    def rate_limited(*args, **kwargs):
        raise HTTPError("https://www.wikidata.org", 429, "rate limited",
                        {"Retry-After": "1200"}, None)

    import tools.normalize_catalog as module
    monkeypatch.setattr(module, "urlopen", rate_limited)
    api = API(tmp_path / "cache", sleeper=lambda seconds: pytest.fail("Must not retry too early"))
    with pytest.raises(DeferredRemote, match="1200s"):
        api.get("https://www.wikidata.org/w/api.php", {"action": "wbgetentities"})


def test_safe_unsupported_id_and_source_urls() -> None:
    assert stable_id("city", "x") == stable_id("city", "x")
    assert valid_coords(48.8, 2.3)
    assert not valid_coords("unknown", 2.3)
    assert not valid_coords(float("nan"), 2.3)
    catalog = normalize([rec(0, qid="not-a-QID")], seed())
    assert catalog["works"][0]["wikidata_id"] is None


def test_offline_cli_writes_separate_raw_and_normalized(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    result = main(["--root", str(repo), "--out", str(tmp_path)])
    assert result == 0
    normalized = json.loads((tmp_path / "normalized_catalog.json").read_text(encoding="utf-8"))
    raw = json.loads((tmp_path / "catalog_raw.json").read_text(encoding="utf-8"))
    summary = json.loads((tmp_path / "normalization_report.json").read_text(encoding="utf-8"))
    assert raw["records"]
    assert normalized["works"]
    assert summary["normalized_holdings"] == len(normalized["works"])
    assert summary["publication"].startswith("NOT APPROVED")
    assert summary["online"]["status"] == "offline_no_api_calls"


def test_report_does_not_claim_external_validation() -> None:
    normalized = normalize([rec(0)], seed())
    result = report(normalized, 1, [], {"status": "offline_no_api_calls"})
    assert result["cities_location_pending"] == 1
    assert result["scientific_status"].endswith("not performed")


def test_unreviewed_export_is_rejected_inside_tracked_data(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError, match="within repo must use dist"):
        main(["--root", str(repo), "--out", str(repo / "data/curation/normalized")])


def test_packaged_generated_collections_are_imported_without_false_approval(tmp_path: Path) -> None:
    generated = {
        "data/curation/museum-expansion-v1.json": {
            "items": [{
                "name": "The Apsis of Notre Dame", "source": "The Cleveland Museum of Art",
                "source_id": "1937.632", "url": "https://clevelandart.org/art/1937.632",
                "city": "Париж", "maker": "Charles Meryon", "date": "1854",
                "rights": "cc0", "verified": "museum_api",
            }],
        },
        "data/curation/world-graphic-archive-v1.json": {
            "items": [{
                "id": "commons-art-1", "name": "Hong Kong view",
                "source": "Wikimedia Commons", "source_id": "File:Hong Kong view.jpg",
                "url": "https://commons.wikimedia.org/wiki/File:Hong_Kong_view.jpg",
                "city": "Гонконг", "country": "Китай",
                "maker": "unknown", "rights": "public_domain_commons",
            }],
        },
    }
    for rel, source_data in generated.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(source_data), encoding="utf-8")
    records, cities, warnings = collect(tmp_path)
    assert len(records) == 2
    assert not cities and not warnings
    normalized = normalize(records, cities)
    assert len(normalized["works"]) == 2
    assert all(work["review_status"] == "needs_editorial_review"
               for work in normalized["works"])
    assert all(work["rights"]["reuse_approved_by_this_pipeline"] is False
               for work in normalized["works"])
    assert all(work["depiction"]["status"] == "location_pending"
               for work in normalized["works"])
