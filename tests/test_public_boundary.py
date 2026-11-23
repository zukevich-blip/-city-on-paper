"""PUBLIC vs PRIVATE_RESEARCH boundary.

Nothing with unconfirmed rights may reach git, Pages, a public ZIP or an artifact.
"""

import json
import subprocess
from pathlib import Path

import pytest

from tools.private import fetch_private_archive as fpa
from tools.release import build_public_site as bps

ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}


def test_private_archive_is_ignored_and_forbidden_in_the_public_bundle():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "private-archive/" in ignore and "data/private/" in ignore
    for rel in ("private-archive", "data/private", "data/research/benoist", "research"):
        assert rel in bps.FORBIDDEN, rel
    for rel in (*bps.PAGES, *bps.DATA, *bps.ASSETS):
        parts = rel.split("/")
        assert parts[0] not in ("private-archive", "research") and rel.split("/")[:3] != [
            "data",
            "research",
            "benoist",
        ], rel
        assert parts[:2] != ["data", "private"], rel


def test_no_workflow_copies_the_private_tier_into_an_artifact():
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = wf.read_text(encoding="utf-8")
        assert "private-archive" not in text and "data/private" not in text, wf.name


def test_every_image_shipped_with_the_book_is_an_open_confirmed_sheet():
    sheets = json.loads((ROOT / "book/benoist-sheets.json").read_text(encoding="utf-8"))["sheets"]
    assert all(s["rights"].startswith(("CC0", "Public Domain Mark", "CC BY")) for s in sheets)
    declared = {s["image"] for s in sheets} | {i["image"] for s in sheets for i in s.get("impressions", [])}
    shipped = {
        p.relative_to(ROOT / "book").as_posix()
        for p in (ROOT / "book" / "img").rglob("*")
        if p.suffix.lower() in IMAGE_SUFFIXES
    }
    assert shipped <= declared, sorted(shipped - declared)


def test_no_image_is_tracked_under_private_paths():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split(
        "\n"
    )
    assert not [p for p in tracked if p.startswith(("private-archive/", "data/private/"))]


def test_private_fetcher_refuses_ci_and_rights_confirmed_records():
    assert fpa.in_ci({"GITHUB_ACTIONS": "true"}) and not fpa.in_ci({})
    recs = [
        {"record_id": "a", "image_url": "u", "rights_status": "open_confirmed"},
        {"record_id": "b", "image_url": "u", "rights_status": "rights_pending"},
        {"record_id": "c", "image_url": None, "rights_status": "unknown"},
        {"record_id": "d", "image_url": "u", "rights_status": "unknown"},
    ]
    assert [r["record_id"] for r in fpa.wanted(recs)] == ["b", "d"]


def test_private_fetcher_cannot_write_outside_the_vault():
    with pytest.raises(ValueError):
        fpa.target_path("../../book/img/x.jpg")
    assert fpa.target_path("ok.jpg").is_relative_to(fpa.VAULT.resolve())
