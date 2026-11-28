# ruff: noqa: E501
"""Three illustrated stories with different compositions. Text comes only from the records (title, date, technique, museum) and from
the sourced place story of the book; no event is added from memory."""
from __future__ import annotations

import json
from pathlib import Path

BOOK = Path(__file__).resolve().parents[2] / "book"


def main() -> int:
    inside = {b["id"]: b for b in json.loads((BOOK / "inside.json").read_text(encoding="utf-8"))["buildings"]}
    places = {p["id"]: p for p in json.loads((BOOK / "places.json").read_text(encoding="utf-8"))["places"]}
    mad = places["madeleine"]
    rome = inside["pantheon-rome"]
    S = [
        {"id": "prazdniki-venetsii", "layout": "scenes", "title": "Праздники Венеции: пять сцен", "city": "Венеция",
         "lede": "Площадь, набережная и лагуна в дни торжеств: четыре листа серии праздников дожей по Каналетто и сцена площади Франческо Гварди. Подписи составлены по записям музеев.",
         "scenes": [{"work": "ex-nga-139341", "kicker": "Сцена 1"}, {"work": "ex-nga-103816", "kicker": "Сцена 2"}, {"work": "ex-nga-47091", "kicker": "Сцена 3"}, {"work": "oa-nga-103851", "kicker": "Сцена 4"}, {"work": "ex-met-338925", "kicker": "Сцена 5 · другой мастер"}],
         "closing": "Первые четыре листа хранит Национальная галерея искусства, пятый Метрополитен. Название места и дата в каждой подписи взяты из записи музея; кто именно гравировал лист по рисунку, смотрите в записи."},
        {"id": "dialog-panteon", "layout": "dialogue", "title": "Диалог мастеров: Пантеон", "city": "Рим",
         "lede": "Один и тот же храм на гравюре, на картине, на плане и на снимке сегодня.",
         "turns": [{"work": "ex-met-348799", "side": "l"}, {"extra": {"building": "pantheon-rome", "kind": "interior-painting"}, "side": "r"}, {"work": "oa-met-363427", "side": "l"}, {"work": "oa-cma-v3-104365", "side": "r"},
                   {"extra": {"building": "pantheon-rome", "kind": "plan", "n": 0}, "side": "l"}, {"modern": {"building": "pantheon-rome", "n": 0}, "side": "r"}],
         "closing": "Внутри истории: " + rome["lede"]},
        {"id": "biografiya-madlen", "layout": "biography", "title": "Биография здания: Мадлен", "city": "Париж",
         "lede": mad["lede_ru"],
         "events": [{"date": f["date"], "text": f["text_ru"], "source": f["source_url"], "source_name": f["source_name"]} for f in mad["facts"]],
         "pieces": [{"after": 4, "work": "bs-parismusees-320295651", "label": "Фасад на листе серии «Vues de Paris»"}, {"after": 4, "work": "bs-parismusees-320295653", "label": "Интерьер на листе № 42"},
                    {"after": 4, "extra": {"building": "madeleine", "kind": "plan"}, "label": "План церкви (чертёж из собрания Paris Musées; дата в источнике не указана)"}, {"after": 6, "modern": {"building": "madeleine", "n": 1}, "label": "Неф сегодня"}],
         "closing": "Что неизвестно: " + " ".join(mad["unknowns_ru"][:2])},
    ]
    (BOOK / "stories.json").write_text(json.dumps({"version": 1, "stories": S}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print([s["id"] for s in S])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
