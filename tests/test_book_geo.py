"""Open map layers of the Île de la Cité: licence and attribution travel with the data; no invented heights."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENCES = {"vasserot": "ODbL", "ohm": "CC0", "ign": "Licence Ouverte Etalab 2.0"}


def test_layers_carry_licence_attribution_and_only_rings():
    for k, lic in LICENCES.items():
        d = json.loads((ROOT / f"book/geo/cite-{k}.json").read_text(encoding="utf-8"))
        assert d["licence"] == lic and d["attribution"] and d["note"]
        assert len(d["features"]) > 300
        for f in d["features"]:
            assert set(f) <= {"r", "s", "e", "n"}, f"{k}: unexpected field (heights are guesses and are not shipped)"
            assert len(f["r"]) >= 4 and all(2.30 < x < 2.40 and 48.8 < y < 48.9 for x, y in f["r"])
