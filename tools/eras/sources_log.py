#!/usr/bin/env python3
"""Generate docs/vision-lab/SOURCES_AND_RIGHTS.md from eras/data/eras.json (single source of truth)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
d = json.loads((ROOT / "eras/data/eras.json").read_text("utf-8"))
KIND = {"print": "литография/гравюра", "photo": "фотография", "photochrom": "фотохром", "today": "сегодня"}
rows = []


def cell(s):
    return str(s or "").replace("|", "/").replace("\n", " ")


def add(city, place, r, kind):
    creators = "; ".join(f'{c["name"]} ({c["role"]})' if c.get("role") else c["name"] for c in r.get("creators", []))
    shown = "встроено" if (r.get("file") or r.get("image")) else "только ссылка"
    cols = [city, cell(place), cell(r.get("year_label", "")), kind, cell(r["title"]), cell(creators),
            cell(r.get("institution", "")), f'[карточка]({r["object_url"]})', cell(r["rights_short"]), shown]
    rows.append("| " + " | ".join(cols) + " |")


P = d["portal"]
add("—", "портал", {**P, "year_label": "1769", "creators": [{"name": "G. de L'Isle; Ph. Buache"}],
                     "institution": "Library of Congress, G&M"}, "карта")
for c in d["cities"]:
    if c.get("plan"):
        add(c["name"], "план города", {**c["plan"], "year_label": "", "creators": [{"name": c["plan"]["credit"]}],
                                        "institution": ""}, "карта")
    for p in c["places"]:
        if p.get("plan_detail"):
            det = {**p["plan_detail"], "year_label": "1878", "creators": [{"name": "E. D. Vorzet"}],
                   "institution": "Library of Congress, G&M"}
            add(c["name"], p["title"], det, "деталь карты (IIIF)")
        for i in p["images"]:
            suffix = " · производная" if i["id"].startswith("derived") else ""
            add(c["name"], p["title"], i, KIND.get(i["kind"], i["kind"]) + suffix)
emb = sum(1 for r in rows if r.endswith("встроено |"))
out = ["# Журнал источников и прав (Issue #34, «Атлас эпох»)", "",
       "Сгенерировано `python3 -m tools.eras.sources_log` из `eras/data/eras.json`. "
       "Права проверены 2026-11-07 по записям хранителей; для коммерческого использования "
       "каждую позицию перепроверять (см. VISION_LAB.md, раздел «Права»).", "",
       f"Всего позиций: **{len(rows)}**; встроено файлов: **{emb}**; только ссылка: **{len(rows) - emb}**.", "",
       "| Город | Место | Дата | Вид | Название | Авторы и роли | Хранитель | Источник | Права | Показ |",
       "|---|---|---|---|---|---|---|---|---|---|", *rows, ""]
(ROOT / "docs/vision-lab/SOURCES_AND_RIGHTS.md").write_text("\n".join(out), "utf-8")
print(len(rows), emb)
