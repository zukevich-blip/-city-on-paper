#!/usr/bin/env python3
"""Locate the building each shipped Benoist sheet shows, using OpenStreetMap Nominatim (approximate, evidence kept).

The LANDMARKS table is a human choice (which sheet shows which building); coordinates come from Nominatim, one polite
request per landmark. Output: data/curation/benoist-sheet-places-v1.json. A landmark that cannot be geocoded is recorded
without coordinates and the book then says "место не привязано".
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "curation" / "benoist-sheet-places-v1.json"
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
# id, Russian name, query for Nominatim, city, sheet ids shown there
LANDMARKS = [
    (
        "sainte-chapelle",
        "Сент-Шапель",
        "Sainte-Chapelle",
        "Париж",
        ["parismusees-320290066", "parismusees-320290060"],
    ),
    ("luxembourg", "Люксембургский дворец", "Palais du Luxembourg, Paris", "Париж", ["parismusees-320291197"]),
    (
        "chateau-eau",
        "Площадь Республики (Шато-д'О)",
        "Place de la République",
        "Париж",
        ["parismusees-320294285"],
    ),
    (
        "notre-dame",
        "Нотр-Дам",
        "Cathédrale Notre-Dame de Paris",
        "Париж",
        ["parismusees-320291945", "rijks-RP-P-1905-5500"],
    ),
    ("palais-royal", "Пале-Рояль", "Palais-Royal, Paris", "Париж", ["parismusees-320290399", "rijks-RP-P-1905-5499"]),
    ("vendome", "Вандомская колонна", "Place Vendôme", "Париж", ["parismusees-320292157"]),
    (
        "louvre-rivoli",
        "Лувр и улица Риволи",
        "Palais du Louvre, Paris",
        "Париж",
        ["parismusees-320288755", "parismusees-320291211"],
    ),
    ("saint-sulpice", "Сен-Сюльпис", "Saint-Sulpice, Paris", "Париж", ["parismusees-320050912"]),
    (
        "saint-etienne",
        "Сен-Этьен-дю-Мон и Сен-Сюльпис",
        "Église Saint-Étienne-du-Mont, Paris",
        "Париж",
        ["parismusees-320290954", "rijks-RP-P-1905-5502"],
    ),
    ("bourse", "Дворец Броньяра (Биржа)", "Palais de la Bourse, Paris", "Париж", ["parismusees-320291262"]),
    (
        "louvre-colonnade",
        "Колоннада Лувра",
        "Rue de l'Amiral de Coligny, Paris",
        "Париж",
        ["parismusees-320291352", "rijks-RP-P-1905-5505"],
    ),
    ("halles-innocents", "Фонтан Невинных", "Fontaine des Innocents, Paris", "Париж", ["parismusees-200009791"]),
    (
        "carrousel",
        "Площадь Карусель",
        "Arc de Triomphe du Carrousel, Paris",
        "Париж",
        ["parismusees-320175609", "parismusees-320175628"],
    ),
    (
        "bastille",
        "Июльская колонна",
        "Colonne de Juillet, Place de la Bastille, Paris",
        "Париж",
        ["parismusees-320262846", "rijks-RP-P-1905-5496"],
    ),
    ("square-temple", "Сквер дю Тампль", "Square du Temple, Paris", "Париж", ["parismusees-320074413"]),
    (
        "palais-industrie",
        "Дворец промышленности (на месте Гран-Пале)",
        "Grand Palais",
        "Париж",
        ["parismusees-320150835", "parismusees-320298071"],
    ),
    ("pont-royal", "Королевский мост", "Pont Royal, Paris", "Париж", ["parismusees-320299869"]),
    (
        "madeleine",
        "Церковь Мадлен",
        "Église de la Madeleine, Paris",
        "Париж",
        ["parismusees-320295651", "parismusees-320295653", "parismusees-320295656", "rijks-RP-P-1905-5495"],
    ),
    (
        "tuileries",
        "Тюильри (утраченный дворец)",
        "Arc de Triomphe du Carrousel, Paris",
        "Париж",
        ["parismusees-320290166", "rijks-RP-P-1905-5501"],
    ),
    ("hotel-de-ville", "Ратуша", "Hôtel de Ville, Paris", "Париж", ["parismusees-320290537", "rijks-RP-P-1905-5498"]),
    ("concorde", "Площадь Согласия", "Place de la Concorde, Paris", "Париж", ["rijks-RP-P-1905-5494"]),
    ("porte-saint-denis", "Ворота Сен-Дени", "Porte Saint-Denis, Paris", "Париж", ["rijks-RP-P-1905-5503"]),
    ("orsay", "Дворец Орсе и Почётного легиона", "Musée d'Orsay", "Париж", ["rijks-RP-P-1905-5504"]),
    ("pantheon", "Пантеон", "Panthéon, Paris", "Париж", ["rijks-RP-P-1905-5506"]),
    (
        "expo-1867",
        "Парижская выставка 1867 года (Марсово поле)",
        "Champ de Mars, Paris",
        "Париж",
        ["parismusees-320298080", "parismusees-320298085"],
    ),
    (
        "freiburg",
        "Фрайбургский собор",
        "Freiburger Münster, Freiburg im Breisgau",
        "Фрайбург",
        ["os-labw-freiburg-1", "os-labw-freiburg-2"],
    ),
    ("cadix", "Кадис", "Cádiz", "Кадис", ["os-icgc-cadix-1845", "os-icgc-cadix-1847", "os-icgc-cadix-679"]),
    (
        "amsterdam-oosterdok",
        "Остердок, Амстердам",
        "Oosterdok, Amsterdam",
        "Амстердам",
        ["rijks-RP-P-1904-3864", "rijks-KOG-AA-1-2-19", "rijks-KOG-AA-8-71"],
    ),
    (
        "amsterdam-westerdok",
        "Вестердок, Амстердам",
        "Westerdok, Amsterdam",
        "Амстердам",
        ["rijks-RP-P-1904-3866", "rijks-KOG-AA-1-2-20"],
    ),
    ("brussels", "Ратуша Брюсселя", "Hôtel de Ville de Bruxelles", "Брюссель", ["rijks-RP-P-1908-1979"]),
    ("bologna", "Башни Азинелли и Гаризенда", "Torre degli Asinelli, Bologna", "Болонья", ["rijks-RP-P-1908-259"]),
    ("naples", "Королевский дворец, Неаполь", "Palazzo Reale di Napoli", "Неаполь", ["rijks-RP-P-1908-258"]),
    ("rome-peter", "Собор Святого Петра, Рим", "Basilica di San Pietro, Vaticano", "Рим", ["rijks-RP-P-1944-1699"]),
    ("salerno", "Салерно", "Salerno, Italia", "Салерно", ["os-ekm-salerno"]),
    ("amalfi", "Собор Амальфи", "Duomo di Amalfi", "Амальфи", ["os-ekm-amalfi"]),
]


def geocode(query: str) -> dict | None:
    url = "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=" + urllib.parse.quote(query)
    res = subprocess.run(["curl", "-sS", "--http1.1", "-m", "40", "-A", UA, url], capture_output=True)
    time.sleep(1.2)
    try:
        hits = json.loads(res.stdout)
    except ValueError:
        return None
    return (
        {
            "lat": round(float(hits[0]["lat"]), 5),
            "lon": round(float(hits[0]["lon"]), 5),
            "display": hits[0]["display_name"][:120],
        }
        if hits
        else None
    )


def main() -> int:
    have = {p["id"]: p for p in json.loads(OUT.read_text(encoding="utf-8"))["places"]} if OUT.exists() else {}
    for lid, name, query, city, sheets in LANDMARKS:
        found = have.get(lid) or {}
        if not found.get("lat"):
            hit = geocode(query)
            found = (
                {"lat": hit["lat"], "lon": hit["lon"], "evidence": "Nominatim: " + hit["display"]}
                if hit
                else {"evidence": "not geocoded"}
            )
        have[lid] = {
            "id": lid,
            "name_ru": name,
            "query": query,
            "city": city,
            "sheets": sheets,
            "approximate": True,
            **found,
        }
    order = [lm[0] for lm in LANDMARKS]
    OUT.write_text(
        json.dumps(
            {
                "version": 1,
                "note": "Координаты приблизительные (OSM Nominatim); какое здание на листе, выбрано человеком.",
                "places": [have[i] for i in order],
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(sum(1 for i in order if have[i].get("lat")), "of", len(order), "located")
    return 0


if __name__ == "__main__":
    sys.exit(main())
