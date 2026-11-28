# ruff: noqa: E501
"""One gallery fund: every work has a local image, a thumbnail, a museum record, a rights statement and a role-aware author line;
nothing previously confirmed is lost (all Benoist sheets, all album plates and all exhibition works are in the fund)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "book"


def test_fund_keeps_everything_confirmed_and_every_work_is_complete():
    g = json.loads((BOOK / "gallery.json").read_text(encoding="utf-8"))["works"]
    ids = [w["id"] for w in g]
    assert len(ids) == len(set(ids)) and len(g) >= 550
    sheets = json.loads((BOOK / "benoist-sheets.json").read_text(encoding="utf-8"))["sheets"]
    assert {"bs-" + s["id"] for s in sheets} <= set(ids), "a Benoist sheet was lost"
    alb = json.loads((BOOK / "albums/paris-dans-sa-splendeur.json").read_text(encoding="utf-8"))
    assert len([i for i in ids if i.startswith("al-")]) == len(alb["plates"])
    ex = json.loads((BOOK / "exhibitions.json").read_text(encoding="utf-8"))["exhibitions"]
    assert {"ex-" + w["id"] for e in ex for w in e["works"]} <= set(ids)
    for w in g:
        assert (BOOK / w["i"]).stat().st_size > 3000 and (BOOK / w["th"]).stat().st_size > 500, w["id"]
        assert w["u"].startswith("https://") and w["m"] and w["n"] and w["r"] and w["a"], w["id"]
        assert w["set"] in {"benoist", "album", "exhibit", "open"}


def test_other_masters_are_never_labelled_benoist_and_open_rights_are_museum_statements():
    g = json.loads((BOOK / "gallery.json").read_text(encoding="utf-8"))["works"]
    for w in g:
        if w["set"] in {"open", "exhibit"}:
            assert "benoist" not in w["a"].lower(), w["id"]
            assert any(k in w["r"] for k in ("openaccess=1", "isPublicDomain", "is_public_domain", "CC0", "publicdomain", "Public Domain")), (w["id"], w["r"])
        if w["set"] == "album":
            assert "benoist" not in w["a"].lower()
    arts = {w["a"] for w in g if w["set"] == "open"}
    assert len(arts) >= 15
