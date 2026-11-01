#!/usr/bin/env python3
"""Build 3 low-fi visual directions from ONE content model, so only the style differs.

Images: two Library of Congress lithographs by Ph. Benoist ("No known restrictions on publication"),
shown with object-fit: contain (never cropped, recoloured or filtered). Restricted items (e.g. BnF menus,
NoC-OKLR) appear as link-only cards with no image - this is deliberate.
"""
from html import escape
from pathlib import Path

HERE = Path(__file__).parent

CONTENT = {
    "hero": {"img": "assets/loc-pga14315v.jpg", "title": "Paris. La Madeleine",
             "credit": "Ph. Benoist del.; Imp. Lemercier, [1845–1860]. Library of Congress, LC-DIG-pga-14315",
             "alt": "Hand-coloured lithograph of the Madeleine church in Paris seen from the south-west, with carriages"},
    "facets": ["Города", "Художники", "Альбомы и серии", "Эпохи", "Архитектура", "Рынки и кафе", "Меню"],
    "walk": [
        {"n": 1, "place": "Église de la Madeleine", "work": "Ph. Benoist, «La Madeleine»", "status": "кандидат · совмещение medium (только портик)"},
        {"n": 2, "place": "Jardin du Palais-Royal", "work": "Ph. Benoist, «Jardin du Palais Royal»", "status": "кандидат · фото не подобрано"},
        {"n": 3, "place": "Colonne Vendôme", "work": "«Colonne Vendôme vue de la rue de Castiglione», 1862", "status": "кандидат · ракурс не проверен"},
    ],
    "card2": {"img": "assets/loc-pga14314v.jpg", "title": "Paris. Jardin du Palais Royal",
              "credit": "Ph. Benoist del.; Imp. Lemercier. Library of Congress, LC-DIG-pga-14314",
              "alt": "Lithograph of the Palais-Royal garden with strolling figures and arcades"},
    "food": [
        {"title": "Menu. Café restaurant de la place Blanche", "date": "1894", "inst": "BnF via Europeana",
         "rights": "NoC-OKLR — только ссылка", "kind": "исторический источник"},
        {"title": "Marché à Pontoise (C. Pissarro)", "date": "1895", "inst": "BnF via Europeana",
         "rights": "NoC-OKLR — только ссылка", "kind": "исторический источник"},
        {"title": "Mlle Bécat at the Café des Ambassadeurs (E. Degas)", "date": "1877–78", "inst": "Cleveland Museum of Art",
         "rights": "CC0", "kind": "исторический источник"},
    ],
}

DIRECTIONS = {
    "a-archive": {
        "name": "A · Архивная бумага", "en": "Archive paper",
        "pitch": "Музейный каталог: кремовая бумага, тёмно-коричневые чернила, антиква, тонкие линейки. Изображение — в паспарту, без эффектов.",
        "css": """
:root{--bg:#f3ecdc;--fg:#2a2118;--muted:#76674f;--rule:#cdbf9f;--accent:#7b2f17;--card:#fbf7ee}
body{font-family:Georgia,'Times New Roman',serif}
h1{font-weight:normal;letter-spacing:.04em;text-transform:uppercase;font-size:1.3rem}
.hero figure{background:var(--card);border:1px solid var(--rule);padding:16px}
.chip{border:1px solid var(--rule);border-radius:0;background:transparent;font-variant:small-caps}
.stop .n{font-family:Georgia,serif;font-style:italic;color:var(--accent)}
.card{border:1px solid var(--rule);background:var(--card)}
.map{background:repeating-linear-gradient(0deg,#0000 0 23px,#d9cdb0 23px 24px),repeating-linear-gradient(90deg,#0000 0 23px,#d9cdb0 23px 24px)}
"""},
    "b-atlas": {
        "name": "B · Ночной атлас", "en": "Night atlas",
        "pitch": "Карта прежде всего, тёмная тема, гротеск. Сценарий спутника путешественника: маршрут, точки съёмки, расстояния.",
        "css": """
:root{--bg:#14171c;--fg:#e8e6e1;--muted:#9aa3ad;--rule:#2b313a;--accent:#e7b75f;--card:#1c2128}
body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif}
h1{font-weight:700;font-size:1.4rem}
.layout{display:grid;grid-template-columns:1fr;gap:16px}
@media(min-width:900px){.layout{grid-template-columns:1.1fr .9fr}.map{order:-1;min-height:520px}}
.hero figure{background:#0b0d10;border-radius:12px;padding:8px}
.chip{border-radius:999px;background:var(--card);border:1px solid var(--rule)}
.stop .n{background:var(--accent);color:#14171c;border-radius:50%;width:28px;height:28px;display:inline-grid;place-items:center;font-weight:700}
.card{border-radius:12px;background:var(--card);border:1px solid var(--rule)}
.map{background:radial-gradient(circle at 30% 40%,#24303d,#14171c 70%)}
"""},
    "c-journal": {
        "name": "C · Путевой дневник и кухня", "en": "Travel journal & table",
        "pitch": "Редакционный журнал: крупные заголовки, тёплые акценты, рубрика «Жизнь на площади» (рынки, кафе, меню) на первом экране.",
        "css": """
:root{--bg:#fffaf3;--fg:#1f1a17;--muted:#6f6259;--rule:#ead9c6;--accent:#b5452b;--card:#fff}
body{font-family:'Palatino Linotype',Palatino,Georgia,serif}
h1{font-size:2rem;line-height:1.1;font-style:italic}
.hero figure{background:var(--card);box-shadow:0 2px 0 var(--rule)}
.chip{border-radius:4px;background:#f6e7d6;border:0}
.stop .n{color:var(--accent);font-size:1.6rem;font-style:italic}
.card{background:var(--card);border-top:4px solid var(--accent)}
.map{background:linear-gradient(135deg,#f4e3cf,#fbefe2)}
"""},
}

