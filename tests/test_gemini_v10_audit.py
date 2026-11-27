"""The Gemini v10 audit keeps the GPT findings fixed: no Paris for Jersey, no [0, 0], no borrowed authorship."""
import json
from pathlib import Path

from tools.world.audit_gemini_v10 import coords, person, place

ROOT = Path(__file__).resolve().parents[1]


def test_unknown_coordinates_never_become_a_place():
    for bad in (None, [None, None], [0, 0], [2.3499, 48.853], [1.0], "x"):
        assert coords(bad) is None
    assert coords([2.35, 48.85]) == [2.35, 48.85]


def test_person_rules():
    assert person("Guillaume Philippe Benoist", "x")[0] is None
    assert person("Eugène Cicéri (1813-1890)", "Vue")[0] is None
    assert person("Man vyi", "Album Félix Benoist 01")[0] == "Félix Benoist"
    assert person("Benoist, Philippe (1813-1905?). Dessinateur", "Vue")[0] == "Philippe Benoist"


def test_publisher_mentions_do_not_decide_the_place():
    assert place("Album de l'Île de Jersey Félix Benoist 06")[0] == "Джерси и Гернси"
    assert place("Planche sans nom")[0] is None


def test_audit_file_matches_the_findings():
    s = json.loads((ROOT / "data/research/benoist/gemini-v10-audit.json").read_text(encoding="utf-8"))
    sm = s["summary"]
    assert sm["jersey_after_audit_in_paris"] == 0 and sm["jersey_pages_linked_to_paris_by_harvest"] == 20
    assert sm["album_pages"] == 137 and sm["album_pages_unique_images"] == 102
    assert all(r["coords"] is None for r in s["records"])
    assert all(r["licence_status"].startswith("claimed") for r in s["records"])
    assert not any("guillaume" in (r["artist"] or "").lower() for r in s["records"])
