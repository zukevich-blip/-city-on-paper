#!/usr/bin/env python3
"""Collect historic city views from the Library of Congress Prints & Photographs catalogue (JSON API).

Collections: Photochrom Prints (pgz, c. 1890-1910), Popular Graphic Arts (pga, prints 1700-1900), and
Detroit Publishing (det). A work is kept only if its own item record says "No known restrictions" in
rights_information, has a digitised image, a year ≤ 1925 and the city (or a historic alias) in its title.
Title, creator, date, medium, call number and rights text are copied from the LoC record — nothing is invented.
Resumable: data/world/_loc_state.json. Polite: ≥ 1 s between calls.

Output: data/world/loc-works.json, data/world/loc-cities.json
"""
from __future__ import annotations

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
UA = "CityOnPaper/1.0 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
# Russian name -> (country, region, lat, lon, [names as they appear in LoC titles])
CITIES = {
    "Санкт-Петербург": ("Россия", "Европа", 59.9386, 30.3141,
                        ["St. Petersburg", "St. Petersbourg", "Saint Petersburg"]),
    "Москва": ("Россия", "Европа", 55.7558, 37.6173, ["Moscow", "Moscou"]),
    "Стамбул": ("Турция", "Азия", 41.0082, 28.9784, ["Constantinople", "Istanbul", "Stamboul"]),
    "Каир": ("Египет", "Африка", 30.0444, 31.2357, ["Cairo"]),
    "Иерусалим": ("Палестина / Израиль", "Азия", 31.7767, 35.2345, ["Jerusalem"]),
    "Алжир": ("Алжир", "Африка", 36.7538, 3.0588, ["Algiers", "Alger"]),
    "Тунис": ("Тунис", "Африка", 36.8065, 10.1815, ["Tunis"]),
    "Дамаск": ("Сирия", "Азия", 33.5138, 36.2765, ["Damascus"]),
    "Бейрут": ("Ливан", "Азия", 33.8938, 35.5018, ["Beirut", "Beyrouth"]),
    "Вена": ("Австрия", "Европа", 48.2082, 16.3738, ["Vienna", "Wien"]),
    "Будапешт": ("Венгрия", "Европа", 47.4979, 19.0402, ["Budapest"]),
    "Прага": ("Чехия", "Европа", 50.0755, 14.4378, ["Prague", "Prag"]),
    "Берлин": ("Германия", "Европа", 52.52, 13.405, ["Berlin"]),
    "Дрезден": ("Германия", "Европа", 51.0504, 13.7373, ["Dresden"]),
    "Мюнхен": ("Германия", "Европа", 48.1351, 11.582, ["Munich", "München"]),
    "Гамбург": ("Германия", "Европа", 53.5511, 9.9937, ["Hamburg"]),
    "Кёльн": ("Германия", "Европа", 50.9375, 6.9603, ["Cologne"]),
    "Копенгаген": ("Дания", "Европа", 55.6761, 12.5683, ["Copenhagen"]),
    "Стокгольм": ("Швеция", "Европа", 59.3293, 18.0686, ["Stockholm"]),
    "Осло": ("Норвегия", "Европа", 59.9139, 10.7522, ["Christiania", "Oslo"]),
    "Берген": ("Норвегия", "Европа", 60.3913, 5.3221, ["Bergen"]),
    "Эдинбург": ("Великобритания", "Европа", 55.9533, -3.1883, ["Edinburgh"]),
    "Дублин": ("Ирландия", "Европа", 53.3498, -6.2603, ["Dublin"]),
    "Брюссель": ("Бельгия", "Европа", 50.8503, 4.3517, ["Brussels", "Bruxelles"]),
    "Брюгге": ("Бельгия", "Европа", 51.2093, 3.2247, ["Bruges"]),
    "Антверпен": ("Бельгия", "Европа", 51.2194, 4.4025, ["Antwerp", "Anvers"]),
    "Амстердам": ("Нидерланды", "Европа", 52.3676, 4.9041, ["Amsterdam"]),
    "Лиссабон": ("Португалия", "Европа", 38.7223, -9.1393, ["Lisbon", "Lisboa"]),
    "Мадрид": ("Испания", "Европа", 40.4168, -3.7038, ["Madrid"]),
    "Севилья": ("Испания", "Европа", 37.3891, -5.9845, ["Seville", "Sevilla"]),
    "Гранада": ("Испания", "Европа", 37.1773, -3.5986, ["Granada"]),
    "Барселона": ("Испания", "Европа", 41.3874, 2.1686, ["Barcelona"]),
    "Генуя": ("Италия", "Европа", 44.4056, 8.9463, ["Genoa"]),
    "Милан": ("Италия", "Европа", 45.4642, 9.19, ["Milan"]),
    "Палермо": ("Италия", "Европа", 38.1157, 13.3615, ["Palermo"]),
    "Марсель": ("Франция", "Европа", 43.2965, 5.3698, ["Marseille", "Marseilles"]),
    "Ницца": ("Франция", "Европа", 43.7102, 7.262, ["Nice"]),
    "Афины": ("Греция", "Европа", 37.9838, 23.7275, ["Athens"]),
    "Варшава": ("Польша", "Европа", 52.2297, 21.0122, ["Warsaw", "Varsovie"]),
    "Киев": ("Украина", "Европа", 50.4501, 30.5234, ["Kiev", "Kiew"]),
    "Одесса": ("Украина", "Европа", 46.4825, 30.7233, ["Odessa"]),
    "Тбилиси": ("Грузия", "Азия", 41.7151, 44.8271, ["Tiflis"]),
    "Нью-Йорк": ("США", "Северная Америка", 40.7128, -74.006, ["New York"]),
    "Бостон": ("США", "Северная Америка", 42.3601, -71.0589, ["Boston"]),
    "Филадельфия": ("США", "Северная Америка", 39.9526, -75.1652, ["Philadelphia"]),
    "Вашингтон": ("США", "Северная Америка", 38.9072, -77.0369, ["Washington, D.C.", "Washington City"]),
    "Чикаго": ("США", "Северная Америка", 41.8781, -87.6298, ["Chicago"]),
    "Сан-Франциско": ("США", "Северная Америка", 37.7749, -122.4194, ["San Francisco"]),
    "Новый Орлеан": ("США", "Северная Америка", 29.9511, -90.0715, ["New Orleans"]),
    "Квебек": ("Канада", "Северная Америка", 46.8139, -71.208, ["Quebec"]),
    "Монреаль": ("Канада", "Северная Америка", 45.5017, -73.5673, ["Montreal"]),
    "Гавана": ("Куба", "Латинская Америка", 23.1136, -82.3666, ["Havana", "Habana"]),
    "Мехико": ("Мексика", "Латинская Америка", 19.4326, -99.1332, ["City of Mexico", "Mexico City"]),
    "Рио-де-Жанейро": ("Бразилия", "Латинская Америка", -22.9068, -43.1729, ["Rio de Janeiro"]),
    "Дели": ("Индия", "Азия", 28.6139, 77.209, ["Delhi"]),
    "Калькутта": ("Индия", "Азия", 22.5726, 88.3639, ["Calcutta"]),
    "Мумбаи": ("Индия", "Азия", 19.076, 72.8777, ["Bombay"]),
    "Токио": ("Япония", "Азия", 35.6762, 139.6503, ["Tokyo", "Tokio", "Yedo", "Edo"]),
    "Киото": ("Япония", "Азия", 35.0116, 135.7681, ["Kyoto", "Kioto"]),
    "Пекин": ("Китай", "Азия", 39.9042, 116.4074, ["Peking", "Pekin"]),
    "Шанхай": ("Китай", "Азия", 31.2304, 121.4737, ["Shanghai"]),
    "Гонконг": ("Китай", "Азия", 22.3193, 114.1694, ["Hong Kong", "Hongkong"]),
    "Сидней": ("Австралия", "Океания", -33.8688, 151.2093, ["Sydney"]),
}
COLLS = [("pgz", "photochrom"), ("pga", "print"), ("det", "photograph")]


