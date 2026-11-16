#!/usr/bin/env python3
"""Collect openly licensed historic city views (≤ 1925) from Wikimedia Commons categories for the world registry.

For each city (Russian name -> English name taken from the seed query) it resolves the Wikidata item through the
English Wikipedia title (coordinates P625, Commons category P373), then reads files from well-named Commons
categories ("Engravings of X", "Lithographs of X", "X in the 19th century", …) and keeps a file only if:
licence is PD / CC0 / CC BY / CC BY-SA; year ≤ 1925; width ≥ 500 px; it is not a map/plan/portrait/text page.
Nothing is invented: title, author, date, licence and credit come from the Commons record of the file.
Resumable (state in data/world/_state.json); polite (≥ 1 s between calls, back-off on 429).

Output: data/world/works.json, data/world/cities.json
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "world"
UA = "CityOnPaperResearch/0.8 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
FREE = re.compile(r"^(cc0|public domain|pd\b|pd-|cc by(-sa)? [1-4]\.0|cc by(-sa)? 2\.[05])", re.I)
BAD = re.compile(r"\b(map|maps|plan of|plano|karte|carte|portrait|coat of arms|wappen|logo|seal|flag|coin|medal|"
                 r"title page|titelblatt|text page|signature|stamp|banknote|diagram|chart)\b", re.I)
KINDS = [("Lithographs of {}", "lithograph"), ("Engravings of {}", "engraving"), ("Etchings of {}", "etching"),
         ("Aquatints of {}", "aquatint"), ("Woodcuts of {}", "woodcut"), ("Prints of {}", "print"),
         ("Ukiyo-e of {}", "woodcut"), ("Photochrom pictures of {}", "photochrom"),
         ("Paintings of {}", "painting"), ("Watercolor paintings of {}", "painting"), ("Drawings of {}", "drawing"),
         ("{} in art", "artwork"), ("Views of {}", "view"), ("Historical images of {}", "historic image"),
         ("{} in the 18th century", "historic image"), ("{} in the 19th century", "historic image"),
         ("{} in the 1850s", "historic image"), ("{} in the 1860s", "historic image"),
         ("{} in the 1870s", "historic image"), ("{} in the 1880s", "historic image"),
         ("{} in the 1890s", "historic image"), ("Old photographs of {}", "photograph")]
EN_FIX = {"Санкт-Петербург": "Saint Petersburg", "Стамбул": "Istanbul", "Мумбаи": "Mumbai", "Калькутта": "Kolkata",
          "Пекин": "Beijing", "Киев": "Kyiv", "Нью-Йорк": "New York City", "Мехико": "Mexico City",
          "Вашингтон": "Washington, D.C.", "Квебек": "Quebec City", "Гуанчжоу": "Guangzhou", "Варанаси": "Varanasi",
          "Кёльн": "Cologne", "Гаага": "The Hague", "Сан-Паулу": "São Paulo", "Салвадор": "Salvador, Bahia",
          "Сантьяго": "Santiago", "Картахена": "Cartagena, Colombia", "Веракрус": "Veracruz (city)",
          "Александрия": "Alexandria", "Луксор": "Luxor", "Иерусалим": "Jerusalem", "Дамаск": "Damascus"}
ALT = {"Istanbul": ["Constantinople"], "Tokyo": ["Edo"], "Mumbai": ["Bombay"], "Kolkata": ["Calcutta"],
       "Beijing": ["Peking"], "Kyiv": ["Kiev"], "New York City": ["New York City", "Manhattan"],
       "Saint Petersburg": ["Saint Petersburg", "St. Petersburg"], "Guangzhou": ["Canton"], "Varanasi": ["Benares"],
       "Chennai": ["Madras"], "Ho Chi Minh City": ["Saigon"], "Jakarta": ["Batavia"], "Izmir": ["Smyrna"],
       "Washington, D.C.": ["Washington, D.C."], "Quebec City": ["Quebec City", "Quebec (city)"],
       "Mexico City": ["Mexico City"], "Salvador, Bahia": ["Salvador, Bahia"],
       "Cartagena, Colombia": ["Cartagena, Colombia"],
       "Veracruz (city)": ["Veracruz (city)", "Veracruz"]}


def api(base: str, **params) -> dict:
    url = base + "?" + urllib.parse.urlencode({"format": "json", **params})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=45) as r:
                time.sleep(0.6)
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                wait = e.headers.get("Retry-After") or ""
                time.sleep(min(120, (int(wait) if wait.isdigit() else 30) + 3 + 5 * attempt))
                continue
            return {}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(5)
    return {}


def strip(s) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def year_of(*texts) -> int | None:
    for t in texts:
        for m in re.finditer(r"(?<!\d)(1[4-9]\d\d)(?!\d)", t or ""):
            return int(m.group(1))
    return None


def english(seed: dict) -> str:
    if seed["name"] in EN_FIX:
        return EN_FIX[seed["name"]]
    q = seed.get("query") or ""
    q = re.sub(r"\b(19th century|18th century|historic|city|town|lithograph|engraving|print|view|old|harbou?r|port)\b",
               " ", q, flags=re.I)
    return re.sub(r"\s+", " ", q).strip()


def wikidata(en: str) -> dict:
    d = api("https://www.wikidata.org/w/api.php", action="wbgetentities", sites="enwiki", titles=en,
            props="claims|labels|sitelinks", languages="ru|en", normalize=1)
    for q, e in (d.get("entities") or {}).items():
        if not q.startswith("Q"):
            continue
        c = e.get("claims", {})
        def val(p, c=c):
            return (c.get(p) or [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value")

        coord = val("P625") or {}
        return {"qid": q, "lat": coord.get("latitude"), "lon": coord.get("longitude"), "commons": val("P373"),
                "label_ru": e.get("labels", {}).get("ru", {}).get("value")}
    return {}


def files_in(cat: str) -> list[str]:
    d = api("https://commons.wikimedia.org/w/api.php", action="query", list="categorymembers",
            cmtitle="Category:" + cat, cmtype="file", cmlimit=120)
    return [m["title"] for m in d.get("query", {}).get("categorymembers", [])
            if re.search(r"\.(jpe?g|png|tiff?)$", m["title"], re.I)]


def nonempty(cats: list[str]) -> list[str]:
    """One call: which of these categories exist and contain files."""
    d = api("https://commons.wikimedia.org/w/api.php", action="query", prop="categoryinfo",
            titles="|".join("Category:" + c for c in cats[:50]))
    have = {p["title"][9:] for p in d.get("query", {}).get("pages", {}).values()
            if (p.get("categoryinfo") or {}).get("files", 0) > 0}
    norm = {n["to"][9:]: n["from"][9:] for n in d.get("query", {}).get("normalized", [])}
    have |= {norm[h] for h in list(have) if h in norm}
    return [c for c in cats if c in have]


def info(titles: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(titles), 40):
        d = api("https://commons.wikimedia.org/w/api.php", action="query", prop="imageinfo",
                iiprop="url|extmetadata|size", iiurlwidth=500, titles="|".join(titles[i:i + 40]))
        for p in d.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [None])[0]
            if ii:
                out.append({"title": p["title"], **ii})
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    seeds = json.loads((ROOT / "data" / "curation" / "world-cities-v1.json").read_text("utf-8"))["cities"]
    extra = [{"name": "Санкт-Петербург", "region": "Европа", "country": "Россия", "query": ""}]
    names = {s["name"] for s in seeds}
    seeds += [e for e in extra if e["name"] not in names]
    first = ["Санкт-Петербург", "Стамбул", "Нью-Йорк", "Каир", "Иерусалим", "Токио", "Киото", "Пекин", "Дели", "Калькутта",
             "Мумбаи", "Вена", "Мадрид", "Лиссабон", "Эдинбург", "Дрезден", "Гавана", "Мехико", "Рио-де-Жанейро",
             "Сидней", "Кейптаун", "Самарканд", "Дамаск", "Гонконг", "Шанхай", "Бостон", "Сан-Франциско", "Квебек"]
    seeds.sort(key=lambda s: first.index(s["name"]) if s["name"] in first else 99)
    only = set(sys.argv[1:])
    state_f = OUT / "_state.json"
    state = json.loads(state_f.read_text("utf-8")) if state_f.exists() else {"cities": {}, "works": {}}
    for s in seeds:
        ru = s["name"]
        if ru in state["cities"] or (only and ru not in only):
            continue
        en = english(s)
        wd = wikidata(en) if en else {}
        variants = list(dict.fromkeys(ALT.get(en, []) + [wd.get("commons") or en, en]))
        seen, picked = set(), []
        per_cat: list[list[dict]] = []
        for v in variants[:3]:
            kind_of = {pattern.format(v): kind for pattern, kind in KINDS}
            for cat in nonempty(list(kind_of)):
                kind = kind_of[cat]
                titles = [t for t in files_in(cat) if t not in seen and not BAD.search(t)]
                if not titles:
                    continue
                seen.update(titles)
                rows = []
                for ii in info(titles[:40]):
                    em = ii.get("extmetadata", {})
                    lic = strip(em.get("LicenseShortName", {}).get("value"))
                    desc = strip(em.get("ImageDescription", {}).get("value"))
                    name = strip(em.get("ObjectName", {}).get("value")) or re.sub(r"^File:|\.\w+$", "", ii["title"])
                    y = year_of(strip(em.get("DateTimeOriginal", {}).get("value")), name, desc)
                    cats = strip(em.get("Categories", {}).get("value"))
                    if not FREE.match(lic) or not y or y > 1925 or ii.get("width", 0) < 500:
                        continue
                    if BAD.search(name) or BAD.search(desc[:200]):
                        continue
                    if re.search(r"\b(maps|plans|portraits) of\b", cats, re.I):
                        continue
                    rows.append({"city": ru, "city_en": en, "file": ii["title"][5:], "page": ii.get("descriptionurl"),
                                 "image": ii.get("thumburl") or ii.get("url"), "width": ii.get("width"),
                                 "height": ii.get("height"), "year": y,
                                 "date_text": strip(em.get("DateTimeOriginal", {}).get("value"))[:60],
                                 "kind": kind, "title": name[:160],
                                 "artist": strip(em.get("Artist", {}).get("value"))[:120],
                                 "license": lic, "license_url": strip(em.get("LicenseUrl", {}).get("value")),
                                 "credit": strip(em.get("Credit", {}).get("value"))[:160], "category": cat})
                if rows:
                    per_cat.append(rows)
            if sum(len(r) for r in per_cat) >= 60:
                break
        while per_cat and len(picked) < 24:  # round-robin across categories for variety
            for rows in list(per_cat):
                if rows and len(picked) < 24:
                    picked.append(rows.pop(0))
                if not rows:
                    per_cat.remove(rows)
        state["cities"][ru] = {"city": ru, "city_en": en, "region": s.get("region"), "country": s.get("country"),
                               "qid": wd.get("qid"), "lat": wd.get("lat"), "lon": wd.get("lon"), "works": len(picked)}
        state["works"][ru] = picked
        state_f.write_text(json.dumps(state, ensure_ascii=False), "utf-8")
        print(f"{ru} ({en}): {len(picked)}", flush=True)
    items = [w for rows in state["works"].values() for w in rows]
    doc = {"generated": time.strftime("%Y-%m-%d"), "source": "Wikimedia Commons API", "items": items}
    (OUT / "works.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", "utf-8")
    (OUT / "cities.json").write_text(json.dumps({"cities": sorted(state["cities"].values(), key=lambda c: c["city"])},
                                                ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"{len(items)} works, {sum(1 for c in state['cities'].values() if c['works'])} cities with works "
          f"of {len(state['cities'])}")


if __name__ == "__main__":
    main()
