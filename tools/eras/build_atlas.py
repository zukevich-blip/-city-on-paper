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
import math
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


COMMONS = re.compile(r"^https://upload\.wikimedia\.org/wikipedia/commons/(?:thumb/)?([0-9a-f])/([0-9a-f]{2})/([^/?#]+)")


def commons_image(url: str | None) -> str | None:
    """Rebuild a clean Commons thumbnail URL (strip tracking queries that break thumb paths)."""
    if not url:
        return url
    m = COMMONS.match(url)
    if not m:
        return url.split("?utm_")[0]
    a, ab, name = m.groups()
    if re.search(r"\.(tiff?|pdf|djvu)$", name, re.I):
        return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{a}/{ab}/{name}/lossy-page1-500px-{name}.jpg"
    if name.lower().endswith(".svg"):
        return f"https://upload.wikimedia.org/wikipedia/commons/{a}/{ab}/{name}"
    return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{a}/{ab}/{name}/500px-{name}"


def load(name: str):
    p = VL / name
    return json.loads(p.read_text("utf-8")) if p.exists() else None


def portal_model():
    """2nd-order polynomial lon/lat -> pixel of the 1769 map (51 GCPs; see portal-georef.json)."""
    g = load("portal-georef.json")
    if not g:
        return None, None, None
    m = g["model"]
    nz = m["normalization"]
    exps = [tuple(int(part[2:]) for part in t.split("*")) for t in m["terms"]]  # "u^1*v^0" -> (1, 0)

    def predict(lat: float, lon: float):
        u, v = (lon - nz["lon0"]) / nz["scale"], (lat - nz["lat0"]) / nz["scale"]
        vals = [u ** a * v ** b for a, b in exps]
        return (sum(c * t for c, t in zip(m["coef_px"], vals, strict=True)),
                sum(c * t for c, t in zip(m["coef_py"], vals, strict=True)))

    hull = g["validity"]["convex_hull_lonlat"]

    def inside(lat: float, lon: float, margin: float = 0.3) -> bool:
        cx = sum(p[0] for p in hull) / len(hull)
        cy = sum(p[1] for p in hull) / len(hull)
        poly = []
        for x, y in hull:
            d = math.hypot(x - cx, y - cy) or 1.0
            poly.append((x + (x - cx) / d * margin, y + (y - cy) / d * margin))
        res = False
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
            if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                res = not res
        return res
    return predict, inside, g


def build() -> dict:
    ov = load("overrides.json")
    eu = load("europe-cities.json")["cities"]
    ben = load("benoist-places.json") or {"places": []}
    predict, inside_hull, g = portal_model()
    W, H = ov["portal"]["width"], ov["portal"]["height"]
    cities: dict[str, dict] = {}
    for c in eu:
        cities[norm(c["name"])] = {"id": FEATURED.get(c["name"]) or slug(c["name"]), "name": c["name"],
                                   "name_orig": None, "country": c["country"], "area": None,
                                   "lat": c["lat"], "lon": c["lon"],
                                   "coord_source": "OpenStreetMap Nominatim" if c.get("osm") else c.get("display", ""),
                                   "benoist": False, "works": [], "albums": []}
    for p in ben.get("places", []):
        base = p["name_ru"].split(" (")[0].split(",")[0]  # "Севилья (пл. ...)" -> "Севилья"
        key = norm(base) if norm(base) in cities else norm(p["name_ru"])
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
            url = w.get("url") or ""
            if re.match(r"http://(gallica\.bnf\.fr|foto\.biblhertz\.it|hdl\.handle\.net|polona\.pl)/", url):
                url = "https://" + url[len("http://"):]
            c["works"].append({"title": w.get("title"), "artist": w.get("artist"), "date": w.get("date"),
                               "institution": w.get("institution"), "url": url,
                               "image": commons_image(w.get("image")) if open_ else None,
                               "rights_class": "open" if open_ else "link",
                               "rights_label": (w.get("rights") or "")[:90], "basis": w.get("attribution_basis")})
    for c in cities.values():
        c["featured"] = FEATURED.get(c["name"])
        c["xy"] = None
        c["xy_approx"] = None
        if predict and inside_hull(c["lat"], c["lon"]):
            x, y = predict(c["lat"], c["lon"])
            if 0 <= x <= W and 0 <= y <= H:
                c["xy"] = [round(x, 1), round(y, 1)]
                c["xy_approx"] = True
    # verified glyph positions win over the model
    for cid, pin in ov["portal"]["pins"].items():
        for c in cities.values():
            if c["featured"] == cid:
                c["xy"] = [pin["x"], pin["y"]]
                c["xy_approx"] = False
    rows = sorted(cities.values(), key=lambda c: c["name"])
    ids = [c["id"] for c in rows]
    assert len(ids) == len(set(ids)), "duplicate city ids"
    keys = ("image", "width", "height", "title", "credit", "object_url", "rights", "alt")
    portal = {k: ov["portal"][k] for k in keys}
    portal["image_small"] = ov["portal"].get("image_small")
    note = ("Метки городов рассчитаны по модели привязки карты"
            + (f" (полином 2-й степени по {len(g['gcps'])} опорным городам, проверка исключением "
               f"≈{g['loo_rms_px']:.0f} px)" if g else "")
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
