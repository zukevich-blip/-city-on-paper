#!/usr/bin/env python3
"""Worldwide source-attributed city print discovery from Wikimedia Commons.

The source file page is the licensing authority, not a claim of CC0 for every old print.
Commons' public-domain status is labelled as Commons' assessment, not a legal guarantee.
A geographic match derived from a search query is not proof of the depicted camera/view.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "CityOnPaperMuseum/2.2 (https://city-on-paper-anatolii.tolyaz.chatgpt.site; archival research) Python-urllib/3.12"
RIGHTS = {
    "CC0": ("cc0", "https://creativecommons.org/publicdomain/zero/1.0/"),
    "CC BY 4.0": ("cc_by", "https://creativecommons.org/licenses/by/4.0/"),
    "CC BY-SA 4.0": ("cc_by_sa", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "CC BY 3.0": ("cc_by", "https://creativecommons.org/licenses/by/3.0/"),
    "CC BY-SA 3.0": ("cc_by_sa", "https://creativecommons.org/licenses/by-sa/3.0/"),
    "CC BY 2.0": ("cc_by", "https://creativecommons.org/licenses/by/2.0/"),
    "CC BY-SA 2.0": ("cc_by_sa", "https://creativecommons.org/licenses/by-sa/2.0/"),
}
VIEW = re.compile(
    r"\b(view|vista|veduta|vue|ansicht|stadt|city|town|street|rue|via|"
    r"piazza|place|square|palace|palazzo|schloss|cathedral|church|basilica|"
    r"bridge|pont|puente|river|canal|port|harbour|harbor|marina|quai|"
    r"architecture|temple|mosque|monument|ruins?|tower|castle|garden|"
    r"panorama|scenery|landscape|street|old town|markt|market|"
    r"lithograph|lithography|litografia|engraving|etching|gravure|"
    r"woodblock|woodcut|print|ukiyo.e|chromolithograph|hills?|mountain|"
    r"silhouette|historic district|tomb|fortress|esplanade|plaza)\b",
    re.I,
)
REJECT = re.compile(
    r"\b(portrait|vanity fair|lady |duchess|princess|prince|fashion|photo|photograph|snapshot|"
    r"artist's portrait|coin|stamp|logo|trade mark|vase|ceramic|"
    r"advertising|newspaper|autograph|letterhead|family album|"
    r"costume|woman in|man in|self.portrait|coat of arms|"
    r"medical diagram|anatomy|label|advertisement)\b",
    re.I,
)
FORMAT = re.compile(r"\.(jpe?g|png)$", re.I)
ALIASES = {
    "Токио": ["Tokyo", "Edo"], "Киото": ["Kyoto"], "Осака": ["Osaka"],
    "Стамбул": ["Constantinople", "Istanbul", "Stamboul"],
    "Рим": ["Rome", "Roma"], "Флоренция": ["Florence", "Firenze"],
    "Венеция": ["Venice", "Venezia"], "Неаполь": ["Naples", "Napoli"],
    "Москва": ["Moscow", "Moscou", "Moskva"], "Санкт-Петербург": ["Saint Petersburg", "St Petersburg"],
    "Лондон": ["London", "Londres"], "Париж": ["Paris"],
    "Нью-Йорк": ["New York"], "Гонконг": ["Hong Kong"],
    "Мехико": ["Mexico City", "Ciudad de Mexico"],
    "Пекин": ["Peking", "Beijing"], "Мумбаи": ["Bombay", "Mumbai"],
    "Калькутта": ["Calcutta", "Kolkata"], "Дели": ["Delhi"],
    "Будапешт": ["Budapest", "Buda", "Pest"],
    "Амстердам": ["Amsterdam"], "Вена": ["Vienna", "Wien"],
    "Афины": ["Athens", "Athenes"], "Каир": ["Cairo", "Le Caire"],
    "Буэнос-Айрес": ["Buenos Aires"], "Рио-де-Жанейро": ["Rio de Janeiro"],
    "Кейптаун": ["Cape Town"], "Сидней": ["Sydney"],
    "Александрия": ["Alexandria", "Alexandrie"], "Иерусалим": ["Jerusalem"],
    "Джакарта": ["Batavia", "Jakarta"], "Тбилиси": ["Tiflis", "Tbilisi"],
    "Киев": ["Kiev", "Kyiv"], "Гуанчжоу": ["Canton", "Guangzhou"],
    "Осло": ["Christiania", "Oslo"], "Варшава": ["Warsaw", "Varsovie"],
    "Прага": ["Prague", "Praha"], "Брюссель": ["Brussels", "Bruxelles"],
    "Антверпен": ["Antwerp", "Anvers"], "Краков": ["Krakow", "Cracow"],
    "Алжир": ["Algiers", "Alger"], "Лиссабон": ["Lisbon", "Lisboa"],
    "Порту": ["Porto", "Oporto"],
    "Зальцбург": ["Salzburg"], "Лима": ["Lima"],
}
# Some query hits refer to the artist's home city, not the depicted city.
# Requiring a city name in the title cuts false geography, at the cost of some omissions.
GENERIC = {"city", "lithograph", "engraving", "old", "town", "view", "harbour", "harbor", "print", "photo"}


def clean(value: object, limit: int = 240) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).split())[:limit]


def from_metadata(data: dict, key: str) -> str:
    part = data.get(key, {})
    return str(part.get("value", "")) if isinstance(part, dict) else ""


def source_city_title(title: str, city: dict) -> bool:
    text = title.casefold()
    aliases = ALIASES.get(city["name"])
    if not aliases:
        query = city["query"].split()
        aliases = [query[0]]
        if len(query) > 1 and query[1].lower() not in GENERIC and len(query[1]) > 3:
            aliases.append(" ".join(query[:2]))
    return any(
        bool(re.search(r"(?<!\w)" + re.escape(alias.casefold()) + r"(?!\w)", text))
        for alias in aliases if alias
    )


def classify(title: str) -> str:
    lower = title.casefold()
    if re.search(r"woodblock|woodcut|ukiyo|nishiki", lower):
        return "Ксилография"
    if re.search(r"lithograph|lithography|litho\b|litograf|chromolithograph", lower):
        return "Литография"
    if re.search(r"engraving|etching|gravure|radierung|steel engraving|gravura", lower):
        return "Гравюра / офорт"
    if re.search(r"watercolor|watercolour|drawing|aquarelle", lower):
        return "Рисунок"
    return "Городская графика"


def label_quality(width: int) -> str:
    if width >= 2500:
        return "высокое"
    if width >= 900:
        return "экранное"
    return "невысокое"


def score(title: str, city: dict, width: int) -> int:
    x = title.casefold()
    if not source_city_title(title, city) or not VIEW.search(x) or REJECT.search(x):
        return -1
    pts = 3
    if re.search(r"lithograph|litho|litograf|chromolithograph", x):
        pts += 5
    if re.search(r"veduta|vue|view|vista|engraving|architecture|city|street", x):
        pts += 3
    if width >= 1800:
        pts += 2
    if width >= 3000:
        pts += 1
    if "file:" in x and len(x) < 22:
        pts -= 2
    return pts


def normalize(page: dict, city: dict) -> tuple[dict, int] | None:
    if page.get("ns") != 6 or not FORMAT.search(str(page.get("title", ""))):
        return None
    details = (page.get("imageinfo") or [{}])[0]
    if details.get("mime") not in {"image/jpeg", "image/png"}:
        return None
    width = int(details.get("width") or 0)
    if width < 550:
        return None
    title = page["title"]
    pts = score(title, city, width)
    if pts < 0:
        return None
    extra = details.get("extmetadata") or {}
    license_name = clean(from_metadata(extra, "LicenseShortName"), 80)
    if license_name in RIGHTS:
        rights, lic = RIGHTS[license_name]
    elif license_name.casefold() in {"public domain", "public domain mark"} and (
        clean(from_metadata(extra, "Copyrighted")).casefold() in {"false", "0", "no"}
    ):
        rights, lic = "public_domain_commons", "https://commons.wikimedia.org/wiki/Commons:Copyright_rules"
    else:
        return None
    thumbnail = details.get("thumburl") or details.get("url") or ""
    full = details.get("url") or ""
    source_page = details.get("descriptionurl") or ""
    if (urlsplit(thumbnail).scheme != "https" or
            urlsplit(thumbnail).hostname not in {"thumb.wikimedia.org", "upload.wikimedia.org"} or
            urlsplit(full).scheme != "https" or
            urlsplit(full).hostname != "upload.wikimedia.org" or
            not source_page.startswith("https://commons.wikimedia.org/wiki/File:")):
        return None
    ident = page.get("pageid")
    if not isinstance(ident, int) or ident < 1:
        return None
    author = clean(from_metadata(extra, "Artist"), 140) or "Автор по источнику не установлен"
    display_title = clean(title.removeprefix("File:").rsplit(".", 1)[0].replace("_", " "), 200)
    if not display_title:
        return None
    record = {
        "id": "commons-art-" + str(ident), "name": display_title,
        "title_original": display_title, "city": city["name"], "country": city["country"],
        "region": city["region"], "maker": author, "date": "",
        "date_note": "Датировка оригинала не установлена автоматически",
        "medium": classify(display_title), "theme": "Исторические города",
        "source": "Wikimedia Commons", "source_id": title,
        "url": source_page, "image": thumbnail, "image_large": thumbnail,
        "original_url": full, "original_width": width,
        "quality_tier": label_quality(width), "rights": rights,
        "license_label": license_name, "license_url": lic,
        "verified": "commons_api_extmetadata",
        "selection": "machine_selected_title_relevance",
        "geography_confidence": "title_mentions_city",
        "original_viewpoint_verified": False,
        "note": "Поисковая находка. Проверьте датировку, автора и вид объекта в архиве.",
        "checked": date.today().isoformat(), "provider": "commons_world",
    }
    return record, pts


def search(city: dict, limit: int = 22) -> dict:
    params = {
        "action": "query", "format": "json", "formatversion": "2",
        "generator": "search", "gsrsearch": city["query"],
        "gsrnamespace": 6, "gsrlimit": limit, "maxlag": 5, "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1000,
    }
    url = API + "?" + urlencode(params)
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}), timeout=10) as resp:
        content = resp.read(2_200_001)
    if len(content) > 2_200_000:
        raise ValueError("Oversize Commons search reply")
    return json.loads(content)


def build(cities_path: Path, out: Path, per_city: int, budget: int, max_seconds: int = 480) -> dict:
    """Incrementally collect responsibly; never lose previously cleared source records.

    A 429/503 stops further requests for this run. The next run resumes only the
    unqueried cities from an on-disk progress snapshot restored by the CI cache.
    """
    cities = json.loads(cities_path.read_text(encoding="utf-8"))["cities"]
    folder = out / "data/curation"
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "world-graphic-archive-v1.json"
    progress_path = folder / "world-graphic-progress-v1.json"
    valid_names = {c["name"] for c in cities}
    previous = {}
    done = set()
    if manifest_path.exists():
        try:
            doc = json.loads(manifest_path.read_text(encoding="utf-8"))
            previous = {
                a["id"]: a for a in doc.get("items", [])
                if a.get("id") and a.get("city") in valid_names
                and a.get("provider") == "commons_world"
                and a.get("rights") in {"cc0", "cc_by", "cc_by_sa", "public_domain_commons"}
            }
        except (ValueError, OSError, TypeError, KeyError):
            previous = {}
    if progress_path.exists():
        try:
            state = json.loads(progress_path.read_text(encoding="utf-8"))
            if state.get("version") == 2:
                done = set(state.get("completed_cities", [])) & valid_names
        except (ValueError, OSError, TypeError):
            done = set()

    by_region = {}
    for item in cities:
        if item["name"] not in done:
            by_region.setdefault(item["region"], []).append(item)
    # Visit the six regions in a round-robin order to avoid European bias.
    scheduled = []
    while any(by_region.values()):
        for region in by_region:
            if by_region[region]:
                scheduled.append(by_region[region].pop(0))

    total = dict(previous)
    errors = []
    attempts = 0
    throttled = False
    retry_after = None
    started_at = time.monotonic()
    for city in scheduled:
        if attempts >= budget or time.monotonic() - started_at >= max_seconds:
            break
        attempts += 1
        try:
            response = search(city)
            relevant = []
            for row in (response.get("query") or {}).get("pages", []):
                artwork = normalize(row, city)
                if artwork is not None:
                    relevant.append(artwork)
            relevant.sort(key=lambda item: (-item[1], item[0]["id"]))
            for record, _ in relevant[:per_city]:
                # Preserve the first source's geolocation when a Commons file is
                # returned by multiple cities; do not inflate the item total.
                total.setdefault(record["id"], record)
            done.add(city["name"])
        except HTTPError as exc:
            if exc.code in {429, 503}:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                errors.append({
                    "city": city["name"], "error": f"HTTP {exc.code}",
                    "retry_after": retry_after or "not provided",
                })
                throttled = True
                # No more requests: respects Retry-After without blocking runner.
                break
            errors.append({"city": city["name"], "error": f"HTTP {exc.code}"})
        except (OSError, ValueError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append({"city": city["name"], "error": str(exc)[:140]})
        time.sleep(1.2)

    works = list(total.values())
    works.sort(key=lambda a: (a["region"], a["country"], a["city"], a["name"]))
    found_cities = {a["city"] for a in works}
    regions = {a["region"] for a in works}
    artifact = {
        "version": date.today().isoformat(),
        "scope": "Wikimedia Commons open-licensed / Commons-designated public-domain print discoveries",
        "editorial_status": (
            "Machine-screened. Original attribution, dating, depicted place "
            "and technique have not all been checked by an art historian."
        ),
        "rights_note": (
            "public_domain_commons is NOT CC0; each Commons file page is the source "
            "of its rights claim."
        ),
        "items": works,
    }
    manifest_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    progress_path.write_text(
        json.dumps({
            "version": 2, "completed_cities": sorted(done), "total_seed_cities": len(cities),
            "last_refresh_date": date.today().isoformat(),
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = {
        "attempted_cities_this_run": attempts,
        "completed_cities_total": len(done),
        "city_seed_total": len(cities),
        "found_cities": len(found_cities),
        "regions": len(regions),
        "item_count": len(works),
        "retained_previous_items": len(previous),
        "rate_limited": throttled,
        "retry_after": retry_after,
        "art_types": dict(Counter(a["medium"] for a in works)),
        "rights": dict(Counter(a["rights"] for a in works)),
        "errors": errors[:35],
        "failures_count": len(errors),
        "not_all_cities": len(done) < len(cities),
        "not_curator_approved": True,
    }
    (out / "world-graphic-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cities", type=Path, default=Path("data/curation/world-cities-v1.json"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--per-city", type=int, default=9)
    p.add_argument("--city-budget", type=int, default=65)
    p.add_argument("--max-seconds", type=int, default=480)
    args = p.parse_args()
    report = build(args.cities, args.out, max(1, min(args.per_city, 15)), args.city_budget, args.max_seconds)
    print(json.dumps(report, ensure_ascii=False))
    # Wikimedia 429 must not block the entire museum. The packaged validator
    # decides whether the current partial collection is usable.


if __name__ == "__main__":
    main()
