"""Publish only explicitly approved pages and image assets from the tested museum ZIP."""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = "https://zukevich-blip.github.io/-city-on-paper/"
PAGES = (
    "index.html", "salon/index.html", "closeup/index.html",
    "photography/index.html", "world/index.html",
    "exhibitions/city-as-evidence/index.html",
    "exhibitions/lost-florence/index.html", "discover/index.html",
    "journeys/index.html", "atlas-prototype/index.html", "detective/index.html", "studio/index.html",
    "ornaments/index.html", "atelier/bargue/index.html",
    "atelier/ornament/index.html", "printlab/index.html",
    "fieldwork/index.html", "ideas/index.html",
    "poc/compare/index.html", "poc/compare/editor.html",
    "eras/index.html",
)
DATA = (
    "data/curation/cc0-gallery-20261103.json",
    "data/curation/close-reading-20261103.json",
    "data/curation/close-reading-benoist-20261103.json",
    "data/curation/era-journeys-20261102.json",
    "data/curation/world-cities-v1.json",
    "data/curation/benoist-paris-musees-v1.json",
    "data/curation/museum-expansion-v1.json",
    "data/curation/modern-city-photography-v1.json",
    "data/curation/world-graphic-archive-v1.json",
    "data/curation/modern-photos-cc0-20261103.json",
    "data/stories/madeleine-dossier-20261103.json",
    "data/research/benoist-production-network-v1.json",
    "data/catalog/ornament-workshop-2026-11-02.json",
    "data/catalog/bargue-academy-2026-11-02.json",
    "data/catalog/ledger-2026-11-01.csv",
    "data/ideas/radar-20261103.json",
)
ASSETS = (
    "assets/art/cc0", "assets/art/expansion", "assets/photos/cc0",
    "poc/compare", "docs/ux/mockups", "eras", "assets/nav",
)
FORBIDDEN = ("data/candidates", "docs/consilium", ".github", ".git",
             "PROJECT_HANDOFF.md", "serve_local.py")


def copy(src: Path, dst: Path, rel: str, mandatory: bool = False) -> None:
    original = src / rel
    if not original.exists():
        if mandatory:
            raise FileNotFoundError(f"Missing verified museum file: {rel}")
        return
    target = dst / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if original.is_dir():
        shutil.copytree(original, target, dirs_exist_ok=True)
    else:
        shutil.copy2(original, target)


