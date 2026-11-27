"""Exhibitions and the album reader: every work carries a museum rights statement, a record link and a local image;
the album keeps the edition's own plate order and never attributes a plate to Benoist on its own."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "book"


def test_exhibition_works_are_open_sourced_and_local():
    d = json.loads((BOOK / "exhibitions.json").read_text(encoding="utf-8"))
    assert len(d["exhibitions"]) >= 3
    ids = set()
    for e in d["exhibitions"]:
        assert len(e["works"]) >= 10, e["id"]
        for w in e["works"]:
            assert w["id"] not in ids
            ids.add(w["id"])
            assert (BOOK / w["image"]).stat().st_size > 5000, w["id"]
            assert w["record_url"].startswith("https://") and w["accession"] and w["institution"], w["id"]
            open_marks = ("openaccess=1", "isPublicDomain: True", "is_public_domain: true", "CC0", "publicdomain")
            assert any(k in w["rights"] for k in open_marks), w["rights"]
            assert w["credit"].startswith(w["institution"]), w["id"]


def test_album_order_is_the_editions_own_and_unattributed():
    a = json.loads((BOOK / "albums/paris-dans-sa-splendeur.json").read_text(encoding="utf-8"))
    nums = [p["n"] for p in a["plates"]]
    assert nums == sorted(nums) and nums[0] == 1 and nums[-1] == 70 and len(nums) == 71
    assert [p["n"] for p in a["plates"] if p["bis"]] == [60]
    assert len(a["covers"]) == 3 and a["coverage"]["plates_missing"] == []
    assert "не приписана Бенуа" in a["attribution_note"] and "порядок самого издания" in a["order_basis"]
    for p in a["plates"]:
        assert (BOOK / p["image"]).exists() and p["record_url"].startswith("https://digi.ub.uni-heidelberg.de/")
        assert "benoist" not in json.dumps(p, ensure_ascii=False).lower()
