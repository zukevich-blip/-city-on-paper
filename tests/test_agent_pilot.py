"""Test the deterministic read-only source and design agent pilot."""
from __future__ import annotations

from tools.agents.pilot import ROOT, SOURCES, audit


def test_real_museum_probe_is_safe_and_reproducible():
    report = audit(ROOT, live_sources=False)
    assert report["passed"], report["quality_gates"]
    assert len(report["pages"]) == 6
    assert len(report["official_sources"]) == 3
    assert report["city_seed_names"] is not None
    assert all(x["reachability"]["status"] == "not_checked_offline"
               for x in report["official_sources"].values())
    assert report["meaning"].startswith("Read-only")
    assert not report["missing"]


def test_evidence_scope_not_misrepresented():
    assert SOURCES["loc_benoist_madeleine"]["rights_note"] != "CC0"
    report = audit(ROOT, live_sources=False)
    assert report["quality_gates"]["original_rights_not_auto_cc0"]
    assert not any("verified_artworks" in x for x in report["official_sources"])
    assert all(x["status"] in ("executing", "connected", "independent_run",
                               "not_installed", "awaiting_external_link")
               for x in report["recommended_roles"])
