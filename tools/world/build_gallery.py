# ruff: noqa: E501, E402
"""One gallery fund from everything the museum may show: Benoist sheets, the Heidelberg album, the exhibitions and a large
open-access selection of city and architecture views by other masters.

in : book/benoist-sheets.json, book/albums/*.json, book/exhibitions.json, data/research/authors/other-authors-v1.json
out: book/gallery.json, book/img/gallery/<id>.jpg (1000 px), book/img/gallery/t/<id>.jpg (360 px thumbnails)

Rules: rights come from the museum's own open-data statement (rights_status == open_confirmed); a work is kept only if it
shows a place or an architectural subject (no birds, caricatures, costume studies); duplicates (same image file, same
record, same title+artist) are merged and the richest source wins; Philippe and Félix Benoist are never merged or relabelled.
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.world.imgfetch import fetch

BOOK = ROOT / "book"
GIMG = BOOK / "img/gallery"
OK_INST = {"The Metropolitan Museum of Art", "National Gallery of Art, Washington", "Art Institute of Chicago", "The Cleveland Museum of Art", "Rijksmuseum"}
QUOTA = {"giovanni-battista-piranesi": 80, "charles-meryon": 40, "canaletto": 30, "hubert-robert": 28, "thomas-shotter-boys": 30, "giuseppe-vasi": 22,
         "francesco-guardi": 22, "thomas-hosmer-shepherd": 22, "thomas-girtin": 14, "jacques-rigaud": 18, "nicolas-marie-joseph-chapuy": 18,
         "bernardo-bellotto": 18, "michele-marieschi": 14, "giuseppe-zocchi": 14, "israel-silvestre": 10, "luca-carlevarijs": 10, "eugene-ciceri": 24,
         "louis-jules-arnout": 20, "francois-alexandre-pernot": 12, "thomas-malton": 6, "vasily-sadovnikov": 6, "karl-beggrov": 5, "adolphe-rouargue": 6, "giovanni-battista-falda": 4}
ART_RU = {"giovanni-battista-piranesi": "Джованни Баттиста Пиранези", "giuseppe-vasi": "Джузеппе Вази", "hubert-robert": "Юбер Робер", "israel-silvestre": "Израэль Сильвестр",
          "canaletto": "Каналетто", "michele-marieschi": "Микеле Мариески", "bernardo-bellotto": "Бернардо Беллотто", "francesco-guardi": "Франческо Гварди",
          "luca-carlevarijs": "Лука Карлеварис", "charles-meryon": "Шарль Мерион", "nicolas-marie-joseph-chapuy": "Николя Шапюи", "thomas-shotter-boys": "Томас Шоттер Бойс",
          "thomas-hosmer-shepherd": "Томас Хосмер Шеперд", "thomas-girtin": "Томас Гёртин", "jacques-rigaud": "Жак Ригó", "eugene-ciceri": "Эжен Сисери",
          "louis-jules-arnout": "Луи-Жюль Арну", "francois-alexandre-pernot": "Франсуа-Александр Perno".replace("Perno", "Перно"), "giuseppe-zocchi": "Джузеппе Дзокки",
          "thomas-malton": "Томас Малтон", "vasily-sadovnikov": "Василий Садовников", "karl-beggrov": "Карл Беггров", "adolphe-rouargue": "Адольф Руарг", "giovanni-battista-falda": "Джованни Баттиста Фальда"}
CITY = [("Рим", r"\bRom(e|an)\b|Roma\b|Colosse|Pantheon|Tiber|Vatican|Capitol|Trevi|Forum|Peter'?s|Lateran|Appia|Quirinal|Palatine|Castel S|Tivoli|Albano|Frascati|Maggiore|Campo Vaccino|Ripetta|Pincio|Tempio|Arco |Veduta di Roma"),
        ("Венеция", r"Venice|Venezia|Venetian|Rialto|San Marco|Salute|Giorgio|Zobenigo|Ducal|Bucintoro|Lido|Gezicht.*Venetië"),
        ("Париж", r"Paris|Louvre|Notre-Dame|Pont[- ]Neuf|Tuileries|Seine|Palais de Justice|Saint-Etienne|Tixéranderie|Morgue|Pont au Change|Petit Pont|Palais-Royal|Madeleine|Saint-Roch|Philippe du Roule"),
        ("Лондон", r"London|Thames|Westminster|St\.? Paul|Greenwich|Tower of"),
        ("Неаполь", r"Napl|Napoli|Vesuv|Pompei|Herculan|Pozzuoli"), ("Флоренция", r"Florence|Firenze|Arno|Uffizi|Duomo"),
        ("Версаль", r"Versailles"), ("Дрезден", r"Dresden"), ("Варшава", r"Warsaw|Warszawa"), ("Вена", r"Vienna|Wien"),
        ("Москва", r"Moscow|Москва|Kremlin"), ("Петербург", r"Petersburg|Петербург|Neva"), ("Милан", r"Milan|Milano"), ("Верона", r"Veron"),
        ("Падуя", r"Padua|Padova"), ("Лион", r"Lyon"), ("Оксфорд", r"Oxford"), ("Эдинбург", r"Edinburgh"), ("Бат", r"\bBath\b")]
KIND = [("interior", "Интерьер", r"Interior|Intérieur|Innen|Inside|Binnen|Staircase|Gallery of"), ("panorama", "Панорама", r"Panorama|Panoramic|General View|Bird'?s[- ]eye|Prospect|View of the city"),
        ("ruins", "Руины", r"Ruin|Rovine|Temple|Tempio|Arch of|Arco|Colosse|Amphitheat|Aqueduct|Tomb|Mausole|Baths|Terme"),
        ("church", "Храм", r"Church|Chiesa|Basilica|Cathedral|Duomo|Chapel|Notre-Dame|St\.|Saint|Santa|San |Abbey|Abside"), ("palace", "Дворец", r"Palace|Palazzo|Palais|Château|Villa|Castle|Castello|Hôtel|Louvre"),
        ("bridge", "Мост", r"Bridge|Ponte|Pont\b|Brug"), ("square", "Площадь и улица", r"Piazza|Square|Place\b|Campo|Street|Rue\b|Via\b|Market|Quay|Quai|Canal|Fountain|Fontana")]
BAD = re.compile(r"\(verso\)|\(recto\)|Caricature|Costume|Bird|Lyre|Jay|Eagle|Raven|Soldier|Figure studies|Portrait|Dredge|Float|Fish|Horse|Dog|Skull|Hand\b|Studies? of|Sketchbook|Title Page|Frontispiece|Table|Index", re.I)
FOLDER_SIZES = (1000, 360)


def classify(title: str, series: str | None) -> tuple[str | None, str | None, str | None]:
    text = f"{title} {series or ''}"
    city = next((c for c, rx in CITY if re.search(rx, text, re.I)), None)
    kind = next(((k, ru) for k, ru, rx in KIND if re.search(rx, text, re.I)), (None, None))
    return city, kind[0], kind[1]


def thumb(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        im.thumbnail((360, 360), Image.LANCZOS)
        im.save(dst, "JPEG", quality=76, optimize=True, progressive=True)


def main() -> int:
    items: list[dict] = []
    seen_img: set[str] = set()

    def add(rec: dict) -> None:
        key = rec["img_key"]
        if key in seen_img:
            return
        seen_img.add(key)
        items.append(rec)

    # 1. Benoist sheets (all 102 are kept; role text as the museum states it)
    for s in json.loads((BOOK / "benoist-sheets.json").read_text(encoding="utf-8"))["sheets"]:
        title = s["title"].split(" / ")[0]
        city, kind, kind_ru = classify(s["title"], None)
        who = "; ".join(f"{c['name']} ({c['role_ru']})" for c in s.get("creators", [])) or "; ".join(s.get("participants", [])[:3])
        add({"id": "bs-" + s["id"], "t": title, "to": s["title"], "a": who or "Бенуа, роль в записи не указана", "ak": "benoist", "d": None, "k": kind, "kr": kind_ru, "c": city,
             "set": "benoist", "m": s["holder"], "n": s["accession"], "u": s["record_url"].replace("http://", "https://"), "r": s["rights"], "src": BOOK / s["image"], "link": "#/sheet/" + s["id"], "img_key": s["image"]})
    # 2. album plates
    alb = json.loads((BOOK / "albums/paris-dans-sa-splendeur.json").read_text(encoding="utf-8"))
    for p in alb["plates"]:
        add({"id": f"al-p{p['n']:03d}{'b' if p['bis'] else ''}", "t": p["title"], "to": "Paris dans sa splendeur, " + p["title"], "a": "Издание 1861 г., авторы планш не названы", "ak": "album", "d": "1861", "k": "square", "kr": None,
             "c": "Париж", "set": "album", "m": "Universitätsbibliothek Heidelberg", "n": f"Band {p['volume']}, Planche {p['n']}", "u": p["record_url"], "r": "Public Domain Mark", "src": BOOK / p["image"],
             "link": f"#/album/{alb['id']}/{p['n']}", "img_key": p["image"]})
    # 3. exhibitions
    for e in json.loads((BOOK / "exhibitions.json").read_text(encoding="utf-8"))["exhibitions"]:
        for w in e["works"]:
            city, kind, kind_ru = classify(w["title"], w.get("series"))
            add({"id": "ex-" + w["id"], "t": w["title"], "to": w["title"], "a": w["artist"], "ak": w["artist"], "d": w["date"], "k": kind, "kr": kind_ru, "c": city or e["city"], "set": "exhibit",
                 "m": w["institution"], "n": w["accession"], "u": w["record_url"].replace("http://", "https://"), "r": w["rights"], "src": BOOK / w["image"], "link": "#/exwork/" + w["id"], "img_key": "x:" + w["id"], "ex": e["id"]})
    # 4. large open-access selection
    recs = [r for r in json.loads((ROOT / "data/research/authors/other-authors-v1.json").read_text(encoding="utf-8"))["records"]
            if r["rights_status"] == "open_confirmed" and r.get("image_url") and r["institution"] in OK_INST and r.get("original_title") and r["artist_id"] in QUOTA]
    have_titles = {(i["a"], re.sub(r"\W+", "", i["to"].lower())[:40]) for i in items}
    by_art: dict[str, list] = {}
    for r in recs:
        title = r["original_title"].split(", from ")[0]
        if BAD.search(title):
            continue
        city, kind, kind_ru = classify(title, r.get("series"))
        if not (city or kind):
            continue
        key = (ART_RU.get(r["artist_id"], r["author_name"]), re.sub(r"\W+", "", title.lower())[:40])
        if key in have_titles:
            continue
        have_titles.add(key)
        by_art.setdefault(r["artist_id"], []).append((r, title, city, kind, kind_ru))
    pick = []
    for art, rows in by_art.items():
        rows.sort(key=lambda x: ({"National Gallery of Art, Washington": 0, "The Metropolitan Museum of Art": 1, "Art Institute of Chicago": 2}.get(x[0]["institution"], 3), x[0]["record_id"]))
        pick += rows[: QUOTA[art]]
    print("selected new:", len(pick))
    def url_of(r):
        u = r["image_url"]
        return u.replace("/full/full/", "/full/1400,/") if "api.nga.gov/iiif" in u else u
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda x: fetch(url_of(x[0]), GIMG / (x[0]["record_id"].replace(":", "-") + ".jpg"), max_side=1000, quality=78), pick))
    for (r, title, city, kind, kind_ru), got in zip(pick, res, strict=True):
        if not got:
            continue
        rid = r["record_id"].replace(":", "-")
        add({"id": "oa-" + rid, "t": title[:150], "to": title[:150], "a": ART_RU.get(r["artist_id"], r["author_name"]), "ak": r["artist_id"], "d": r["date_as_stated"], "k": kind, "kr": kind_ru, "c": city, "set": "open",
             "m": r["institution"], "n": r["accession"], "u": r["record_url"], "r": r["rights_statement"].split(" (")[0][:60], "src": GIMG / (rid + ".jpg"), "link": None, "img_key": "oa:" + rid, "ser": r.get("series")})
    out = []
    for it in items:
        src = it.pop("src")
        if not src.exists():
            continue
        with Image.open(src) as im:
            w, h = im.size
        tid = it["id"] + ".jpg"
        thumb(src, GIMG / "t" / tid)
        it["i"] = src.relative_to(BOOK).as_posix()
        it["th"] = "img/gallery/t/" + tid
        it["w"], it["h"] = w, h
        it.pop("img_key", None)
        if w / h >= 2.0:
            it["k"], it["kr"] = "panorama", "Панорама"
        out.append(it)
    (BOOK / "gallery.json").write_text(json.dumps({"version": 1, "rule": "rights from the museum's open-data statement; titles in Russian only where a translation exists, original title always kept", "count": len(out), "works": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    from collections import Counter
    print(len(out), Counter(i["set"] for i in out), Counter(i["c"] for i in out).most_common(8), Counter(i["k"] for i in out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
