import json
from pathlib import Path

from tools.world.build_benoist_sheets import build, eligible, sheet

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "book/benoist-sheets.json").read_text(encoding="utf-8"))


def test_published_file_matches_the_harvest():
    assert DATA == build()
    assert len(DATA["sheets"]) >= 20


def test_every_sheet_is_open_imaged_and_stored_locally():
    kinds = {"paris": 0, "rijks": 0}
    for s in DATA["sheets"]:
        kinds["rijks" if s["holder"] == "Rijksmuseum" else "paris"] += 1
        assert (ROOT / "book" / s["image"]).stat().st_size > 20_000, s["id"]
        assert s["accession"] and s["record_url"].startswith("https://")
        if s["holder"] == "Rijksmuseum":
            assert s["rights"] == "Public Domain Mark" and "publicdomain/mark" in s["rights_url"]
            assert s["record_url"].startswith("https://www.rijksmuseum.nl/")
            assert any("Benoist" in c["name"] for c in s["creators"]), s["id"]
        else:
            assert s["rights"].startswith("CC0") and s["rights_url"].endswith("publicdomain/zero/1.0/")
            assert "parismuseescollections.paris.fr/" in s["record_url"]
            assert any("Benoist" in n for n in s["participants"]), s["id"]
            assert "impression_of" not in s  # a second impression is counted on its first sheet, never twice
    assert kinds["rijks"] == 22 and kinds["paris"] >= 11
    batch = json.loads((ROOT / "data/curation/benoist-parismusees-batch-v1.json").read_text(encoding="utf-8"))
    assert kinds["paris"] == len([r for r in batch["records"] if not r["impression_of"]])


def test_paris_musees_batch_states_cc0_for_each_file_and_groups_impressions():
    batch = json.loads((ROOT / "data/curation/benoist-parismusees-batch-v1.json").read_text(encoding="utf-8"))
    assert (
        len(batch["records"]) >= 13
    )  # the museum throttles big files: failures are recorded and retried, never dropped
    assert all("CC0" in r["rights"] and r["rights_url"].endswith("publicdomain/zero/1.0/") for r in batch["records"])
    impressions = {r["node"]: r["impression_of"] for r in batch["records"] if r["impression_of"]}
    assert impressions.items() >= {"320288773": "320288755", "320291365": "320291352"}.items()
    shown = {s["accession"] for s in DATA["sheets"] if s["holder"].startswith("Paris")}
    assert "node 320288773" not in shown and "node 320288755" in shown


def test_roles_are_kept_as_the_museum_states_them():
    s = sheet(
        {
            "id": "x",
            "title_original": "T",
            "holder": "H",
            "accession_id": "A",
            "record_url": "u",
            "image_rights_statement": "r",
            "creators": [
                {"name": "Auguste Bry", "role_as_stated": "printer (person)"},
                {"name": "P. B.", "role_as_stated": "odd"},
            ],
        }
    )
    assert s["creators"][0]["role_ru"] == "печатник" and s["creators"][1]["role_ru"] == "odd"


def test_only_confident_open_pdm_rijks_records_qualify():
    base = {
        "source": "rijks",
        "rights_class": "open",
        "image_url": "u",
        "attribution_confidence": "high",
        "image_rights_statement": "https://creativecommons.org/publicdomain/mark/1.0/",
    }
    assert eligible(base)
    for change in (
        {"source": "europeana"},
        {"rights_class": "link"},
        {"image_url": None},
        {"attribution_confidence": "medium"},
        {"image_rights_statement": "http://rightsstatements.org/vocab/InC/1.0/"},
    ):
        assert not eligible({**base, **change})
