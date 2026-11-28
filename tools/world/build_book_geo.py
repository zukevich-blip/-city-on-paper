"""Compact map layers of the Île de la Cité for the book's place map (open data only, attribution kept).

in:  data/research/benoist/gemini-v10/geo/*.geojson  (Gemini v10 copies of ALPAGE, IGN BD TOPO, OpenHistoricalMap)
out: book/geo/cite-{vasserot,ohm,ign}.json  (rings + minimal properties; no heights, they are guesses)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/research/benoist/gemini-v10/geo"
OUT = ROOT / "book/geo"
LAYERS = {
    "vasserot": ("alpage-vasserot-ile-de-la-cite.geojson", "ODbL", "Arch. nat. F31 73-96 – Arch. Paris © ALPAGE",
                 "Участки кадастра Вассеро, 1810–1836 (участки, а не здания)"),
    "ohm": ("ohm-buildings-ile-de-la-cite.geojson", "CC0", "OpenHistoricalMap",
            "Здания по OpenHistoricalMap: даты вносят волонтёры, не архивный обмер"),
    "ign": ("ign-modern-buildings-ile-de-la-cite.geojson", "Licence Ouverte Etalab 2.0", "© IGN France, BD TOPO",
            "Здания сегодня"),
}


def ring(g: dict) -> list:
    """Outer ring of the largest polygon, 5 decimals (~1 m)."""
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    outer = max((p[0] for p in polys), key=len)
    return [[round(x, 5), round(y, 5)] for x, y in outer]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for key, (fname, lic, attr, note) in LAYERS.items():
        fc = json.loads((SRC / fname).read_text(encoding="utf-8"))
        feats = []
        for f in fc["features"]:
            p = f["properties"]
            row = {"r": ring(f["geometry"])}
            if key == "ohm":
                row.update(s=p.get("startYear"), e=p.get("endYear"))
                if p.get("name") and p["name"] != "yes":
                    row["n"] = p["name"]
            elif key == "vasserot":
                row.update(s=p.get("startYear"), e=p.get("endYear"))
            feats.append(row)
        doc = {"layer": key, "licence": lic, "attribution": attr, "note": note, "features": feats}
        text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        (OUT / f"cite-{key}.json").write_text(text, encoding="utf-8")
        print(key, len(feats), (OUT / f"cite-{key}.json").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
