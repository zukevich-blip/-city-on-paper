#!/usr/bin/env python3
"""Build eras/data/eras.json for the "Atlas of eras" prototype (Issue #34).

Inputs (all committed):
  data/vision-lab/sources-eras-curator.json  - curator agent research (records, rights, cameras, pair ratings)
  data/vision-lab/georef-paris-1878.json     - approximate affine georeference of LoC 2012586603
  data/vision-lab/STORY_la_madeleine.md      - sourced story (edited)
  data/vision-lab/overrides.json             - coordinator review: corrected ratings, derived crops, portal pins

Only images present in eras/img/ are embedded; others are link-only cards.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VL = ROOT / "data" / "vision-lab"
OUT = ROOT / "eras" / "data" / "eras.json"
IMG = ROOT / "eras" / "img"

KIND_MAP = [("photochrom", "photochrom"), ("lithograph", "print"), ("etching", "print"), ("engraving", "print"),
            ("photograph", "photo"), ("albumen", "photo"), ("stereo", "photo"), ("today", "today")]
ERA_OF = {"print": "print", "photo": "photo", "photochrom": "photo", "today": "today"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kind_of(era: str) -> str:
    e = era.lower()
    for key, k in KIND_MAP:
        if key in e:
            return k
    return "photo"


def year_label(img: dict) -> str:
    e = img.get("era", "")
    if e == "today":
        return (img.get("date") or "")[:4] or "сегодня"
    m = re.search(r"(c\.|ca\.|before|pre)?\s*(\d{4})(\s*-\s*\d{4})?", e)
    if not m:
        return e
    pre = {"c.": "ок. ", "ca.": "ок. ", "before": "до ", "pre": "до "}.get((m.group(1) or "").strip(), "")
    return pre + m.group(2) + (("–" + m.group(3).split("-")[-1].strip()) if m.group(3) else "")


def rights_class(r: str) -> tuple[str, str]:
    t = (r or "").lower()
    if "no known restrictions" in t:
        return "open", "LoC: без известных ограничений"
    if "cc0" in t:
        return "open", "CC0"
    if "public_domain: true" in t or "public domain" in t:
        return "open", "общественное достояние (AIC)"
    if "etalab" in t:
        return "open", "Licence Ouverte / etalab-2.0"
    if "cc-by-sa" in t:
        return "open", "CC BY-SA 4.0"
    return "link", "права не подтверждены"


def md_to_html(md: str) -> str:
    """Tiny, escaping markdown subset: ##/### headings, paragraphs, '-' lists, **bold**, *em*, [text](https://url)."""
    def inline(s: str) -> str:
        s = html.escape(s, quote=True)
        s = re.sub(r"\[([^\]]+)\]\((https://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return s
    out, para, lst = [], [], []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()
        if lst:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in lst) + "</ul>")
            lst.clear()
    for line in md.splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("## ") or line.startswith("### "):
            flush()
            out.append(f"<h3>{inline(line.lstrip('#').strip())}</h3>")
        elif line.startswith("- "):
            if para:
                flush()
            lst.append(line[2:])
        elif not line.strip():
            flush()
        else:
            if lst:
                flush()
            para.append(line.strip())
    flush()
    return "\n".join(out)


class Georef:
    def __init__(self, g: dict, web_w: int):
        self.p = g["local_projection"]
        self.a = g["transforms"]["affine"]["inverse_local_metres_to_pixel"]
        self.k = web_w / g["pixel_space"]["width"]
        self.full = g["pixel_space"]
        self.label = (f'{g["label"]}; аффинное преобразование по {len(g["gcps"])} опорным точкам, '
                      f'RMS {g["transforms"]["affine"]["rms_m"]} м, проверка исключением '
                      f'{g["transforms"]["affine"]["loo_rms_m"]} м')

    def full_px(self, lat: float, lon: float) -> tuple[float, float]:
        p = self.p
        x = (lon - p["lon0"]) * math.pi / 180 * p["R_m"] * math.cos(math.radians(p["lat0"]))
        y = (lat - p["lat0"]) * math.pi / 180 * p["R_m"]
        a, b = x / 1000, y / 1000
        return (self.a["coef_px"][0] + self.a["coef_px"][1] * a + self.a["coef_px"][2] * b,
                self.a["coef_py"][0] + self.a["coef_py"][1] * a + self.a["coef_py"][2] * b)

    def px(self, lat, lon):
        x, y = self.full_px(lat, lon)
        return round(x * self.k, 1), round(y * self.k, 1)


