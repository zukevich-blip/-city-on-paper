# ruff: noqa: E501, E402
"""Thematic exhibitions from open-access museum records (rights are the museums' own statements, read from their APIs).

in : data/research/authors/other-authors-v1.json  (records with rights_status == open_confirmed and an image URL)
out: book/exhibitions.json, book/img/exhibits/*.jpg (resized copies, 1280 px)
Nothing is invented: captions are made from the record's own title, date, technique, series, institution and accession.
A work whose rights are not 'open_confirmed' is never selected.
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.world.imgfetch import fetch

SRC = ROOT / "data/research/authors/other-authors-v1.json"
OUT = ROOT / "book/exhibitions.json"
IMG = ROOT / "book/img/exhibits"
OK_INST = {"The Metropolitan Museum of Art", "National Gallery of Art, Washington", "Art Institute of Chicago",
           "The Cleveland Museum of Art", "Rijksmuseum"}
ART = {"giovanni-battista-piranesi": "Джованни Баттиста Пиранези", "giuseppe-vasi": "Джузеппе Вази", "hubert-robert": "Юбер Робер",
       "israel-silvestre": "Израэль Сильвестр", "canaletto": "Каналетто", "michele-marieschi": "Микеле Мариески",
       "bernardo-bellotto": "Бернардо Беллотто", "francesco-guardi": "Франческо Гварди", "luca-carlevarijs": "Лука Карлеварис",
       "charles-meryon": "Шарль Мерион", "nicolas-marie-joseph-chapuy": "Николя Шапюи"}
EXHIBITS = [
    {"id": "rim", "title": "Рим во всём его величии", "city": "Рим",
     "lede": "Рим глазами тех, кто рисовал его с натуры и по памяти: офорты Пиранези и Вази, фантазии Юбера Робера. Все листы открыты музеями; подписи составлены из их записей.",
     "pick": [("giovanni-battista-piranesi", r"Colosseum|Pantheon|St\. Peter|Trevi|Capitol|Forum|Constantine|Concord|Bacchus|Lateran|Maggiore", 9),
              ("giuseppe-vasi", r"Rome|Roma|Tiber|Panorama|Maria", 3), ("hubert-robert", r"Rome|Roman|Colosseum|Colonnade|Medici", 3),
              ("israel-silvestre", r"Rome|Capitoline|Sun Temple", 2)]},
    {"id": "venetsiya", "title": "Венеция сквозь столетия", "city": "Венеция",
     "lede": "Площади, мосты и лагуна в офортах и рисунках Каналетто, Мариески, Беллотто и Гварди.",
     "pick": [("canaletto", r"Venice|Rialto|Ascension|Campo", 5), ("michele-marieschi", r"Rialto|Salute|Giorgio|Venice", 4),
              ("bernardo-bellotto", r"Piazza|Venetian|Venice", 2), ("francesco-guardi", r"Venice|San Marco|Piazza", 3)]},
    {"id": "ischeznuvshiy-parizh", "title": "Исчезнувший Париж", "city": "Париж",
     "lede": "Париж до больших перестроек середины XIX века: офорты Мериона и виды Шапюи. Многих улиц и зданий, показанных здесь, давно нет.",
     "pick": [("charles-meryon", r"Pont|Notre|Palais|Paris|Saint|Louvre|Morgue", 10), ("nicolas-marie-joseph-chapuy", r"Paris|Saint|Church", 2),
              ("hubert-robert", r"Paris|Louvre", 2)]},
]


def size_url(r: dict) -> str:
    u = r["image_url"]
    if "api.nga.gov/iiif" in u:
        u = u.replace("/full/full/", "/full/1400,/")
    return u


def credit(r: dict) -> str:
    return f"{r['institution']}, {r['accession']}; {r['rights_statement'].split(' (')[0]}"


def main() -> int:
    recs = [r for r in json.loads(SRC.read_text(encoding="utf-8"))["records"]
            if r["rights_status"] == "open_confirmed" and r.get("image_url") and r["institution"] in OK_INST and r.get("original_title")]
    chosen, seen = {}, set()
    for ex in EXHIBITS:
        works = []
        for art, rx, limit in ex["pick"]:
            pool = [r for r in recs if r["artist_id"] == art and re.search(rx, r["original_title"], re.I) and not re.search(r"\(recto\)|\(verso\)|^Plate \d+: ", r["original_title"])]
            pool.sort(key=lambda r: ({"National Gallery of Art, Washington": 0, "The Metropolitan Museum of Art": 1, "Art Institute of Chicago": 2}.get(r["institution"], 3), r["record_id"]))
            n = 0
            for r in pool:
                key = (art, re.sub(r"\W+", "", r["original_title"].lower())[:40])
                if key in seen:
                    continue
                seen.add(key)
                works.append(r)
                n += 1
                if n >= limit:
                    break
        chosen[ex["id"]] = works
    all_r = {r["record_id"]: r for ws in chosen.values() for r in ws}
    ids = list(all_r)
    with ThreadPoolExecutor(4) as ex_:
        res = dict(zip(ids, ex_.map(lambda i: fetch(size_url(all_r[i]), IMG / (i.replace(":", "-") + ".jpg")), ids), strict=True))
    out = []
    for ex in EXHIBITS:
        ws = [r for r in chosen[ex["id"]] if res.get(r["record_id"])]
        out.append({"id": ex["id"], "title": ex["title"], "city": ex["city"], "lede": ex["lede"], "works": [{
            "id": r["record_id"].replace(":", "-"), "title": r["original_title"].split(", from ")[0][:140], "series": r.get("series"),
            "artist": ART.get(r["artist_id"], r["author_name"]), "role": next((p.get("role_as_stated") for p in r["participants"] if p.get("role_as_stated")), None),
            "date": r["date_as_stated"], "technique": r.get("technique_as_stated"), "institution": r["institution"], "accession": r["accession"],
            "record_url": r["record_url"], "rights": r["rights_statement"], "credit": credit(r),
            "image": "img/exhibits/" + r["record_id"].replace(":", "-") + ".jpg", "w": res[r["record_id"]]["w"], "h": res[r["record_id"]]["h"]} for r in ws]})
    OUT.write_text(json.dumps({"version": 1, "rule": "rights are the museum's statement from its open-data feed; captions come from the record", "exhibitions": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print({e["id"]: len(e["works"]) for e in out}, "failed:", [i for i in ids if not res.get(i)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
