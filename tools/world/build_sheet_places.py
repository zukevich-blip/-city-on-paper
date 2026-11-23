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
GROUPS = ROOT / "data" / "research" / "benoist" / "duplicate-groups-v1.json"
PAIRS_DIR = ROOT / "poc" / "compare" / "pairs"
OUT = ROOT / "book" / "sheet-places.json"
PAIRS = {  # sheet id -> pair ids showing the same view of the same building
    "rijks-RP-P-1905-5501": [
        "tuileries-benoist-rijksmuseum",
    ],
    "parismusees-320290166": [
        "tuileries-benoist-rijksmuseum",
    ],
    "rijks-RP-P-1905-5499": [
        "palais-royal-jardin-benoist-rijksmuseum",
    ],
    "parismusees-320295651": [
        "madeleine-benoist-carnavalet",
    ],
    # Panoramax photos of several years added 2026-11-22: same building, status per pair JSON
    # (see data/research/benoist/photos-by-place-v1.json)
    "parismusees-320292157": [
        "vendome-pm320292157-f43dc246",
    ],
    "parismusees-320291197": [
        "luxembourg-pm320291197-3b758447",
        "luxembourg-pm320291197-0ee50c84",
        "luxembourg-pm320291197-9ea84c7a",
    ],
    "parismusees-320291945": [
        "notre-dame-benoist-carnavalet",
        "notre_dame-pm320291945-5c4e33a2",
        "notre_dame-pm320291945-dd602ce3",
        "notre_dame-pm320291945-33acc54c",
    ],
    "rijks-RP-P-1905-5500": [
        "notre_dame-rijks-5500-5c4e33a2",
        "notre_dame-rijks-5500-dd602ce3",
    ],
    "parismusees-320291352": [
        "louvre-colonnade-benoist-carnavalet",
        "louvre_colonnade-pm320291352-01ca11e0",
        "louvre_colonnade-pm320291352-9229020f",
    ],
    "rijks-RP-P-1905-5505": [
        "louvre_colonnade-rijks-5505-01ca11e0",
    ],
    "parismusees-320050912": [
        "saint_sulpice-pm320050912-98282647",
        "saint_sulpice-pm320050912-e3c70c4a",
    ],
    "parismusees-320290954": [
        "saint_sulpice-pm320290954-98282647",
    ],
    "parismusees-320291262": [
        "bourse-pm320291262-d7a724ab",
        "bourse-pm320291262-ca6cd57d",
    ],
    "parismusees-320290537": [
        "hotel_de_ville-pm320290537-f67766f2",
    ],
    "rijks-RP-P-1905-5498": [
        "hotel_de_ville-rijks-5498-6afa5131",
    ],
    "rijks-RP-P-1905-5506": [
        "pantheon-rijks-5506-451335cc",
        "pantheon-rijks-5506-5116b338",
        "pantheon-rijks-5506-5974302a",
    ],
    "rijks-RP-P-1905-5503": [
        "porte_saint_denis-rijks-5503-9e737168",
        "porte_saint_denis-rijks-5503-0e034840",
        "porte_saint_denis-rijks-5503-2cb1a095",
    ],
    "parismusees-320262846": [
        "bastille-pm320262846-0f8bd6c7",
        "bastille-pm320262846-5812222c",
        "bastille-pm320262846-c2c532bf",
    ],
    "rijks-RP-P-1905-5496": [
        "bastille-rijks-5496-0f8bd6c7",
        "bastille-rijks-5496-5812222c",
        "bastille-rijks-5496-c2c532bf",
    ],
    "parismusees-200009791": [
        "halles_innocents-pm200009791-34348d73",
        "halles_innocents-pm200009791-4d4442b8",
    ],
    "parismusees-320294285": [
        "chateau_eau-pm320294285-69edbfd4",
        "chateau_eau-pm320294285-25cc66b6",
        "chateau_eau-pm320294285-5f5a19ad",
        "chateau_eau-pm320294285-78bbe58d",
    ],
    "parismusees-320291211": [
        "rivoli-pm320291211-c0239b58",
        "rivoli-pm320291211-c5b57013",
    ],
    "parismusees-320295653": [
        "madeleine-pm320295653-800c5582",
    ],
    "parismusees-320295656": [
        "madeleine-pm320295656-800c5582",
    ],
    "parismusees-320299869": [
        "pont_royal-pm320299869-d0859ca4",
    ],
    "rijks-RP-P-1908-259": [
        "bologna-rijks-259-550bb3e3",
    ],
    "rijks-RP-P-1908-1979": [
        "brussels-rijks-1979-4ad71c94",
    ],
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


def propagate_through_duplicates(sheets: list[dict], out: dict) -> None:
    """A sheet that a high-confidence duplicate group says is another impression of a paired sheet shares its pairs."""
    if not GROUPS.exists():
        return
    sys.path.insert(0, str(ROOT))
    from tools.world.build_benoist_registry import norm_url

    by_url = {norm_url(s["record_url"]): s["id"] for s in sheets}
    for g in json.loads(GROUPS.read_text(encoding="utf-8")).get("high_groups", []):
        ids = [by_url[norm_url(m.get("record_url"))] for m in g["members"] if norm_url(m.get("record_url")) in by_url]
        source = next((i for i in ids if out[i]["pairs"]), None)
        for i in ids:
            if source and not out[i]["pairs"]:
                out[i]["pairs"] = [{**q, "via_duplicate_of": source} for q in out[source]["pairs"]]


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
    propagate_through_duplicates(sheets, out)
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
