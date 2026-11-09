"""Bounded world map discovery tests using only real stored seed and fake API fixtures."""
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from tools.maps.discover_loc_historical_maps import (
    LOC_API,
    build_queue,
    discover,
    loc_url,
    official_loc_record,
    search_phrase,
)

ROOT = Path(__file__).resolve().parents[1]


def test_real_world_city_queue_is_global_and_search_is_not_georeference():
    a = json.loads((ROOT / "eras/data/atlas.json").read_text("utf-8"))
    s = json.loads((ROOT / "data/curation/world-cities-v1.json").read_text("utf-8"))
    queue = build_queue(a, s)
    assert len(queue) >= 180
    assert len({r["city_id"] for r in queue}) == len(queue)
    assert queue[0]["name"] == "Париж"
    assert all(r["review_status"] == "search_queued_not_a_verified_map" for r in queue)
    assert all(r["source"] == LOC_API for r in queue)
    assert any(r["name"] == "Токио" for r in queue)
    assert any(r["name"] == "Нью-Йорк" for r in queue)
    assert any(r["name"] == "Рим" for r in queue)
    assert all("(" not in r["name"] for r in queue)


def test_search_uses_existing_transliteration_without_synthetic_artwork():
    a = {"name": "Флоренция", "name_original": "Florence",
         "discovery_query": "Florence city lithograph"}
    assert search_phrase(a) == "Florence city map"
    assert "fo=json" in loc_url("Florence map", 3)
    with pytest.raises(ValueError):
        loc_url("Paris map", 500)


def test_official_loc_id_only_no_third_party_or_unverified_hd():
    rec = official_loc_record({
        "id": "http://www.loc.gov/item/2012586603/",
        "title": "Paris et ses environs",
        "date": "1878",
    })
    assert rec is not None
    assert rec["object_url"] == "https://www.loc.gov/item/2012586603/"
    assert rec["hd_verified"] is False
    assert rec["georeferencing_status"] == "not_attempted"
    assert rec["depicted_city_verified"] is False
    assert official_loc_record({
        "id": "https://example.net/item/2012586603/",
        "title": "Impossible map",
    }) is None
    assert official_loc_record({"id": "https://www.loc.gov/", "title": "News"}) is None


def test_mocked_discovery_deduplicates_while_keeping_only_source_candidates():
    queue = [{"city_id": "paris", "name": "Париж", "country": "Франция",
              "query": "Paris map"}]
    called = []

    def fake_fetch(url):
        called.append(url)
        return {"results": [
            {"id": "https://www.loc.gov/item/2012586603/", "title": "Map A", "date": "1878"},
            {"id": "http://www.loc.gov/item/2012586603/", "title": "Map A duplicate"},
            {"id": "https://thirdparty.invalid/item/12345/", "title": "Fake"},
        ]}

    archive, report = discover(queue, budget=1, delay=0, fetch=fake_fetch)
    assert len(called) == 1
    assert report["attempted_city_count"] == 1
    assert report["map_candidate_count"] == 1
    assert report["georeferenced_city_count"] == 0
    assert report["rights_confirmed_count"] == 0
    item = archive["city_search_results"][0]["candidate_maps"][0]
    assert item["classification"] == "map_search_candidate_not_verified"


def test_429_stops_and_never_ignores_rate_limit():
    queue = [{"city_id": str(i), "name": str(i), "country": "test", "query": str(i)}
             for i in range(3)]

    def denied(_):
        raise HTTPError(LOC_API, 429, "Too Many Requests",
                        {"Retry-After": "42"}, None)

    _, report = discover(queue, budget=3, delay=0, fetch=denied)
    assert report["throttled"]
    assert report["attempted_city_count"] == 1
    assert report["errors"][0]["retry_after"] == "42"

def test_geonames_adds_worldwide_city_searches_without_collapsing_homonyms():
    a = {"cities": [{"id": "paris", "name": "Париж", "country": "Франция",
                      "lat": 48.85, "lon": 2.3, "works": []}]}
    seed = {"cities": []}
    geonames = {
        "schema": "city-on-paper/geonames-major-city-candidates/v1",
        "cities": [{
            "candidate_city_id": "geonames-123",
            "name": "Paris", "name_ascii": "Paris", "country_iso2": "FR",
            "lat": 48.85, "lon": 2.3, "population_reported_by_geonames": 2000000,
            "source_url": "https://www.geonames.org/123/",
        }],
    }
    rows = build_queue(a, seed, geonames)
    assert len(rows) == 2
    assert {r["city_id"] for r in rows} == {"paris", "geonames-123"}
    geo = next(x for x in rows if x["city_id"] == "geonames-123")
    assert geo["query"] == "Paris historical city map"
    assert geo["identity_status"] == "geonames_candidate_not_reconciled_with_atlas"
    assert geo["review_status"] == "search_queued_not_a_verified_map"