def optimize(page: Path, rel: str) -> None:
    content = page.read_text(encoding="utf-8")
    if "</head>" not in content:
        raise ValueError(f"Missing HTML head: {rel}")
    address = BASE + ("" if rel == "index.html" else rel.removesuffix("index.html"))
    title_match = re.search(r"<title>(.*?)</title>", content, re.S | re.I)
    title = re.sub(r"\s+", " ", html.unescape(title_match.group(1))).strip() if title_match else "Город на бумаге"
    metas = (
        f'<link rel="canonical" href="{html.escape(address, quote=True)}">\n'
        f'<meta property="og:type" content="website">\n'
        f'<meta property="og:site_name" content="City on Paper / Город на бумаге">\n'
        f'<meta property="og:title" content="{html.escape(title, quote=True)}">\n'
        f'<meta property="og:url" content="{html.escape(address, quote=True)}">\n'
        '<meta property="og:locale" content="ru_RU">\n'
        '<meta name="twitter:card" content="summary">\n'
        '<meta name="robots" content="index,follow,max-image-preview:large">\n'
    )
    if rel == "index.html":
        content = re.sub(r'<button\s+data-go="research"\s*>[^<]*</button>', "", content)
        content = re.sub(r'(<section\s+id="research"\s+class="tab wrap")',
                         r'\1 hidden', content, count=1)
        # This source-labelled image is a Library of Congress original.
        metas += (
            f'<meta property="og:image" content="{BASE}poc/compare/pairs/madeleine-historic-loc-pga14315v.jpg">\\n'
            '<meta property="og:image:alt" content="Париж. Церковь Мадлен, литография Филиппа Бенуа">\\n'
        )
        content = content.replace(
            "Частная исследовательская выставка.", "Открытая цифровая выставка."
        ).replace(
            "Исследовательская версия.", "Открытая исследовательская версия."
        ).replace(
            "Интерактивный просмотрщик Claude:", "Интерактивный просмотрщик:"
        ).replace(
            "27 записей перечитаны Claude по музейным источникам.",
            "27 карточек сверены по музейным источникам."
        )
        stats = (
            '<div class="stats">'
            '<div class="stat"><strong>27</strong><span>Сверенных музейных карточек</span></div>'
            '<div class="stat"><strong>41</strong><span>Работа CC0 в кураторском ядре</span></div>'
            '<div class="stat"><strong>2</strong><span>Исторические пары для сравнения</span></div>'
            '<div class="stat"><strong>19</strong><span>Залов и инструментов</span></div>'
            '</div>'
        )
        has_statistics = '<div class="stats">' in content
        content, changed = re.subn(
            r'<div class="stats"><div class="stat">.*?</div></div>',
            stats, content, count=1,
        )
        if has_statistics and changed != 1:
            raise ValueError("Museum home statistics layout unexpectedly changed")
        content = content.replace(
            '</footer>',
            '<nav style="padding:12px 24px;text-align:center;font-size:13px">'
            '<a href="about/">О проекте</a> · '
            '<a href="rights/">Источники и права</a> · '
            '<a href="privacy/">Конфиденциальность</a> · '
            '<a href="contribute/">Присоединиться к музею</a>'
            '</nav></footer>', 1
        )
        content = content.replace(
            '<a href="journeys/" class="btn">Путешествовать по векам</a>',
            '<a href="journeys/" class="btn">Путешествовать по векам</a>'
            '<button class="btn" type="button" id="share-museum">Поделиться музеем</button>',
            1
        )
        share_script = (
            '<script>document.getElementById("share-museum")?.addEventListener('
            '"click", async function () {'
            'const title="Город на бумаге / City on Paper";'
            'const url=location.origin+location.pathname;'
            'try{if(navigator.share){await navigator.share({title,url,'
            'text:"Литографии, города и сравнение эпох."});}'
            'else if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(url);'
            'this.textContent="Ссылка скопирована";}'
            'else{this.textContent="Скопируйте адрес из браузера";}}'
            'catch(err){if(err?.name!=="AbortError")'
            'this.textContent="Скопируйте адрес из браузера";}'
            '});</script>'
        )
        content = content.replace('</body>', share_script + '</body>', 1)
        metas += (
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"CollectionPage",'
            '"name":"Город на бумаге / City on Paper",'
            '"description":"Открытый музей исторической графики, городов и архитектуры.",'
            f'"url":"{BASE}"'
            '}</script>\n'
        )
    page.write_text(content.replace("</head>", metas + "</head>", 1),
                    encoding="utf-8")


