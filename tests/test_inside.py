# ruff: noqa: E501
"""Building dossiers use real materials only: gallery ids exist, extras carry credit and licence, gaps are stated."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "book"


def test_inside_dossiers_are_real_and_honest():
    d = json.loads((BOOK / "inside.json").read_text(encoding="utf-8"))["buildings"]
    ids = {w["id"] for w in json.loads((BOOK / "gallery.json").read_text(encoding="utf-8"))["works"]}
    assert [b["id"] for b in d] == ["madeleine", "sainte-chapelle", "pantheon-paris", "pantheon-rome", "notre-dame"]
    for b in d:
        for gid in b["facade"] + b["interior"]:
            assert gid in ids, (b["id"], gid)
        for x in b["plan"] + b["section"] + b["extras"]:
            assert (BOOK / x["i"]).stat().st_size > 5000, x["i"]
            assert x["credit"] and x["licence"] in {"CC0", "CC0 1.0", "Public Domain", "CC BY-SA 3.0", "CC BY-SA 4.0"}, x["caption"]
        for x in b["modern"]:
            assert (BOOK / x["i"]).exists() and x["credit"] and x["licence"]
        if not (b["interior"] or b["extras"]):
            assert "journey" not in b, "no door without a real interior"
        assert b["missing"], b["id"]
    mad = next(b for b in d if b["id"] == "madeleine")
    assert mad["journey"]["door"] and len(mad["modern"]) == 2 and mad["plan"]
