#!/usr/bin/env python3
"""Merge the world collectors' output into the museum's curation format.

Inputs (optional): data/world/loc-works.json (Library of Congress), data/world/works.json (Commons),
and data/world/museum-works.json (selected museum records).
Output: data/curation/world-open-views-v2.json and data/world/registry.json (cities with coordinates).
Every field of a card is copied from the holder's record. Status of the cards: open rights confirmed in the record,
subject selected by a title/category match — a machine-selected candidate, not curator approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "data" / "world"
OUT = ROOT / "data" / "curation" / "world-open-views-v2.json"
KIND_RU = {"lithograph": "Литография", "engraving": "Гравюра", "etching": "Офорт", "aquatint": "Акватинта",
           "woodcut": "Ксилография", "print": "Эстамп", "photochrom": "Фотохром", "painting": "Живопись",
           "drawing": "Рисунок", "artwork": "Произведение искусства", "view": "Вид города",
           "historic image": "Историческое изображение", "photograph": "Фотография"}
RIGHTS_LOC = "Библиотека Конгресса: ограничений на публикацию не известно"
NOTE = "rights, date and author read from the holder's record; subject matched by title/category, not curator-reviewed"


def load(name: str) -> dict:
    p = W / name
    return json.loads(p.read_text("utf-8")) if p.exists() else {}


def main() -> None:
    items, seen, cities = [], set(), {}
    for c in load("loc-cities.json").get("cities", []) + load("cities.json").get("cities", []):
        if c.get("lat") is not None:
            cities.setdefault(c["city"], {k: c.get(k) for k in ("city", "country", "region", "lat", "lon")})
    for w in load("loc-works.json").get("items", []):
        key = "loc:" + str(w["pk"])
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "id": "loc-" + str(w["pk"]), "city": w["city"], "country": w.get("country"), "region": w.get("region"),
            "name": w["title"], "title_original": w["title"], "maker": w.get("artist") or "Автор не указан в записи",
            "date": str(w["year"]), "date_note": w.get("date_text") or "",
            "medium": KIND_RU.get(w["kind"], w["kind"]) + (f" · {w['medium']}" if w.get("medium") else ""),
            "source": "Library of Congress, Prints & Photographs Division",
            "source_id": w.get("call_number") or str(w["pk"]),
            "url": w["page"], "image": w["image"], "rights": "loc_no_known_restrictions",
            "rights_label": RIGHTS_LOC if "no known restrictions" in w["rights"].lower() else "LoC: " + w["rights"],
            "verified": NOTE})
    for w in load("works.json").get("items", []):
        if w["file"] in seen or not (w.get("page") or "").startswith("https://"):
            continue
        seen.add(w["file"])
        lic = (w.get("license") or "").lower()
        rights = ("cc0" if lic.startswith("cc0") else "public_domain_commons" if lic.startswith(("public", "pd"))
                  else "cc_by_sa" if "sa" in lic else "cc_by")
        c = cities.get(w["city"], {})
        items.append({
            "id": "wc2-" + hashlib.sha1(w["file"].encode("utf-8")).hexdigest()[:12],
            "city": w["city"], "country": c.get("country"), "region": c.get("region"),
            "name": w["title"], "title_original": w["title"], "maker": w.get("artist") or "Автор не указан в записи",
            "date": str(w["year"]), "date_note": w.get("date_text") or "", "medium": KIND_RU.get(w["kind"], w["kind"]),
            "source": "Wikimedia Commons" + (f" · {w['credit']}" if w.get("credit") else ""),
            "source_id": w["file"], "url": w["page"], "image": w["image"], "rights": rights,
            "rights_label": w.get("license"), "license_url": w.get("license_url"), "verified": NOTE})
    known_urls = {item["url"] for item in items}
    for item in load("museum-works.json").get("items", []):
        if item["url"] not in known_urls:
            items.append(item)
            known_urls.add(item["url"])
    items.sort(key=lambda x: (x["city"], x["date"], x["id"]))
    out = {"version": "2026-11-16",
           "source": "Library of Congress P&P JSON API; Wikimedia Commons API; selected museum records",
           "editorial_policy": "Historic city views (≤ 1925) with open rights stated in the holder's record. "
                               "Machine-selected candidates: " + NOTE + ".", "items": items}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", "utf-8")
    reg = {"cities": sorted(cities.values(), key=lambda c: c["city"])}
    (W / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(len(items), "cards for", len({i["city"] for i in items}), "cities;", len(cities), "cities with coordinates")


if __name__ == "__main__":
    main()
