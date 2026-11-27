import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACES = json.loads((ROOT / "data/stories/benoist-places-v1.json").read_text(encoding="utf-8"))["places"]
SHEET_IDS = {s["id"] for s in json.loads((ROOT / "book/benoist-sheets.json").read_text(encoding="utf-8"))["sheets"]}
EXPECTED = {"madeleine", "notre-dame", "sainte-chapelle", "louvre-colonnade", "palais-royal", "tuileries"}
STATUSES = {"exists", "lost", "rebuilt"}


def test_the_six_places_are_present_with_unique_ids():
    ids = [p["id"] for p in PLACES]
    assert len(ids) == len(set(ids))
    assert set(ids) == EXPECTED


def test_every_place_has_the_required_fields_and_no_empty_text():
    for p in PLACES:
        for key in ("id", "name_ru", "name_fr", "coords_source_url", "lede_ru", "print_licence_note"):
            assert isinstance(p[key], str) and p[key].strip(), (p["id"], key)
        assert p["status"] in STATUSES, p["id"]
        assert 48.8 < p["lat"] < 48.9 and 2.2 < p["lon"] < 2.4, p["id"]
        assert p["coords_source_url"].startswith("https://"), p["id"]
        assert p["changes_ru"] and all(c.strip() for c in p["changes_ru"]), p["id"]
        assert p["unknowns_ru"] and all(u.strip() for u in p["unknowns_ru"]), p["id"]


def test_every_place_has_at_least_three_dated_sourced_facts():
    for p in PLACES:
        assert len(p["facts"]) >= 3, p["id"]
        for f in p["facts"]:
            assert f["text_ru"].strip(), p["id"]
            assert f["date"].strip() and re.search(r"\d{3,4}|век", f["date"]), (p["id"], f["date"])
            assert f["source_url"].startswith("https://"), (p["id"], f["source_url"])
            assert f["source_name"].strip(), p["id"]


def test_related_sheets_exist_in_the_book():
    for p in PLACES:
        assert p["related_sheet_ids"], p["id"]
        assert set(p["related_sheet_ids"]) <= SHEET_IDS, p["id"]


def test_old_plan_points_to_an_existing_file():
    for p in PLACES:
        plan = p["old_plan"]
        if plan is not None:
            assert (ROOT / plan["file"]).is_file(), p["id"]
            assert plan["note"].strip(), p["id"]


def test_the_lost_palace_is_marked_lost_and_never_promises_a_matching_modern_view():
    tuileries = next(p for p in PLACES if p["id"] == "tuileries")
    assert tuileries["status"] == "lost"
    assert "1883" in " ".join(f["date"] for f in tuileries["facts"])
    assert "нельзя" in tuileries["lede_ru"] or "Не подгоняйте" in " ".join(tuileries["changes_ru"])
