# ruff: noqa: E501
"""Thematic halls built from the gallery fund (book/gallery.json): each hall is a list of gallery ids with its own layout.
Selection is deterministic (filters + diversity caps); every work keeps the rights and source of the fund."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

BOOK = Path(__file__).resolve().parents[2] / "book"


def year(w):
    m = re.search(r"\b(1[2-9]\d\d)\b", str(w.get("d") or ""))
    return int(m.group(1)) if m else 0


def pick(works, f, n, per_artist=6, per_city=0, key=None):
    out, ca, cc = [], Counter(), Counter()
    for w in sorted([w for w in works if f(w)], key=key or (lambda w: (-min(w["w"], w["h"]), w["id"]))):
        if ca[w["a"]] >= per_artist or (per_city and cc[w["c"]] >= per_city):
            continue
        ca[w["a"]] += 1
        cc[w["c"]] += 1
        out.append(w)
        if len(out) >= n:
            break
    return out


def main() -> int:
    works = json.loads((BOOK / "gallery.json").read_text(encoding="utf-8"))["works"]
    for w in works:
        w["y"] = year(w)
    H = [
        ("tsvet", "Первые цветные фотографии", "wall", "Фотохромы конца XIX века: города, какими их увидели в цвете задолго до цветной плёнки. Каталог Библиотеки Конгресса называет их «нет известных ограничений на воспроизведение».",
         pick(works, lambda w: w["k"] == "photo" and w["c"] and w["w"] >= 600, 72, per_artist=60, per_city=4)),
        ("italiya", "Италия глазами великих художников", "timeline", "От Пиранези и Каналетто до фотохромов: Рим, Венеция, Неаполь, Флоренция в одном ряду по годам.",
         pick(works, lambda w: w["c"] in {"Рим", "Венеция", "Неаполь", "Флоренция", "Падуя", "Верона", "Милан"} and w["y"], 80, per_artist=8, key=lambda w: (w["y"], w["id"]))),
        ("peterburg-moskva", "Петербург и Москва", "magazine", "Две столицы Российской империи: гравюры, литографии и первые цветные снимки.",
         pick(works, lambda w: w["c"] in {"Петербург", "Москва"}, 24, per_artist=8)),
        ("interery", "Дворцовые интерьеры и храмы изнутри", "spreads", "Залы, нефы, лестницы и галереи: взгляд внутрь.",
         pick(works, lambda w: w["k"] == "interior", 28, per_artist=4)),
        ("drevnie", "Античные города и руины", "timeline", "Руины, арки и амфитеатры глазами художников XVII–XIX веков.",
         pick(works, lambda w: w["k"] == "ruins" and w["y"], 60, per_artist=8, key=lambda w: (w["y"], w["id"]))),
        ("panoramy", "Большие панорамы", "wall", "Города и виды в широком кадре: листайте картины вбок.",
         pick(works, lambda w: w["k"] == "panorama", 40, per_artist=6)),
        ("benua-istochniki", "Бенуа: ещё источники", "spreads", "Листы и рисунки Бенуа из дополнительных открытых источников. Авторство только как в записи источника.",
         pick(works, lambda w: w["set"] == "benoist" and w["id"].startswith("bx-"), 20, per_artist=20)),
        ("amerika", "Города Америки в цвете", "magazine", "Чикаго, Нью-Йорк, Квебек и другие: фотохромы и фотографии на рубеже веков.",
         pick(works, lambda w: w["c"] in {"Чикаго", "Нью-Йорк", "Квебек", "Филадельфия", "Бостон", "Сан-Франциско", "Монреаль", "Гавана"} and w["k"] == "photo", 24, per_artist=24, per_city=4)),
        ("mosty", "Мосты и набережные", "timeline", "Мосты и каналы городов: от Венеции до Парижа.",
         pick(works, lambda w: w["k"] == "bridge" and w["y"], 40, per_artist=6, key=lambda w: (w["y"], w["id"]))),
    ]
    halls = [{"id": i, "title": t, "layout": lay, "lede": lede, "ids": [w["id"] for w in ws]} for i, t, lay, lede, ws in H if len(ws) >= 5]
    (BOOK / "halls.json").write_text(json.dumps({"version": 1, "halls": halls}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print({h["id"]: len(h["ids"]) for h in halls})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
