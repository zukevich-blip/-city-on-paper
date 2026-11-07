#!/usr/bin/env python3
"""Build eras/data/atlas.json: every European city of the museum + every Benoist place (Issue #34, v2).

Inputs (committed):
  data/vision-lab/europe-cities.json   - museum city list with coordinates (OSM Nominatim, 4 fixed by hand)
  data/vision-lab/benoist-places.json  - Benoist gazetteer: places, works, rights (optional)
  data/vision-lab/portal-georef.json   - lon/lat -> pixel model for the 1769 portal map (optional)
  data/vision-lab/overrides.json       - portal image, featured cities
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VL = ROOT / "data" / "vision-lab"
OUT = ROOT / "eras" / "data" / "atlas.json"
FEATURED = {"Париж": "paris", "Флоренция": "florence", "Неаполь": "naples"}
TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
              ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u",
               "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya"], strict=True))


def slug(name: str) -> str:
    s = "".join(TR.get(ch, ch) for ch in name.lower())
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def norm(name: str) -> str:
    return re.sub(r"[^a-zа-яё]", "", name.lower().replace("ё", "е"))


def load(name: str):
    p = VL / name
    return json.loads(p.read_text("utf-8")) if p.exists() else None


def portal_model():
    g = load("portal-georef.json")
    if not g:
        return None, None
    m = g["model"]
    cx, cy = m["coef_px"], m["coef_py"]
    terms = m["terms"]  # list of [i, j] exponents of (x, y) where x, y = normalised lon, lat
    lon0, lat0, s = m["lon0"], m["lat0"], m["scale"]

    def predict(lat: float, lon: float):
        x, y = (lon - lon0) / s, (lat - lat0) / s
        vals = [x ** i * y ** j for i, j in terms]
        return (sum(a * v for a, v in zip(cx, vals, strict=True)),
                sum(a * v for a, v in zip(cy, vals, strict=True)))
    return predict, g


def build() -> dict:
    ov = load("overrides.json")
    eu = load("europe-cities.json")["cities"]
    ben = load("benoist-places.json") or {"places": []}
    predict, g = portal_model()
    W, H = ov["portal"]["width"], ov["portal"]["height"]
    dom = (g or {}).get("domain")
    cities: dict[str, dict] = {}
    for c in eu:
        cities[norm(c["name"])] = {"id": FEATURED.get(c["name"]) or slug(c["name"]), "name": c["name"],
                                   "name_orig": None, "country": c["country"], "area": None,
                                   "lat": c["lat"], "lon": c["lon"],
                                   "coord_source": "OpenStreetMap Nominatim" if c.get("osm") else c.get("display", ""),
                                   "benoist": False, "works": [], "albums": []}
    for p in ben.get("places", []):
        key = norm(p["name_ru"])
        c = cities.get(key)
        if not c:
            c = cities[key] = {"id": slug(p["name_ru"]) or p["id"], "name": p["name_ru"],
                               "name_orig": p.get("name_orig"), "country": p.get("country", ""),
                               "area": p.get("region"), "lat": p["lat"],
                               "lon": p["lon"], "coord_source": p.get("coord_source", ""), "benoist": False,
                               "works": [], "albums": []}
        c["name_orig"] = c["name_orig"] or p.get("name_orig")
        c["area"] = c["area"] or p.get("region")
        c["benoist"] = True
        c["kind"] = p.get("kind")
        c["albums"] = sorted(set(c["albums"]) | set(p.get("albums") or []))
        for w in p.get("works", []):
            open_ = w.get("rights_class") == "open"
            c["works"].append({"title": w.get("title"), "artist": w.get("artist"), "date": w.get("date"),
                               "institution": w.get("institution"), "url": w.get("url"),
                               "image": w.get("image") if open_ else None, "rights_class": "open" if open_ else "link",
                               "rights_label": (w.get("rights") or "")[:90], "basis": w.get("attribution_basis")})
    for c in cities.values():
        c["featured"] = FEATURED.get(c["name"])
        c["xy"] = None
        inside = not dom or (dom["lat_min"] <= c["lat"] <= dom["lat_max"]
                             and dom["lon_min"] <= c["lon"] <= dom["lon_max"])
        if predict and inside:
            x, y = predict(c["lat"], c["lon"])
            if 0 <= x <= W and 0 <= y <= H:
                c["xy"] = [round(x, 1), round(y, 1)]
    # verified glyph positions win over the model
    for cid, pin in ov["portal"]["pins"].items():
        for c in cities.values():
            if c["featured"] == cid:
                c["xy"] = [pin["x"], pin["y"]]
    rows = sorted(cities.values(), key=lambda c: c["name"])
    ids = [c["id"] for c in rows]
    assert len(ids) == len(set(ids)), "duplicate city ids"
    keys = ("image", "width", "height", "title", "credit", "object_url", "rights", "alt")
    portal = {k: ov["portal"][k] for k in keys}
    portal["image_small"] = ov["portal"].get("image_small")
    note = ("Метки городов рассчитаны по модели привязки карты"
            + (f" ({g['model_name']}, средняя ошибка ≈{g['loo_rms_px']:.0f} px)" if g else "")
            + "; метки Парижа, Флоренции и Неаполя сверены со знаками городов на самой карте.")
    return {"version": "2026-11-07", "portal": portal, "portal_note": note,
            "regions": sorted({c["country"] for c in rows if c["country"]}),
            "counts": {"cities": len(rows), "benoist_places": sum(c["benoist"] for c in rows),
                       "benoist_works": sum(len(c["works"]) for c in rows),
                       "benoist_open_images": sum(1 for c in rows for w in c["works"] if w["image"]),
                       "on_portal": sum(1 for c in rows if c["xy"])},
            "cities": rows}


if __name__ == "__main__":
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(d["counts"])
