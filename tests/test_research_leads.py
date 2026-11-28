"""Research leads keep their honesty fields: what was read, what was not, and no open rights without a statement."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_italy_structure_has_three_parts_and_honest_statuses():
    d = json.loads((ROOT / "data/research/benoist/italy-rome-v1.json").read_text(encoding="utf-8"))
    assert [p["id"] for p in d["parts"]] == ["antique-rome", "christian-rome", "rome-19th-century"]
    for p in d["parts"]:
        for lead in p["leads"]:
            if lead.get("url"):
                assert lead["source_status"] in {"read", "not_read", "page_read_no_details"}
                assert lead["rights"] != "open", lead["title"]
            if lead.get("source_status") == "not_read":
                assert lead.get("reason")


def test_albums_do_not_claim_order_without_a_source():
    d = json.loads((ROOT / "data/research/benoist/albums-v1.json").read_text(encoding="utf-8"))["albums"]
    for a in d:
        assert a["status"] in {"restored_in_book", "lead"}
        if a["status"] == "restored_in_book":
            assert a["order_basis"] and (ROOT / a["where"]).exists()