def info_pages(destination: Path) -> None:
    docs = {
        "about": ("О проекте",
            "«Город на бумаге» объединяет подлинные исторические виды городов, источники музеев, архитектурные маршруты, упражнения и визуальные сравнения разных эпох.",  # noqa: E501 — editorial copy
            "Некоторые датировки и атрибуции остаются исследовательскими гипотезами. Совпадение исторического и современного ракурса не гарантировано."),  # noqa: E501 — editorial copy
        "rights": ("Источники и права",
            "У произведений указаны учреждения, авторы, ссылки и права. Отметка Библиотеки Конгресса No known restrictions не равна лицензии CC0.",  # noqa: E501 — editorial copy
            "Современные фотографии CC BY и CC BY-SA требуют указания авторов, лицензий и изменений. Ошибки в описании можно сообщить через GitHub Issues."),  # noqa: E501 — editorial copy
        "contribute": ("Присоединиться к музею",
            "Открытый музей принимает предложения литографий, карт, исторических видов, исправления архитектурных терминов и помощь с реальными ракурсами. Участниками могут быть специалисты и любители истории.",  # noqa: E501 — editorial copy
            "Нужны ссылки на первоисточники, авторы, датировка, география и точные сведения о правах. Открытый доступ не означает, что любое изображение можно перепубликовать. Не загружайте чужие файлы без разрешения."),  # noqa: E501 — editorial copy
        "privacy": ("Конфиденциальность",
            "Для посещения не нужна регистрация. Закладки, заметки и фотографии пользователя, если они доступны в мастерских, хранятся локально в браузере. Сайт не включает рекламные пиксели и формы сбора адресов.",  # noqa: E501 — editorial copy
            "Хостинг GitHub Pages может вести технические журналы. Переходы по ссылкам на музейные источники открывают сторонние сайты."),  # noqa: E501 — editorial copy
    }
    for slug, (heading, first, second) in docs.items():
        page = destination / slug / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        extra = (
            '<p><a href="https://github.com/zukevich-blip/-city-on-paper/issues/new/choose">'
            'Предложить произведение, ракурс или исправление через GitHub</a></p>'
            '<p><a href="https://github.com/zukevich-blip/-city-on-paper/blob/main/CONTRIBUTING.md">'
            'Как участвовать и как мы проверяем источники</a></p>'
            if slug == "contribute" else ""
        )
        page.write_text(
            '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{heading} | Город на бумаге</title>'
            '<style>body{margin:0;background:#f5f0e7;color:#292720;'
            'font:17px/1.7 system-ui,sans-serif}main{max-width:740px;'
            'margin:9vh auto;padding:0 23px}h1{font:normal 48px Georgia,serif}'
            'a{color:#893f32}nav,footer{border-top:1px solid #d8d0c5;'
            'padding:22px 0;font-size:14px}</style></head><body>'
            '<main><nav><a href="../">Город на бумаге</a> · '
            '<a href="../salon/">Галерея</a> · <a href="../world/">Атлас</a></nav>'
            f'<h1>{heading}</h1><p>{first}</p><p>{second}</p>{extra}'
            '<footer><a href="../about/">О проекте</a> · '
            '<a href="../rights/">Источники и права</a> · '
            '<a href="../privacy/">Конфиденциальность</a> · '
            '<a href="../contribute/">Присоединиться</a> · '
            '<a href="https://github.com/zukevich-blip/-city-on-paper/issues/new">'
            'Сообщить об ошибке в GitHub</a></footer></main></body></html>',
            encoding="utf-8",
        )
        optimize(page, f"{slug}/index.html")


def build(source: Path, output: Path) -> dict:
    source, output = source.resolve(), output.resolve()
    if source == output or output.is_relative_to(source):
        raise ValueError("Public output must not overwrite the archive")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for rel in PAGES:
        copy(source, output, rel, mandatory=True)
    for rel in (*DATA, *ASSETS):
        copy(source, output, rel)
    for rel in PAGES:
        optimize(output / rel, rel)
    info_pages(output)
    for rel in FORBIDDEN:
        if (output / rel).exists():
            raise ValueError(f"Restricted file found in public bundle: {rel}")
    (output / ".nojekyll").touch()
    (output / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: " + BASE + "sitemap.xml\n",
        encoding="utf-8",
    )
    pages = [*PAGES, "about/index.html", "rights/index.html", "privacy/index.html", "contribute/index.html"]
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for rel in pages:
        ET.SubElement(ET.SubElement(root, "url"), "loc").text = (
            BASE + ("" if rel == "index.html" else rel.removesuffix("index.html"))
        )
    ET.ElementTree(root).write(output / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (output / "PUBLIC_BUILD.json").write_text(json.dumps({
        "source": "Tested GitHub Actions City on Paper museum artifact",
        "public_html_pages": len(pages), "candidate_research_included": False,
        "source_review": "Automated metadata checks; human artwork editorial review pending"
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"html_pages": len(pages), "files": sum(p.is_file() for p in output.rglob("*"))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.source, args.out))
