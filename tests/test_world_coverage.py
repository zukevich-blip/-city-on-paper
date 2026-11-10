"""Guard the meaning of a city, named place, candidate and museum-original record."""
from __future__ import annotations

import json

from tools.audit.world_coverage import build, norm


def write_json(root, filename, data):
    p = root / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_city_coverage_distinguishes_city_place_and_machine_candidate(tmp_path):
    write_json(tmp_path, "data/curation/world-cities-v1.json", {
        "cities": [
            {"name": "Париж", "country": "Франция", "region": "Европа"},
            {"name": "Санкт-Петербург", "country": "Россия", "region": "Европа"},
        ]
    })
    write_json(tmp_path, "eras/data/atlas.json", {
        "cities": [
            {"name": "ПАРИЖ", "kind": "city", "country": "Франция",
             "works": [
                 {"title": "La Madeleine", "rights_class": "open",
                  "url": "https://www.loc.gov/item/2016652452/",
                  "image": "https://example.org/old-print.jpg"},
                 {"title": "A link-only image", "rights_class": "link",
                  "url": "https://example.org/entry"},
             ]},
            {"name": "Амальфи (собор)", "kind": "monument", "country": "Италия",
             "works": []},
        ]
    })
    write_json(tmp_path, "eras/data/eras.json", {
        "cities": [{"name": "Париж", "places": [{"images": [
            {"rights_class": "open", "file": "img/historic.jpg",
             "object_url": "https://www.loc.gov/item/2016652452/"},
        ]}]}]
    })
    write_json(tmp_path, "data/curation/world-graphic-archive-v1.json", {
        "items": [{"city": "Амальфи (собор)", "name": "Subject",
                   "url": "https://commons.wikimedia.org/wiki/File:Subject.jpg"}]
    })
    write_json(tmp_path, "data/curation/museum-expansion-v1.json", {
        "items": [{"city": "Город", "name": "Unclassified",
                   "url": "https://example.org/uncertain"}]
    })
    write_json(tmp_path, "data/curation/modern-city-photography-v1.json", {
        "items": []
    })
    result = build(tmp_path)
    rows = {norm(x["name"]): x for x in result["entries"]}
    summary = result["summary"]
    assert summary["combined_names"] == 3
    assert summary["name_overlap"] == 1
    assert summary["atlas_with_work"] == 1
    assert summary["atlas_work_references"] == 2
    assert summary["atlas_open_image_references"] == 1
    assert summary["detailed_names"] == 1
    assert summary["names_with_candidates_or_detail"] == 2
    assert summary["unfilled_names"] == 1
    assert summary["orphan_candidate_rows"]["museum"] == 1
    assert rows[norm("Париж")]["status"] == "detailed"
    assert rows[norm("Париж")]["atlas_open_images"] == 1
    assert rows[norm("Париж")]["atlas_works"] == 2
    assert rows[norm("Амальфи (собор)")]["type"] == "place"
    assert rows[norm("Амальфи (собор)")]["status"] == "candidate"
    assert rows[norm("Санкт-Петербург")]["status"] == "seed_only"


def test_name_normalization_does_not_erase_geographic_qualifiers():
    assert norm(" ПАРИЖ  ") == norm("париж")
    assert norm("Амальфи (собор)") != norm("Амальфи")