BASE_CSS = """
*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--fg);line-height:1.45}
.wrap{max-width:1100px;margin:0 auto;padding:16px}
header{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:baseline;border-bottom:1px solid var(--rule);padding-bottom:8px}
.lang{font:13px system-ui,sans-serif;color:var(--muted)}
.mock{font:12px system-ui,sans-serif;color:var(--accent);border:1px solid var(--accent);padding:1px 6px;border-radius:3px}
.pitch{color:var(--muted);font-size:.95rem}
.layout{display:flex;flex-direction:column;gap:16px}
.hero figure{margin:0}
.hero img,.card img{display:block;width:100%;height:auto;max-height:68vh;object-fit:contain}
figcaption,.credit{font:12px/1.4 system-ui,sans-serif;color:var(--muted);margin-top:6px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.chip{font:14px system-ui,sans-serif;padding:10px 14px;min-height:44px;color:var(--fg)}
h2{font-size:1.1rem;margin:18px 0 8px}
.stop{display:grid;grid-template-columns:40px 1fr;gap:8px;padding:10px 0;border-bottom:1px solid var(--rule)}
.stop small{display:block;color:var(--muted);font:12px system-ui,sans-serif}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{padding:12px}
.card .tag{font:11px system-ui,sans-serif;text-transform:uppercase;letter-spacing:.06em;color:var(--accent)}
.nolink{font:12px system-ui,sans-serif;color:var(--muted);border:1px dashed var(--rule);padding:18px 8px;text-align:center;margin:6px 0}
.map{border:1px solid var(--rule);min-height:220px;position:relative;border-radius:inherit}
.pin{position:absolute;width:30px;height:30px;border-radius:50%;background:var(--accent);color:var(--bg);display:grid;place-items:center;font:700 13px system-ui}
.map .note{position:absolute;left:8px;bottom:8px;font:11px system-ui,sans-serif;color:var(--muted)}
footer{font:12px system-ui,sans-serif;color:var(--muted);border-top:1px solid var(--rule);margin-top:24px;padding-top:8px}
"""


def page(key: str, d: dict) -> str:
    c = CONTENT
    stops = "".join(f'<div class="stop"><span class="n">{s["n"]}</span><div><strong>{escape(s["place"])}</strong>'
                    f'<small>{escape(s["work"])}</small><small>{escape(s["status"])}</small></div></div>' for s in c["walk"])
    food = "".join(f'<article class="card"><span class="tag">{escape(f["kind"])}</span><h3 style="font-size:1rem;margin:4px 0">'
                   f'{escape(f["title"])}</h3><div class="nolink">изображение не встраивается · {escape(f["rights"])}</div>'
                   f'<p class="credit">{escape(f["date"])} · {escape(f["inst"])} · открыть у держателя →</p></article>'
                   for f in c["food"])
    chips = "".join(f'<button class="chip">{escape(x)}</button>' for x in c["facets"])
    h, c2 = c["hero"], c["card2"]
    food_html = (f'<section class="food"><h2>Жизнь на площади: рынки, кафе, меню</h2><p class="credit">Исторический источник '
                 f'≠ редакционная интерпретация ≠ современный статус заведения. Мы не утверждаем, что заведение работает сегодня.'
                 f'</p><div class="grid">{food}</div></section>')
    food_top, food_bottom = (food_html, "") if key == "c-journal" else ("", food_html)
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(d['name'])} — макет</title>
<style>{BASE_CSS}{d['css']}</style></head><body><div class="wrap">
<header><h1>Город на бумаге <span class="lang">/ City on Paper</span></h1><span><span class="mock">макет · {escape(d['name'])}</span> <span class="lang">RU · EN</span></span></header>
<p class="pitch">{escape(d['pitch'])}</p>
<div class="chips" role="list">{chips}</div>
{food_top}<div class="layout">
 <section class="hero"><figure><img src="{h['img']}" alt="{escape(h['alt'])}"><figcaption>{escape(h['title'])} — {escape(h['credit'])}. Оригинал без изменений.</figcaption></figure></section>
 <section class="map" aria-label="Схема карты (заглушка, без тайлов)">
  <span class="pin" style="left:38%;top:30%">1</span><span class="pin" style="left:62%;top:58%">2</span><span class="pin" style="left:45%;top:48%">3</span>
  <span class="note">Карта: Leaflet + свободные тайлы — в реализации. Здесь заглушка.</span></section>
</div>
<h2>Прогулка во времени · Париж, 1840–1860 → сегодня</h2>{stops}
{food_bottom}
<h2>В коллекции</h2><div class="grid"><article class="card"><img src="{c2['img']}" alt="{escape(c2['alt'])}"><p class="credit">{escape(c2['title'])} — {escape(c2['credit'])}</p></article></div>
<footer>Макет для Issue #6 (PR C). Изображения: Library of Congress, «No known restrictions on publication». Записи BnF показаны только ссылкой. Без сгенерированной декоративной графики.</footer>
</div></body></html>"""


if __name__ == "__main__":
    for key, d in DIRECTIONS.items():
        (HERE / f"{key}.html").write_text(page(key, d), "utf-8")
        print(HERE / f"{key}.html")
