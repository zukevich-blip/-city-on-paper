#!/usr/bin/env python3
"""Build eras/data/atlas.json: every European city of the museum + every Benoist place (Issue #34, v2).

Inputs (committed):
  data/vision-lab/europe-cities.json   - museum city list with coordinates (OSM Nominatim, 4 fixed by hand)
  data/vision-lab/benoist-places.json  - Benoist gazetteer: places, works, rights (optional)
  data/vision-lab/portal-georef.json   - lon/lat -> pixel model for the 1769 portal map (optional)
  data/vision-lab/overrides.json       - portal image, featured cities
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
import urllib.parse
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


def wid(url: str) -> str:
    return hashlib.sha1((url or "").encode("utf-8")).hexdigest()[:10]


class PlanGeoref:
    """lat/lon -> full-resolution plan pixels (affine or 2nd-order polynomial in local metres)."""

    def __init__(self, g: dict):
        self.p = g["local_projection"]
        t = g["transforms"]
        self.kind = g.get("chosen") or g.get("recommended_transform") or ("affine" if "affine" in t else next(iter(t)))
        self.kind = self.kind if self.kind in t else "affine"
        self.t = t[self.kind]
        self.full_w = g["pixel_space"]["width"]

    def full_px(self, lat: float, lon: float) -> tuple[float, float]:
        p = self.p
        x = (lon - p["lon0"]) * math.pi / 180 * p["R_m"] * math.cos(math.radians(p["lat0"]))
        y = (lat - p["lat0"]) * math.pi / 180 * p["R_m"]
        a, b = x / 1000, y / 1000
        inv = self.t["inverse_local_metres_to_pixel"]
        terms = [1, a, b] if len(inv["coef_px"]) == 3 else [1, a, b, a * a, a * b, b * b]
        px = sum(c * v for c, v in zip(inv["coef_px"], terms, strict=True))
        py = sum(c * v for c, v in zip(inv["coef_py"], terms, strict=True))
        return px, py


def attach_sites_and_plans(rows: list[dict]) -> None:
    """Optional inputs: data/vision-lab/sites.json (where each work was drawn) and plans.json (+ georef-<id>.json)."""
    sites = load("sites.json") or {"items": []}
    plans = (load("plans.json") or {}).get("plans", [])
    by_name = {c["name"]: c for c in rows}
    by_id = {c["id"]: c for c in rows}
    wdate = {w["url"]: w.get("date") for c in rows for w in c["works"]}
    for it in sites.get("items", []):
        c = by_name.get(it.get("city"))
        if not c or it.get("lat") is None or it.get("kind") == "unresolved" or it.get("confidence") == "low":
            continue
        img = it.get("image") or ""
        c.setdefault("sites", []).append({
            "wid": wid(it["work_url"]), "url": it["work_url"], "title": (it.get("title") or "")[:140],
            "image": commons_image(it.get("image")) or (img if img.startswith("https://") else None),
            "site_name": it.get("site_name"), "site_ru": it.get("site_name_ru") or it.get("site_name"),
            "qid": it.get("qid"), "lat": round(it["lat"], 6), "lon": round(it["lon"], 6),
            "kind": it.get("kind"), "confidence": it.get("confidence"),
            "date": it.get("date") or wdate.get(it["work_url"])})
    today = load("today-photos.json") or {}
    for c in rows:
        groups: dict[str, dict] = {}
        for x in c.get("sites", []):
            key = x.get("qid") or f'{x["lat"]:.4f},{x["lon"]:.4f}'
            g = groups.setdefault(key, {"key": key, "qid": x.get("qid"), "name": x["site_ru"], "lat": x["lat"],
                                        "lon": x["lon"], "kind": x.get("kind"), "works": []})
            g["works"].append(x["wid"])
        out = []
        for g in groups.values():
            t = today.get(g["qid"] or "")
            if t:
                keep = ("file", "image", "page", "license", "license_url", "author", "date")
                g["today"] = {k: t.get(k) for k in keep}
            if len(g["works"]) >= 2 or t:
                out.append(g)
        if out:
            c["epochs"] = sorted(out, key=lambda g: (-len(g["works"]), g["name"] or ""))
    for pl in plans:
        c = by_id.get(pl.get("city_id")) or by_name.get(pl.get("city_ru"))
        tj = ROOT / "eras" / "tiles" / f"plan-{pl['city_id']}" / "tiles.json"
        gf = VL / pl["georef_file"] if pl.get("georef_file") else None
        if not c or not tj.exists() or (gf is not None and not gf.exists()):
            continue
        t = json.loads(tj.read_text("utf-8"))
        geo = PlanGeoref(json.loads(gf.read_text("utf-8"))) if gf else None
        who = ", ".join(pl.get("creators") or [])
        note = (f"Привязка плана приблизительная: проверка исключением ≈{round(pl['loo_rms_m'])} м." if geo
                else pl.get("georef_note", "План без привязки: метки мест показаны на современной карте."))
        c["plan"] = {"tiles": f"tiles/plan-{pl['city_id']}", **t, "title": pl["title"], "year": pl.get("year"),
                     "credit": f"{who}{'; ' if who else ''}{pl.get('date', '')}; {pl['institution']}",
                     "object_url": pl["object_url"], "rights": pl["rights"], "georef_note": note}
        if not geo:
            continue
        k = t["width"] / geo.full_w
        for s in c.get("sites", []):
            x, y = geo.full_px(s["lat"], s["lon"])
            if 0 <= x <= geo.full_w and 0 <= y <= t["height"] / k:
                s["px"] = [round(x * k, 1), round(y * k, 1)]


def attach_halls(rows: list[dict]) -> None:
    """Links from a city page to the other halls of the museum that hold material about the same city."""
    cur = ROOT / "data" / "curation"
    journeys = {i["city"] for i in json.loads((cur / "era-journeys-20261102.json").read_text("utf-8"))["items"]}
    world = {c["name"] for c in json.loads((cur / "world-cities-v1.json").read_text("utf-8"))["cities"]}
    fixed = {"Париж": [["../detective/", "Дело № 01: Мадлен под лупой"], ["../poc/compare/", "Тогда / сейчас: Мадлен"],
                       ["../exhibitions/city-as-evidence/", "Выставка «Город как свидетельство»"]],
             "Флоренция": [["../exhibitions/lost-florence/", "Выставка «Исчезнувшая Флоренция»"]]}
    for c in rows:
        h = [["../salon/?city=" + urllib.parse.quote(c["name"]), "Салон открытий: листы этого города"]]
        if c["name"] in journeys:
            h.append(["../journeys/", "Атлас времени: город по векам"])
        if c["name"] in world:
            h.append(["../world/", "Города мира"])
        h += fixed.get(c["name"], [])
        c["halls"] = h


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
                               "institution": w.get("institution"), "url": url, "wid": wid(url),
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
    tj = ROOT / "eras" / "tiles" / "europe-1769" / "tiles.json"
    if tj.exists():
        portal["tiles"] = {"tiles": "tiles/europe-1769", **json.loads(tj.read_text("utf-8"))}
    attach_sites_and_plans(rows)
    attach_halls(rows)
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
