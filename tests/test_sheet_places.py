import json
from pathlib import Path

from tools.world.build_sheet_places import PAIRS, build

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "book/sheet-places.json").read_text(encoding="utf-8"))["sheets"]
SHEETS = json.loads((ROOT / "book/benoist-sheets.json").read_text(encoding="utf-8"))["sheets"]


def test_published_file_matches_its_inputs():
    assert json.loads(json.dumps(build()["sheets"])) == DATA


def test_every_sheet_has_an_entry_and_coordinates_are_plausible():
    assert set(DATA) == {s["id"] for s in SHEETS}
    for sid, e in DATA.items():
        if e["place"]:
            assert -90 < e["place"]["lat"] < 90 and -180 < e["place"]["lon"] < 180 and e["place"]["approximate"], sid


def test_pairs_exist_and_only_claim_what_their_json_says():
    for sid, pair_ids in PAIRS.items():
        assert sid in DATA, sid
        for pid in pair_ids:
            pair = json.loads((ROOT / f"poc/compare/pairs/{pid}.json").read_text(encoding="utf-8"))
            got = next(q for q in DATA[sid]["pairs"] if q["id"] == pid)
            assert got["status"] in {"exact_verified", "approximate", "lost_or_reconstructed", "unverified"}
            if got["status"] == "exact_verified":
                assert pair.get("viewpoint_review") or pair.get("control_points"), pid  # never exact without evidence
            assert got["photo"]["licence"] in {"CC BY-SA 4.0", "CC BY 4.0", "CC0", "CC0 1.0"}, pid
            assert got["photo"]["author"] and got["photo"]["date"], pid


def test_lost_buildings_are_never_offered_as_a_geometric_match():
    for sid in ("rijks-RP-P-1905-5501", "parismusees-320290166"):
        assert [q["status"] for q in DATA[sid]["pairs"]] == ["lost_or_reconstructed"]