def build() -> dict:
    cur = json.loads((VL / "sources-eras-curator.json").read_text("utf-8"))
    ov = json.loads((VL / "overrides.json").read_text("utf-8"))
    geo = Georef(json.loads((VL / "georef-paris-1878.json").read_text("utf-8")), 2000)
    detail = ov["paris_detail"]

    def img_rec(src: dict) -> dict:
        lf = src.get("local_file")
        name = lf.split("/")[-1] if lf else None
        file = f"img/{name}" if name and (IMG / name).exists() else None
        rc, rs = rights_class(src.get("rights_as_stated", ""))
        k = kind_of(src.get("era", ""))
        rec = {
            "id": src["id"], "era": ERA_OF[k], "kind": k, "year_label": year_label(src),
            "title": src.get("title_original") or src.get("title") or src.get("kind"),
            "creators": [{"name": c.get("name"), "role": c.get("role")} for c in src.get("creators") or []],
            "date": (src.get("date") or "")[:40], "institution": src.get("institution"),
            "object_url": src.get("viewer_url") if src.get("era") == "today" and src.get("viewer_url")
            else (src.get("object_url_new_site") or src.get("object_url")),
            "rights": src.get("rights_as_stated"), "rights_checked": src.get("rights_checked"),
            "rights_class": rc, "rights_short": rs, "file": file,
            "alt": src.get("summary_from_record") or src.get("title_original") or src.get("kind"),
        }
        if file:
            rec["sha256"] = sha(IMG / name)
            if src.get("sha256") and src["sha256"] != rec["sha256"] and "re-encoded" not in json.dumps(src):
                raise SystemExit(f"sha mismatch for {name}")
        cam = src.get("camera") or {}
        if cam.get("lat") is not None:
            rec["camera"] = {k2: cam.get(k2) for k2 in ("lat", "lon", "radius_m", "azimuth_deg", "basis", "confidence")}
        return rec

    cities = []
    for cid, cdef in ov["cities"].items():
        places = []
        for pid, pdef in cdef["places"].items():
            src = cur["cities"][cid]["places"][pid]
            imgs = [img_rec(i) for i in src["images"] if i["id"] not in pdef.get("drop", [])]
            for extra in pdef.get("derived", []):
                f = IMG / extra["file"].split("/")[-1]
                extra = {**extra, "sha256": sha(f), "rights_class": "open", "rights_short": "etalab-2.0 (производная)"}
                imgs.append(extra)
            def first_year(r: dict) -> int:
                m = re.search(r"\d{4}", r["year_label"])
                return int(m.group(0)) if m else 9999
            imgs.sort(key=lambda r: (first_year(r), r["id"]))
            pairs = [p for p in src.get("pairs", []) if not any(p["a"] == o["a"] and p["b"] == o["b"]
                                                               for o in pdef.get("pair_overrides", []))]
            ru = ov.get("reason_ru", {})
            pairs = [{"a": p["a"], "b": p["b"], "rating": p["rating"],
                      "reason": ru.get(f'{p["a"]}|{p["b"]}') or ru.get(f'{p["b"]}|{p["a"]}') or p.get("reasons", ""),
                      "by": "куратор (агент консилиума)"} for p in pairs]
            pairs += [{**p, "by": p.get("by", "координатор, проверка перспективным фрагментом")}
                      for p in pdef.get("pair_overrides", [])] + pdef.get("pairs_extra", [])
            ids = {i["id"] for i in imgs}
            pairs = [p for p in pairs if p["a"] in ids and p["b"] in ids]
            place = {"id": f"{cid}-{pid}", "title": pdef["title"], "short": pdef.get("short", pdef["title"]),
                     "summary": pdef["summary"], "images": imgs,
                     "pairs": pairs}
            if pdef.get("hunt"):
                place["hunt"] = pdef["hunt"]
            if pdef.get("story"):
                place["story"] = md_to_html((VL / pdef["story"]).read_text("utf-8"))
            if cid == "paris" and pdef.get("on_detail"):
                for im in imgs:
                    c = im.get("camera")
                    if c and c.get("lat") is not None:
                        fx, fy = geo.full_px(c["lat"], c["lon"])
                        c["px"] = round((fx - detail["x"]) / detail["w"] * detail["web_w"], 1)
                        c["py"] = round((fy - detail["y"]) / detail["w"] * detail["web_w"], 1)
                place["plan_detail"] = {k: detail[k] for k in ("image", "width", "height", "title", "credit",
                                                                "object_url", "rights", "rights_class", "rights_short",
                                                                "alt")}
            places.append(place)
        city = {"id": cid, "name": cdef["name"], "country": cdef["country"], "summary": cdef["summary"],
                "places": places}
        if cdef.get("plan"):
            plan = dict(cdef["plan"])
            if cid == "paris":
                plan["georef"] = geo.label
                for pl in places:
                    if pl["id"] in plan.get("place_points", {}):
                        lat, lon = plan["place_points"][pl["id"]]
                        x, y = geo.px(lat, lon)
                        pl["plan_xy"] = [x, y]
            city["plan"] = plan
        cities.append(city)
    return {"version": "2026-11-07", "note": ov["note"], "portal": ov["portal"], "eras": ov["eras"], "cities": cities}


if __name__ == "__main__":
    d = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", "utf-8")
    n = sum(len(p["images"]) for c in d["cities"] for p in c["places"])
    e = sum(1 for c in d["cities"] for p in c["places"] for i in p["images"] if i.get("file"))
    print(f"{len(d['cities'])} cities, {sum(len(c['places']) for c in d['cities'])} places, {n} records, {e} embedded")
