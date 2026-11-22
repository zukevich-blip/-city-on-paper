"""Every shipped sheet is linked to a register work by its museum page; unlinked sheets are listed, never guessed."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Sheets whose record page is not in the register at all (no accession/URL match): shown with a museum link only.
UNLINKED = {"parismusees-320290066", "parismusees-320294285", "parismusees-320291262"}


def test_sheets_link_to_register_without_mixing_artists():
    sheets = json.loads((ROOT / "book/benoist-sheets.json").read_text(encoding="utf-8"))["sheets"]
    works = json.loads((ROOT / "book/benoist-registry.json").read_text(encoding="utf-8"))["works"]
    owner: dict[str, dict] = {}
    for w in works:
        for im in w["images"]:
            assert im not in owner, f"{im} linked to two works"
            owner[im] = w
        assert not w["image"] or w["image"] in w["images"]
    missing = {s["id"] for s in sheets if s["image"] not in owner}
    assert missing == UNLINKED, sorted(missing ^ UNLINKED)
    for s in sheets:
        if s["id"] in UNLINKED:
            assert s["record_url"].startswith("https://") or s["record_url"].startswith("http://")
    summary = json.loads((ROOT / "book/benoist-registry.json").read_text(encoding="utf-8"))["summary"]
    assert summary["shipped_with_image"] == len(sheets)
    assert summary["shipped_matched_to_register"] == len(sheets) - len(UNLINKED)
