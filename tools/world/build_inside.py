# ruff: noqa: E501, E402
"""'Внутри истории': building dossiers (facade -> door -> interior -> plan -> section -> today) from real materials only.
Every item is a gallery work (rights and source in the fund) or a local extra with its own credit. Reconstructions are never
drawn here: a missing interior, plan or section is stated as missing, with a lead."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.world.imgfetch import fetch

BOOK = ROOT / "book"
OUT_IMG = BOOK / "img/inside"
SRC = json.loads((ROOT / "data/research/benoist/gemini-v10/inside-source.json").read_text(encoding="utf-8"))


def thumb(u: str, w: int = 1280) -> str:
    m = re.match(r"https://upload\.wikimedia\.org/wikipedia/commons/(\w/\w\w)/(.+)$", u)
    return f"https://thumb.wikimedia.org/wikipedia/commons/thumb/{m.group(1)}/{m.group(2)}/{w}px-{m.group(2)}" if m else u


def extra(key: str, url: str, caption: str, credit: str, page: str, licence: str, kind: str) -> dict | None:
    got = fetch(thumb(url), OUT_IMG / f"{key}.jpg", max_side=1400, quality=80)
    return {"i": f"img/inside/{key}.jpg", "w": got["w"], "h": got["h"], "caption": caption, "credit": credit, "page": page, "licence": licence, "kind": kind} if got else None


def modern(file: str, caption: str, credit: str, page: str) -> dict:
    return {"i": f"../poc/compare/pairs/{file}", "caption": caption, "credit": credit, "page": page, "licence": "CC BY-SA 4.0" if "Panoramax" in credit else "CC0", "kind": "modern"}


def main() -> int:
    fp = {x["id"]: x for x in SRC["floorPlans"]}
    cw = {x["id"]: x for x in SRC["architecturalCutaways"]}
    di = {x["id"]: x for x in SRC["documentedInteriors"]}
    mp, np_, rp = fp["plan-paris-madeleine"], fp["plan-paris-notre-dame"], fp["plan-rome-pantheon"]
    D = []
    D.append({"id": "madeleine", "title": "Церковь Мадлен", "city": "Париж", "place": "madeleine",
              "lede": "Храм, построенный как античный: от портика с 52 колоннами до трёх куполов нефа. Здесь можно пройти от литографии фасада к литографии интерьера, плану и сегодняшним снимкам обоих.",
              "facade": ["bs-parismusees-320295651", "bs-parismusees-320295200", "bs-rijks-RP-P-1905-5495"], "interior": ["bs-parismusees-320295653", "bs-parismusees-320295656"],
              "plan": [extra("madeleine-plan", mp["archivalPlanImageUrl"], mp["archivalPlanCaptionRu"], mp["architecturalSourceRu"], mp["archivalPlanSourcePage"], mp["archivalPlanLicense"], "plan")],
              "modern": [modern("madeleine-photo-panoramax-38b6d262.jpg", "Южный портик, 30.04.2026", "jerome92370 / Panoramax, CC BY-SA 4.0", "https://api.panoramax.xyz/api/collections/732a0136-de7a-4ee5-94d7-07853d4d9f08/items/38b6d262-648f-461e-b9a3-ab05eb22d92a"),
                         modern("madeleine-photo-panoramax-800c5582.jpg", "Неф, 30.04.2026", "jerome92370 / Panoramax, CC BY-SA 4.0", "https://api.panoramax.xyz/api/collections/732a0136-de7a-4ee5-94d7-07853d4d9f08")],
              "journey": {"from": 0, "to": 1, "door": [51, 67], "note": "Монтаж двух снимков с одного дня, не пространственная модель: камера «входит» в дверной проём, а за ним показан реальный кадр нефа."},
              "section": [], "missing": ["Архитектурный разрез церкви не найден в открытых собраниях."]})
    sc = di["paris-sainte-chapelle-upper"]["historicalInterior"]
    D.append({"id": "sainte-chapelle", "title": "Сент-Шапель", "city": "Париж", "place": "sainte-chapelle",
              "lede": "Двухъярусная капелла Людовика Святого. У Бенуа сохранились вид снаружи и два листа церемонии внутри; сегодняшнего снимка и плана в нашем фонде пока нет.",
              "facade": ["bs-parismusees-320290066", "oa-aic-131199"], "interior": ["bs-parismusees-320290060", "bs-parismusees-320290069"],
              "plan": [], "modern": [], "section": [], "extras": [extra("sainte-chapelle-upper", sc["imageUrl"], "Верхняя капелла (фото 2009 г., до реставрации 2015 г.)", "Wikimedia Commons", "https://commons.wikimedia.org/wiki/File:La_Sainte_Chapelle_-_avec_le_Christ_en_Majesté.jpg", "CC BY-SA 3.0", "interior-photo")],
              "missing": ["Плана и разреза капеллы в открытых собраниях пока не найдено.", "Современный снимок можно искать на странице листа («Найти фото сегодня»)."]})
    ps = di["paris-pantheon-nave"]["historicalInterior"]
    D.append({"id": "pantheon-paris", "title": "Пантеон, Париж", "city": "Париж", "place": None,
              "lede": "Здание, которое менялось от церкви Св. Женевьевы до усыпальницы великих людей. Сохранились листы Бенуа, снимки сегодня и конструктивный разрез тройного купола 1881 года: так видно, что держит купол.",
              "facade": ["bs-parismusees-320292326", "bs-rijks-RP-P-1905-5506", "oa-aic-131185"], "interior": [], "plan": [],
              "modern": [modern("pantheon-photo-panoramax-5116b338.jpg", "Площадь и портик, 06.04.2024", "jerome92370 / Panoramax, CC BY-SA 4.0", "https://api.panoramax.xyz/api/collections/9b248e54-31e1-4916-b28b-c9c453453c97/items/5116b338-3c8c-45a6-bc72-5a93da6867f"),
                         modern("pantheon-photo-panoramax-451335cc.jpg", "Колоннада, 20.06.2024", "Britzz / Panoramax, CC BY-SA 4.0", "https://api.panoramax.xyz/api/collections/79f39c2c-f682-4f92-861b-9fcfc22d1166/items/451335cc-20a9-4707-a01e-3fe72b15833d")],
              "section": [extra("pantheon-paris-section", ps["imageUrl"], "Разрез тройного купола Пантеона, архитектурный атлас 1881 г.", "Wikimedia Commons", "https://commons.wikimedia.org/wiki/File:Coupe-Panthéon-Coupoles-Paris-France.jpg", "Public Domain", "section")],
              "missing": ["Исторического интерьерного листа Пантеона в нашем фонде нет: переход через дверь не показываем."]})
    pr = di["rome-pantheon-rotunda"]["historicalInterior"]
    D.append({"id": "pantheon-rome", "title": "Пантеон, Рим", "city": "Рим", "place": None,
              "lede": "Ротонда Адриана глазами Пиранези, Панини и Нолли: фасад, интерьер, план города 1748 года и обмерный план XIX века.",
              "facade": ["ex-nga-75851", "ex-met-348799", "oa-met-363427", "oa-cma-v3-104365"], "interior": [], "plan": [
                  extra("pantheon-rome-nolli", rp["archivalPlanImageUrl"], rp["archivalPlanCaptionRu"], rp["architecturalSourceRu"], rp["archivalPlanSourcePage"], rp["archivalPlanLicense"], "plan"),
                  extra("pantheon-rome-dehio", cw["cutaway-rome-pantheon"]["archivalSectionUrl"], cw["cutaway-rome-pantheon"]["archivalSectionCaptionRu"], "Георг Дехио, 1887–1901", "https://commons.wikimedia.org/wiki/File:Dehio_1_Pantheon_Floor_plan.jpg", "Public Domain", "plan")],
              "extras": [extra("pantheon-rome-panini", pr["imageUrl"], "Интерьер Пантеона, Панини, ок. 1734", "National Gallery of Art, Washington (через Wikimedia Commons)", "https://commons.wikimedia.org/wiki/File:Giovanni_Paolo_Panini,_Interior_of_the_Pantheon,_Rome,_probably_1734.jpg", "CC0 1.0", "interior-painting")],
              "modern": [modern("rome-pantheon-2025.jpg", "Пантеон сегодня, 03.03.2025", "Van Der Meulen Christofle / Викисклад, CC0", "https://commons.wikimedia.org/wiki/File:Ext%C3%A9rieur_du_Panth%C3%A9on_%C3%A0_Rome.jpg")],
              "section": [], "missing": ["Разреза-чертежа XVIII–XIX веков в открытых собраниях для этого окна пока не найдено; параметрическая 3D-реконструкция Gemini не включена: она не документальная."]})
    nd_cut = cw["cutaway-paris-notre-dame"]
    D.append({"id": "notre-dame", "title": "Нотр-Дам", "city": "Париж", "place": "notre-dame",
              "lede": "Западный фасад на листах Бенуа, план собора и конструктивный разрез колокольни Виолле-ле-Дюка: от рисунка фасада к тому, как стоит здание.",
              "facade": ["bs-parismusees-320291945", "bs-rijks-RP-P-1905-5500"], "interior": [], "plan": [
                  extra("notre-dame-plan", np_["archivalPlanImageUrl"], np_["archivalPlanCaptionRu"], np_["architecturalSourceRu"], np_["archivalPlanSourcePage"], np_["archivalPlanLicense"], "plan")],
              "modern": [modern("notre-dame-photo-panoramax-8cf17a79.jpg", "Западный фасад с паперти, 04.04.2025", "JLZIMMERMANN / Panoramax, CC BY-SA 4.0", "https://api.panoramax.xyz/api/collections/")],
              "section": [extra("notre-dame-section", nd_cut["archivalSectionUrl"], nd_cut["archivalSectionCaptionRu"], "Э. Виолле-ле-Дюк, XIX в.", "https://commons.wikimedia.org/wiki/File:Coupe.beffroi.cathedrale.Paris.png", "Public Domain", "section")],
              "missing": ["Интерьерного листа собора среди листов Бенуа в фонде нет."]})
    for d in D:
        for k in ("plan", "section", "extras"):
            if k in d:
                d[k] = [x for x in d[k] if x]
        d.setdefault("extras", [])
    (BOOK / "inside.json").write_text(json.dumps({"version": 1, "rule": "real materials only; missing items are stated", "buildings": D}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print({d["id"]: (len(d["facade"]), len(d["interior"]) + len(d["extras"]), len(d["plan"]), len(d["section"]), len(d["modern"])) for d in D})
    return 0


if __name__ == "__main__":
    sys.exit(main())
