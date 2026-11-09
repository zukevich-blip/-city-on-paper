"""Offline regression checks for global staging-city reconciliation (never an import)."""
import json
from pathlib import Path

from tools.curation.audit_global_cities import audit, city_key, slug_for_candidate

ROOT = Path(__file__).resolve().parents[1]


def _sources():
    atlas = json.loads((ROOT / "eras/data/atlas.json").read_text("utf-8"))
    seed = json.loads((ROOT / "data/curation/world-cities-v1.json").read_text("utf-8"))
    return atlas, seed


def test_current_source_counts_are_audited_without_claiming_verified_cities():
    atlas, seed = _sources()
    registry, report, queue = audit(atlas, seed)
    c = report["counts"]
    assert c["atlas_entries"] >= 180
    assert c["seed_entries"] >= 150
    assert c["atlas_works_listed"] >= c["atlas_distinct_source_urls"]
    assert c["combined_candidate_records"] >= c["atlas_distinct_name_country"]
    assert c["matched_name_country"] + c["seed_not_in_atlas"] == c[
        "seed_distinct_name_country"
    ]
    assert len(registry["cities"]) == c["combined_candidate_records"]
    assert len(queue["items"]) == c["queue_not_fetched"]
    assert queue["network_calls"] == 0
    assert registry["publication_status"].startswith("research_only")
    assert all(x["status"] == "queued_not_fetched" for x in queue["items"])


def test_seed_only_rows_have_no_fabricated_coordinates_or_works():
    atlas, seed = _sources()
    registry, _, _ = audit(atlas, seed)
    pending = [x for x in registry["cities"] if x["catalog_status"] == "seed_candidate_only"]
    assert pending
    assert all(x["lat"] is None and x["lon"] is None for x in pending)
    assert all(x["works_listed"] == 0 for x in pending)
    assert all(x["city_id"].startswith("unresolved-") for x in pending)
    assert all(x["review_status"].startswith("awaiting_") for x in pending)


def test_multiword_names_and_case_normalized_only_with_same_country():
    a = {"cities": [
        {"id": "venice", "name": "Венеция", "country": "Италия", "lat": 45.4,
         "lon": 12.3, "works": [{"url": "https://example.org/work#image"}]}
    ]}
    s = {"cities": [
        {"name": " ВЕНЕЦИЯ ", "country": "Италия", "query": "Venice city lithograph"},
        {"name": "Венеция", "country": "США", "query": "Venice California art"},
    ]}
    registry, report, queue = audit(a, s)
    assert report["counts"]["matched_name_country"] == 1
    assert report["counts"]["seed_not_in_atlas"] == 1
    assert report["counts"]["combined_candidate_records"] == 2
    assert len(queue["items"]) == 2
    assert city_key(s["cities"][0]) == city_key(a["cities"][0])
    unknown = next(x for x in registry["cities"] if x["country"] == "США")
    assert unknown["lat"] is None
    assert slug_for_candidate(s["cities"][1]) == unknown["city_id"]


def test_duplicate_work_urls_not_counted_as_two_unique_holding_records():
    a = {"cities": [
        {"id": "a", "name": "A", "country": "Q", "lat": 1, "lon": 2,
         "works": [{"url": "https://museum.example/a"},
                   {"url": "https://museum.example/a#detail"}]},
        {"id": "b", "name": "B", "country": "Q", "lat": 3, "lon": 4,
         "works": [{"url": "https://museum.example/a"}]},
    ]}
    registry, report, _ = audit(a, {"cities": []})
    c = report["counts"]
    assert c["atlas_works_listed"] == 3
    assert c["atlas_distinct_source_urls"] == 1
    assert c["source_url_repeat_occurrences"] == 2
    assert registry["cities"][0]["works_listed"] == 2


def test_homonyms_in_same_country_are_flagged_not_silently_merged():
    a = {"cities": [
        {"id": "x", "name": "Springfield", "country": "USA", "lat": 0, "lon": 1},
        {"id": "y", "name": "Springfield", "country": "USA", "lat": 2, "lon": 3},
    ]}
    registry, report, _ = audit(a, {"cities": []})
    assert len(registry["cities"]) == 1  # staging only, never published
    assert report["counts"]["atlas_duplicate_name_country_entries"] == 1
    assert report["ambiguous_atlas_name_country"][0]["duplicate_ids"] == ["x", "y"]