class Blocked(RuntimeError):
    pass


def get(url: str) -> dict:
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=45) as r:
                time.sleep(1.0)
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(40 * (attempt + 1))
                continue
            if e.code == 404:
                return {}
            time.sleep(5)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(5)
    raise Blocked(url[:100])


def year_of(text: str) -> int | None:
    m = re.search(r"(?<!\d)(1[5-9]\d\d)(?!\d)", text or "")
    return int(m.group(1)) if m else None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    state_f = OUT / "_loc_state.json"
    state = json.loads(state_f.read_text("utf-8")) if state_f.exists() else {}
    only = set(sys.argv[1:])
    try:
        for ru, (country, region, lat, lon, names) in CITIES.items():
            if ru in state or (only and ru not in only):
                continue
            rows, seen = [], set()
            for coll, kind in COLLS:
                got = 0
                for name in names[:2]:
                    q = urllib.parse.urlencode({"q": name, "co": coll, "fo": "json", "c": 40})
                    d = get("https://www.loc.gov/pictures/search/?" + q)
                    for r in d.get("results", []):
                        title, pk = r.get("title") or "", r.get("pk")
                        if not pk or pk in seen or not (r.get("image") or {}).get("full"):
                            continue
                        if not any(n.lower() in title.lower() for n in names):
                            continue
                        if re.search(r"\b(map|plan of|portrait|cartoon|caricature|sheet music)\b", title, re.I):
                            continue
                        y = year_of(r.get("created_published_date") or "")
                        if not y or y > 1925:
                            continue
                        seen.add(pk)
                        item = get(f"https://www.loc.gov/pictures/item/{pk}/?fo=json").get("item") or {}
                        rights = (item.get("rights_information") or "").strip()
                        if "no known restrictions" not in rights.lower():
                            continue
                        full = r["image"]["full"]
                        rows.append({
                            "city": ru, "country": country, "region": region, "pk": pk, "kind": kind,
                            "title": title.strip(" []")[:180], "year": y,
                            "date_text": (r.get("created_published_date") or "").strip(" []."),
                            "artist": (r.get("creator") or "").strip()[:120],
                            "medium": (r.get("medium") or item.get("medium") or "")[:140],
                            "call_number": (item.get("call_number") or "")[:80],
                            "page": f"https://www.loc.gov/pictures/item/{pk}/",
                            "image": ("https:" + full) if full.startswith("//") else full,
                            "rights": rights, "collection": coll,
                        })
                        got += 1
                        if got >= 10:
                            break
                    if got >= 10:
                        break
            state[ru] = {"country": country, "region": region, "lat": lat, "lon": lon, "works": rows}
            state_f.write_text(json.dumps(state, ensure_ascii=False), "utf-8")
            print(f"{ru}: {len(rows)}", flush=True)
    except Blocked as e:
        print("blocked, stopping; resume later:", e, flush=True)
    items = [w for c in state.values() for w in c["works"]]
    doc = {"generated": time.strftime("%Y-%m-%d"), "source": "Library of Congress, Prints & Photographs (JSON API)",
           "items": items}
    (OUT / "loc-works.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", "utf-8")
    cities = [{"city": k, **{f: v[f] for f in ("country", "region", "lat", "lon")}, "works": len(v["works"])}
              for k, v in sorted(state.items())]
    (OUT / "loc-cities.json").write_text(json.dumps({"cities": cities}, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"{len(items)} works, {sum(1 for c in cities if c['works'])} cities with works of {len(cities)}")


if __name__ == "__main__":
    main()
