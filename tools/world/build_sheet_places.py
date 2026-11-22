#!/usr/bin/env python3
"""Build book/sheet-places.json: for every shipped Benoist sheet, where the building is and which then/now pairs exist.

Inputs: book/benoist-sheets.json, data/curation/benoist-sheet-places-v1.json (building coordinates, see
geocode_sheet_places.py), poc/compare/pairs/*.json (existing comparison pairs). A pair is attached only through the
explicit PAIRS table below (a human decision: the same view of the same building). Nothing is claimed beyond what the
pair JSON itself says: viewpoint status, photo author/date/licence, camera position and heading.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEETS = ROOT / "book" / "benoist-sheets.json"
GEO = ROOT / "data" / "curation" / "benoist-sheet-places-v1.json"
PAIRS_DIR = ROOT / "poc" / "compare" / "pairs"
OUT = ROOT / "book" / "sheet-places.json"
PAIRS = {  # sheet id -> pair ids showing the same view of the same building
    "parismusees-320291945": ["notre-dame-benoist-carnavalet"],
    "parismusees-320291352": ["louvre-colonnade-benoist-carnavalet"],
    "rijks-RP-P-1905-5501": ["tuileries-benoist-rijksmuseum"],
    "parismusees-320290166": ["tuileries-benoist-rijksmuseum"],
    "rijks-RP-P-1905-5499": ["palais-royal-jardin-benoist-rijksmuseum"],
    "parismusees-320295651": ["madeleine-benoist-carnavalet"],
}
# Camera positions read from the Panoramax item itself (GeoJSON point of the picture) where the pair JSON has none.
CAMERAS = {
    "madeleine-benoist-carnavalet": {
        "lat": 48.86933,
        "lon": 2.32395,
        "heading": 21,
        "source": "Panoramax item 38b6d262 (point + azimuth)",
    },
    "palais-royal-jardin-benoist-rijksmuseum": {
        "lat": 48.86418,
        "lon": 2.33737,
        "heading": 20,
        "source": "Panoramax item 200a3dee (point + azimuth)",
    },
}
STATUS_RU = {
    "exact_verified": "точное совпадение: ракурс и геометрия проверены",
    "approximate": "приблизительное совпадение: то же место, перспектива отличается",
    "lost_or_reconstructed": "здание утрачено или перестроено: сравнение по контексту, без наложения",
    "unverified": "ракурс не подтверждён: показываем два кадра отдельно",
}


def pair_info(pair_id: str) -> dict:
    d = json.loads((PAIRS_DIR / f"{pair_id}.json").read_text(encoding="utf-8"))
    status = d.get("viewpoint_status") or ("approximate" if d.get("status") == "candidate_real_pair" else "unverified")
    photo = d.get("photo", {})
    cam = photo.get("camera") if isinstance(photo.get("camera"), dict) else {}
    fallback = CAMERAS.get(pair_id, {})
    return {
        "id": pair_id,
        "status": status,
        "status_ru": STATUS_RU.get(status, status),
        "photo": {
            "author": photo.get("author"),
            "date": photo.get("date"),
            "licence": photo.get("license"),
            "lat": cam.get("lat") or fallback.get("lat"),
            "lon": cam.get("lon") or fallback.get("lon"),
            "heading": cam.get("heading_deg") or photo.get("azimuth_deg") or fallback.get("heading"),
            "camera_source": cam.get("source") or fallback.get("source"),
            "distance_m": photo.get("distance_to_building_m_approx"),
        },
        "viewpoint_note": (d.get("viewpoint") or {}).get("note"),
        "artist_estimate": (d.get("viewpoint") or {}).get("historic_camera_estimate"),
    }


def build() -> dict:
    sheets = json.loads(SHEETS.read_text(encoding="utf-8"))["sheets"]
    places = {}
    for p in json.loads(GEO.read_text(encoding="utf-8"))["places"]:
        for sid in p["sheets"]:
            places[sid] = p
    out = {}
    for s in sheets:
        p = places.get(s["id"])
        entry = {"place": None, "pairs": [pair_info(x) for x in PAIRS.get(s["id"], [])]}
        if p and p.get("lat") is not None:
            entry["place"] = {
                "id": p["id"],
                "name": p["name_ru"],
                "city": p["city"],
                "lat": p["lat"],
                "lon": p["lon"],
                "approximate": True,
                "evidence": p.get("evidence"),
            }
        out[s["id"]] = entry
    return {
        "version": 1,
        "note": "Координаты приблизительные; пары перечислены только там, где есть проверенный кадр.",
        "sheets": out,
    }


def main() -> int:
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    located = sum(1 for v in data["sheets"].values() if v["place"])
    paired = sum(1 for v in data["sheets"].values() if v["pairs"])
    print(f"{len(data['sheets'])} sheets, {located} located, {paired} with a modern photo pair")
    return 0


if __name__ == "__main__":
    sys.exit(main())
