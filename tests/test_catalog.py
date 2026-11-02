"""Offline checks of the curated catalog (data/catalog/works) against the schema rules."""
import copy
import csv
import json

import pytest

from tools.catalog import ledger
from tools.catalog.validate import DEFAULT_WORKS, ROOT, load_enums, validate_dir, validate_record

WORKS = sorted(DEFAULT_WORKS.glob("*.json"))


def test_catalog_directory_validates():
    n, errors = validate_dir()
    assert n >= 20
    assert errors == []


@pytest.mark.parametrize("path", WORKS, ids=[p.stem for p in WORKS])
def test_each_record(path):
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert validate_record(rec, load_enums()) == []
    assert path.stem == rec["id"]


def _sample():
    return json.loads(WORKS[0].read_text(encoding="utf-8"))


def test_validator_rejects_verified_without_evidence():
    rec = _sample()
    rec["review"]["geo"] = {"status": "verified"}
    assert any("no evidence_urls" in e for e in validate_record(rec, load_enums()))


def test_validator_rejects_bad_enum_and_missing_field():
    rec = copy.deepcopy(_sample())
    rec["agents"][0]["role"] = "genius"
    del rec["rights"]
    errs = validate_record(rec, load_enums())
    assert any("role 'genius'" in e for e in errs)
    assert any("missing required field 'rights'" in e for e in errs)


def test_validator_detects_duplicate_ids(tmp_path):
    rec = _sample()
    (tmp_path / f"{rec['id']}.json").write_text(json.dumps(rec), encoding="utf-8")
    (tmp_path / "copy.json").write_text(json.dumps(rec), encoding="utf-8")
    _, errors = validate_dir(tmp_path)
    assert any("duplicate id" in e for e in errors)
    assert any("file name does not match" in e for e in errors)


def test_ledger_csv_in_sync_with_records():
    path = ROOT / "data" / "catalog" / "ledger-2026-11-01.csv"
    with path.open(encoding="utf-8") as fh:
        on_disk = list(csv.DictReader(fh))
    assert on_disk == ledger.rows()


def test_no_coordinates_without_justification():
    for p in WORKS:
        place = json.loads(p.read_text(encoding="utf-8")).get("place", {})
        assert "lat" not in place, f"{p.stem}: coordinates need a cited source"
