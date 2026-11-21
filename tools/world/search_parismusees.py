#!/usr/bin/env python3
"""Enumerate works by Philippe Benoist and Felix Benoist in the Paris Musees collections.

Re-runnable, polite, standard library only. Writes data/research/benoist/parismusees-search-v1.json
following data/research/benoist/SCHEMA.md. Images are NEVER downloaded: only URLs and pixel sizes
that the public IIIF manifest states are recorded.

Pipeline
  1. Walk every result page of the author queries (and, optionally, series / free-text queries) on
     parismuseescollections.paris.fr and record the hit total the source reports for each query.
  2. Open every distinct record page (roles, series title, technique, dimensions, manifest link).
  3. Read the public IIIF manifest (Droits / Copyright per canvas, canvas width and height).
  4. Group impressions of the same sheet by duplicate_hint.

Rules kept here: unknown is None, never a guess; rights_status is open_confirmed only when the
manifest itself states CC0 for every canvas file; 403 / 429 / CAPTCHA pages are never bypassed and are
written to coverage.blocked.

Usage
  python3 -m tools.world.search_parismusees --cache-dir /tmp/pm-cache
  python3 -m tools.world.search_parismusees --no-series          # author queries only
"""
# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
import html as htmllib
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "research" / "benoist" / "parismusees-search-v1.json"
KNOWN_FILES = (
    ROOT / "data" / "curation" / "benoist-paris-musees-v1.json",
    ROOT / "data" / "curation" / "benoist-parismusees-batch-v1.json",
)
UA = "CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
SITE = "https://www.parismuseescollections.paris.fr"
SOURCE = "parismusees"
BREAKER = 4  # consecutive failed record pages before falling back to card-only records
MIN_DELAY = 1.2
TIMEOUT = 150

AUTHOR_QUERIES = (
    ("author:Benoist, Philippe", "/fr/recherche/AND/auteur/Benoist%2C%20Philippe"),
    ("author:Benoist, Félix", "/fr/recherche/AND/auteur/Benoist%2C%20F%C3%A9lix"),
)
SERIES_QUERIES = (
    ("text:Paris dans sa splendeur", "/fr/recherche/Paris%20dans%20sa%20splendeur"),
    ("text:Vues de Paris", "/fr/recherche/Vues%20de%20Paris"),
    ("text:Promenade dans Paris et ses environs", "/fr/recherche/Promenade%20dans%20Paris%20et%20ses%20environs"),
)
KNOWN_SERIES = (
    ("Paris dans sa splendeur", r"paris dans sa splendeur"),
    ("Promenade dans Paris et ses environs", r"promenade dans paris et (?:ses )?environs"),
    ("Vues de Paris", r"vues de paris"),
)

ROLE_MAP = (  # (substring of the stated role, normalized role) - first match is the primary role
    ("dessinateur", "designer"),
    ("lithographe", "lithographer"),
    ("imprimeur", "printer"),
    ("editeur", "publisher"),
    ("éditeur", "publisher"),
    ("graveur", "engraver"),
    ("auteur du texte", "author_of_text"),
)
ROLE_WORDS = {w for w, _ in ROLE_MAP} | {"dessinateur-lithographe", "imprimeur-lithographe", "lithographe", "graveur"}

PHILIPPE_RE = re.compile(r"^\s*Benoist,\s*Philippe(?:\s*\(|\s*$)")
FELIX_RE = re.compile(r"^\s*Benoist,\s*F[ée]lix(?:\s*\(|\s*$)")


# ---------------------------------------------------------------- pure parsing


def clean(text: str | None) -> str:
    if text is None:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = htmllib.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def parse_search_page(html: str) -> dict:
    """Return {total, cards[], max_page}. total is None when the page does not state it."""
    flat = clean(html)
    m = re.search(r"(\d[\d\s]*?)\s+résultats?\s+trouvés?", flat)
    total = int(re.sub(r"\D", "", m.group(1))) if m else None
    cards = []
    for art in re.finditer(r'<article id="node-(\d+)"[^>]*?about="([^"]+)".*?</article>', html, re.S):
        body = art.group(0)
        t = re.search(r"<h3>(.*?)</h3>", body, re.S)
        authors = [clean(a) for a in re.findall(r'class="auteur-nom">(.*?)</div>', body, re.S)]
        museum = re.search(r'field-name-field-musee.*?field-item even">(.*?)</div>', body, re.S)
        cards.append(
            {
                "node": art.group(1),
                "path": art.group(2),
                "title": clean(t.group(1)) if t else None,
                "authors": authors,
                "museum": clean(museum.group(1)) if museum else None,
            }
        )
    pages = [int(p) for p in re.findall(r"[?&]page=(\d+)", html)]
    pager_nums = [int(n) for n in re.findall(r"pager-(?:current|item)[^>]*>(?:<a[^>]*>)?(\d+)", html)]
    max_page = max(pages + pager_nums) if (pages or pager_nums) else 1
    return {"total": total, "cards": cards, "max_page": max_page}


def split_author_line(line: str) -> dict:
    """'Benoist, Philippe (Genève, en 1813 - en 1905), dessinateur-lithographe' -> name/dates/role."""
    line = clean(line)
    role = None
    if ")" in line:
        head, _, tail = line.rpartition(")")
        head += ")"
        tail = tail.lstrip(", ").strip()
        role = tail or None
        line = head
    else:
        head, sep, tail = line.rpartition(",")
        if sep and fold(tail) in {fold(w) for w in ROLE_WORDS}:
            line, role = head.strip(), tail.strip()
    m = re.match(r"^(.*?)\s*\((.*)\)\s*$", line)
    name, dates = (m.group(1).strip(), m.group(2).strip()) if m else (line.strip(), None)
    return {"name": name, "life_data": dates, "role_as_stated": role}


def normalise_role(role: str | None) -> tuple[str, list[str]]:
    if not role:
        return "unspecified", []
    low = role.lower()
    hits = {}
    for needle, norm in ROLE_MAP:
        pos = low.find(needle)
        if pos >= 0 and norm not in hits:
            hits[norm] = pos
    found = sorted(hits, key=hits.get)  # order of appearance in the stated role
    if not found:
        return "unspecified", []
    return found[0], found[1:]


def parse_record_page(html: str) -> dict:
    """Read one notice page. Missing fields stay None."""
    canon = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    short = re.search(r'<link rel="shortlink" href="[^"]*?/node/(\d+)"', html)
    h1 = re.search(r"<h1>(.*?)</h1>", html, re.S)
    title = clean(h1.group(1)) if h1 else None
    lic = re.search(r'<a href="([^"]+)" class="licence[^"]*">([^<]*)</a>', html)
    droits = re.search(r'class="droits">(.*?)</span>', html, re.S)
    sec = re.search(r'id="infos-secondaires-detail">(.*?)(?:<section|<div class="picto-to-top"|$)', html, re.S)
    block = sec.group(1) if sec else ""
    fields: dict[str, str] = {}
    parts = re.split(r'<div class="field-label">', block)
    for chunk in parts[1:]:
        lab, _, rest = chunk.partition("</div>")
        label = clean(lab).rstrip(":").strip()
        value = clean(rest)
        if label and not fields.get(label):
            fields[label] = value
    authors = []
    for line in re.findall(r'class="auteur-complet">(.*?)</div>', block, re.S):
        authors.append(split_author_line(line))
    dims = {}
    for lab, ul in re.findall(
        r'<div class="field-label">(Dimensions[^<]*)</div>\s*<div class="item-list">(.*?)</ul>', block, re.S
    ):
        dims[clean(lab).rstrip(":")] = "; ".join(clean(li) for li in re.findall(r"<li[^>]*>(.*?)</li>", ul, re.S))
    other_titles = [clean(t) for t in re.findall(r'class="field-items titres">(.*?)</div>', block, re.S)]
    manifest = re.search(r'href="(https://apicollections\.parismusees\.paris\.fr/iiif/\d+/manifest)"', html)
    inventory = None
    date = None
    for label, value in fields.items():
        low = fold(label)
        if "inventaire" in low and value:
            inventory = value
        if low in {"date", "date de creation", "date de realisation", "datation", "periode", "epoque"} and value:
            date = value
    return {
        "record_url": canon.group(1) if canon else None,
        "node": short.group(1) if short else None,
        "title": title,
        "authors": authors,
        "other_titles": other_titles,
        "object_types": [
            clean(x)
            for x in re.findall(r"<a href=\"/fr/recherche/type/oeuvre/ET/types-objet/[^>]*>(.*?)</a>", block, re.S)
        ],
        "denominations": [
            clean(x)
            for x in re.findall(r"<a href=\"/fr/recherche/type/oeuvre/ET/denominations/[^>]*>(.*?)</a>", block, re.S)
        ],
        "techniques": [
            clean(x)
            for x in re.findall(
                r"<a href=\"/fr/recherche/type/oeuvre/ET/materiaux-technique/[^>]*>(.*?)</a>", block, re.S
            )
        ],
        "dimensions": dims or None,
        "description": fields.get("Description") or None,
        "institution": fields.get("Institution") or None,
        "inventory": inventory,
        "date": date,
        "manifest": manifest.group(1) if manifest else None,
        "html_licence_label": clean(lic.group(2)) if lic else None,
        "html_licence_url": lic.group(1) if lic else None,
        "html_rights_caption": clean(droits.group(1)) if droits else None,
        "field_labels": sorted(fields),
    }


def parse_manifest(data: dict) -> dict:
    canvases = []
    for seq in data.get("sequences") or []:
        for cv in seq.get("canvases") or []:
            meta = {clean(m.get("label")): m.get("value") for m in cv.get("metadata") or []}
            img = None
            for im in cv.get("images") or []:
                img = (im.get("resource") or {}).get("@id")
                break
            canvases.append(
                {
                    "canvas_id": cv.get("@id"),
                    "width": cv.get("width") if isinstance(cv.get("width"), int) else None,
                    "height": cv.get("height") if isinstance(cv.get("height"), int) else None,
                    "droits": meta.get("Droits"),
                    "copyright": meta.get("Copyright"),
                    "image_url": img,
                }
            )
    md = {}
    for m in data.get("metadata") or []:
        md.setdefault(clean(m.get("label")), m.get("value"))
    return {"label": data.get("label"), "metadata": md, "canvases": canvases}


def canvas_is_cc0(cv: dict) -> bool:
    c = (cv.get("copyright") or "").lower()
    d = (cv.get("droits") or "").lower()
    return "publicdomain/zero" in c or d.startswith("cc0")


def rights_from_canvases(canvases: list[dict]) -> tuple[str, str | None]:
    """open_confirmed only if the manifest states CC0 for every file."""
    if not canvases:
        return "unknown", None
    stmts = [" | ".join(x for x in (cv.get("droits"), cv.get("copyright")) if x) for cv in canvases]
    statement = "; ".join(dict.fromkeys(s for s in stmts if s)) or None
    if all(canvas_is_cc0(cv) for cv in canvases):
        return "open_confirmed", statement
    if statement and re.search(r"©|tous droits|all rights|reserv", statement, re.I):
        return "link_only", statement
    return "rights_pending", statement


def detect_series(title: str | None, other_titles: list[str]) -> tuple[str | None, str | None]:
    """Series from a known-series phrase in the title; plate number only when it follows the phrase."""
    for cand in [title or ""] + list(other_titles):
        flat = fold(cand)
        for label, pat in KNOWN_SERIES:
            m = re.search(pat, flat)
            if m:
                rest = flat[m.end() :]
                n = re.match(r"\s*(\d{1,3})\b", rest)
                if not n:
                    n = re.match(r"\s*(?:no|n)\s*(\d{1,3})\b", rest)
                return label, (n.group(1) if n else None)
    return None, None


def series_title_on_sheet(other_titles: list[str]) -> str | None:
    for t in other_titles:
        if "(Titre de la série)" in t:
            return t.replace("(Titre de la série)", "").strip()
    return None


def classify_artist(authors: list[dict]) -> tuple[str, str, str]:
    names = [a["name"] + (f" ({a['life_data']})" if a.get("life_data") else "") for a in authors]
    ph = any(PHILIPPE_RE.match(n) for n in names)
    fe = any(FELIX_RE.match(n) for n in names)
    other_b = [
        a["name"]
        for a in authors
        if re.match(r"^\s*Benoist\b", a["name"]) and not (PHILIPPE_RE.match(a["name"]) or FELIX_RE.match(a["name"]))
    ]
    if ph and fe:
        return (
            "uncertain-benoist",
            "medium",
            "Both Philippe and Félix Benoist are named on the record; not assigned to one.",
        )
    if other_b and not (ph or fe):
        return (
            "uncertain-benoist",
            "low",
            f"Another Benoist is named ({', '.join(other_b)}); neither Philippe nor Félix matched exactly.",
        )
    if ph or fe:
        who = "philippe-benoist" if ph else "felix-benoist"
        data = next((a for a in authors if (PHILIPPE_RE if ph else FELIX_RE).match(a["name"])), {})
        conf = "high" if data.get("life_data") else "medium"
        return (
            who,
            conf,
            "Name matches the museum authority form exactly"
            + ("" if data.get("life_data") else "; no life data on the record")
            + ".",
        )
    return "other", "low", "No Philippe or Félix Benoist among the named participants."


def object_type(denoms: list[str], types: list[str]) -> str | None:
    blob = fold(" ".join(denoms + types))
    if "illustration de livre" in blob:
        return "page_in_book"
    if "estampe" in blob:
        return "print"
    if "dessin" in blob:
        return "drawing"
    if re.search(r"\balbum\b", blob):
        return "album"
    if re.search(r"\blivre\b", blob):
        return "book"
    return None


def make_duplicate_hint(title: str | None, series: str | None, plate: str | None) -> str | None:
    if not title:
        return None
    base = fold(title)
    if series:
        for _, pat in KNOWN_SERIES:
            base = re.sub(pat, " ", base)
    base = re.sub(r"\b\d{1,3}\b", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return f"{base}|{fold(series) if series else ''}|{plate or ''}"


def node_from_path(path: str | None) -> str | None:
    m = re.search(r"/node/(\d+)", path or "")
    return m.group(1) if m else None


def iiif_id(manifest: str | None) -> str | None:
    m = re.search(r"/iiif/(\d+)/manifest", manifest or "")
    return m.group(1) if m else None


def load_known(files=KNOWN_FILES) -> dict[str, set[str]]:
    keys = {"iiif": set(), "url_slug": set(), "node": set()}
    for f in files:
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for rec in (data.get("items") or []) + (data.get("records") or []):
            for key in ("source_id", "node"):
                if rec.get(key):
                    keys["iiif"].add(str(rec[key]))
            for url in (rec.get("manifest_url"), rec.get("manifest")):
                if iiif_id(url):
                    keys["iiif"].add(iiif_id(url))
            for url in (rec.get("url"), rec.get("record_url")):
                if url:
                    keys["url_slug"].add(url.rstrip("/").rsplit("/", 1)[-1])
                    if node_from_path(url):
                        keys["node"].add(node_from_path(url))
    return keys


def is_known(rec: dict, known: dict[str, set[str]]) -> bool:
    slug = (rec.get("record_url") or "").rstrip("/").rsplit("/", 1)[-1]
    return bool(
        (iiif_id(rec.get("iiif_manifest")) in known["iiif"])
        or (slug and slug in known["url_slug"])
        or (rec.get("_node") and rec["_node"] in known["node"])
    )


def card_only_page(card: dict) -> dict:
    """Minimal page dict from a search-result card when the record page could not be read."""
    authors = [dict(split_author_line(a), role_as_stated=None) for a in card.get("authors") or []]
    return {
        "record_url": SITE + card["path"],
        "node": card.get("node"),
        "title": card.get("title"),
        "authors": authors,
        "_card_only": True,
        "institution": card.get("museum"),
    }


def build_record(
    card: dict, page: dict, manifest: dict | None, found_by: list[str], known: dict[str, set[str]]
) -> dict:
    node = page.get("node") or card.get("node")
    title = page.get("title") or card.get("title")
    other_titles = page.get("other_titles") or []
    series, plate = detect_series(title, other_titles)
    artist, conf, note = classify_artist(page.get("authors") or [])
    participants = []
    for a in page.get("authors") or []:
        primary, also = normalise_role(a.get("role_as_stated"))
        p = {"name": a["name"], "role_as_stated": a.get("role_as_stated"), "role_normalized": primary}
        if also:
            p["role_normalized_also"] = also
        if a.get("life_data"):
            p["life_data_as_stated"] = a["life_data"]
        participants.append(p)
    cvs = (manifest or {}).get("canvases") or []
    status, statement = rights_from_canvases(cvs)
    if not cvs:
        statement = page.get("html_rights_caption")
        if page.get("html_licence_label"):
            statement = f"{statement or ''} [page licence label: {page['html_licence_label']}; not confirmed by a manifest]".strip()
    first = cvs[0] if cvs else {}
    techniques = page.get("techniques") or []
    city = "Paris" if title and re.search(r"\bparis\b", fold(title)) else None
    rec = {
        "record_id": f"{SOURCE}:{node}",
        "artist_id": artist,
        "participants": participants,
        "original_title": title,
        "translated_title_ru": None,
        "series": series,
        "series_title_on_sheet": series_title_on_sheet(other_titles),
        "plate_number": plate,
        "volume": None,
        "city": city,
        "place": None,
        "country": None,
        "geo_confidence": "city" if city else "unknown",
        "date_as_stated": page.get("date"),
        "technique_as_stated": "; ".join(techniques) or None,
        "object_type": object_type(page.get("denominations") or [], page.get("object_types") or []),
        "dimensions_as_stated": page.get("dimensions"),
        "institution": page.get("institution") or card.get("museum"),
        "accession": page.get("inventory"),
        "record_url": page.get("record_url"),
        "iiif_manifest": page.get("manifest"),
        "image_url": first.get("image_url"),
        "image_width": first.get("width"),
        "image_height": first.get("height"),
        "canvas_count": len(cvs) if manifest else None,
        "rights_statement": statement,
        "rights_status": status,
        "duplicate_hint": make_duplicate_hint(title, series, plate),
        "impression_note": None,
        "verification_status": "search_hit_only" if page.get("_card_only") else "source_record_read",
        "attribution_confidence": conf,
        "attribution_note": note,
        "found_by": sorted(set(found_by)),
        "known_before": False,
        "_node": node,
    }
    if card.get("authors") and not page.get("authors"):
        rec["attribution_note"] += " Search-card authors only: " + "; ".join(card["authors"])
    if page.get("_card_only") and artist == "other" and any(q.startswith("author:") for q in found_by):
        # The result card lists only the first authors; the author query itself matched the authority record.
        hit = {q for q in found_by if q.startswith("author:")}
        phil, fel = any("Philippe" in q for q in hit), any("Félix" in q for q in hit)
        rec["artist_id"] = "uncertain-benoist" if phil == fel else ("philippe-benoist" if phil else "felix-benoist")
        rec["attribution_confidence"] = "medium"
        rec["attribution_note"] = (
            "Assigned from the author-query hit ("
            + "; ".join(sorted(hit))
            + "); the search card shows other authors only and the record page was not read."
        )
    rec["known_before"] = is_known(rec, known)
    del rec["_node"]
    return rec


def group_duplicates(records: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for r in records:
        if r["artist_id"] == "other":
            continue
        groups.setdefault(r["duplicate_hint"] or f"nohint:{r['record_id']}", []).append(r)
    out = []
    for hint, items in sorted(groups.items()):
        out.append(
            {
                "duplicate_hint": hint,
                "impressions": len(items),
                "record_ids": [i["record_id"] for i in items],
                "artist_ids": sorted({i["artist_id"] for i in items}),
                "any_known_before": any(i["known_before"] for i in items),
            }
        )
        if len(items) > 1:
            for i in items:
                i["impression_note"] = (
                    f"{len(items)} records share this duplicate_hint; check whether they are impressions of one sheet or different compositions with a similar title."
                )
    return {"unique_compositions": len(out), "groups": out}


# ---------------------------------------------------------------- network


class Fetcher:
    def __init__(self, cache_dir: Path | None, delay: float = MIN_DELAY):
        self.cache_dir = cache_dir
        self.delay = delay
        self.last = 0.0
        self.blocked: list[dict] = []
        self.requests = 0
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, url: str) -> Path | None:
        return self.cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".txt") if self.cache_dir else None

    def get(self, url: str, attempts: int = 3) -> str | None:
        cp = self._cache_path(url)
        if cp and cp.exists():
            return cp.read_text(encoding="utf-8")
        for attempt in range(1, attempts + 1):
            wait = self.delay - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            self.requests += 1
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr,en;q=0.5"})
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    text = resp.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as exc:
                if exc.code in (403, 429):
                    self.blocked.append({"url": url, "http": exc.code, "why": "access refused; not bypassed"})
                    return None
                if exc.code in (404, 410):
                    self.blocked.append({"url": url, "http": exc.code, "why": "not found"})
                    return None
                err = f"HTTP {exc.code}"
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                err = f"{type(exc).__name__}: {exc}"
            else:
                if len(text) < 500:
                    err = f"short/empty body ({len(text)} bytes)"
                    print(f"  retry {attempt}/{attempts} {url}: {err}", file=sys.stderr)
                    time.sleep(10 * attempt)
                    continue
                if re.search(r"captcha|are you a robot|access denied", text[:4000], re.I):
                    self.blocked.append({"url": url, "http": 200, "why": "CAPTCHA / challenge page; not bypassed"})
                    return None
                if cp:
                    cp.write_text(text, encoding="utf-8")
                return text
            print(f"  retry {attempt}/{attempts} {url}: {err}", file=sys.stderr)
            time.sleep(5 * attempt)
        self.blocked.append({"url": url, "http": None, "why": f"failed after {attempts} attempts: {err}"})
        return None


def walk_query(fetch: Fetcher, label: str, path: str, max_pages: int) -> dict:
    cards, per_page, total = [], [], None
    page = 1
    while page <= max_pages:
        url = SITE + path + (f"?page={page}" if page > 1 else "")
        html = fetch.get(url)
        if html is None:
            per_page.append({"page": page, "url": url, "cards": None, "error": "blocked or failed"})
            break
        parsed = parse_search_page(html)
        if total is None:
            total = parsed["total"]
        per_page.append(
            {"page": page, "url": url, "cards": len(parsed["cards"]), "hits_reported_by_source": parsed["total"]}
        )
        print(f"[{label}] page {page}: {len(parsed['cards'])} cards, source total {parsed['total']}", file=sys.stderr)
        cards.extend(parsed["cards"])
        if not parsed["cards"] or page >= parsed["max_page"] or (total is not None and len(cards) >= total):
            break
        page += 1
    return {
        "query": label,
        "path": path,
        "hits_reported_by_source": total,
        "cards_seen": len(cards),
        "pages": per_page,
        "cards": cards,
    }


def run(args) -> dict:
    fetch = Fetcher(Path(args.cache_dir) if args.cache_dir else None)
    known = load_known()
    queries = list(AUTHOR_QUERIES) + ([] if args.no_series else list(SERIES_QUERIES))
    walked = []
    seen: dict[str, dict] = {}
    found_by: dict[str, list[str]] = {}
    for label, path in queries:
        is_author = label.startswith("author:")
        res = walk_query(fetch, label, path, args.max_pages if is_author else args.series_max_pages)
        walked.append({k: v for k, v in res.items() if k != "cards"})
        for c in res["cards"]:
            keep = is_author or any("Benoist" in a for a in c["authors"])
            if not keep:
                walked[-1]["cards_not_benoist_on_card"] = walked[-1].get("cards_not_benoist_on_card", 0) + 1
                continue
            seen.setdefault(c["node"], c)
            found_by.setdefault(c["node"], []).append(label)
    records = []
    consecutive_fail = 0
    for node, card in seen.items():
        html = None if consecutive_fail >= BREAKER else fetch.get(SITE + card["path"])
        page = parse_record_page(html) if html else None
        if page is None or not page["node"] or not page["authors"]:
            consecutive_fail += 1
            if consecutive_fail == BREAKER:
                fetch.blocked.append(
                    {
                        "url": SITE,
                        "http": None,
                        "why": f"{BREAKER} consecutive record pages came back empty/failed (throttling); "
                        "remaining records kept as search_hit_only from the result cards, no further hammering",
                    }
                )
            records.append(build_record(card, card_only_page(card), None, found_by[node], known))
            print(f"card-only {records[-1]['record_id']} {records[-1]['artist_id']}", file=sys.stderr)
            continue
        consecutive_fail = 0
        manifest = None
        if page["manifest"]:
            raw = fetch.get(page["manifest"])
            if raw:
                try:
                    manifest = parse_manifest(json.loads(raw))
                except ValueError:
                    fetch.blocked.append({"url": page["manifest"], "http": 200, "why": "manifest is not JSON"})
        records.append(build_record(card, page, manifest, found_by[node], known))
        print(
            f"record {len(records)}/{len(seen)} {records[-1]['record_id']} {records[-1]['artist_id']} {records[-1]['rights_status']}",
            file=sys.stderr,
        )
    # reconcile search hits with the record page: only Benoist records are kept in the output
    records = [r for r in records if r["artist_id"] != "other"] + [r for r in records if r["artist_id"] == "other"]
    grouping = group_duplicates(records)
    by_artist: dict[str, int] = {}
    for r in records:
        by_artist[r["artist_id"]] = by_artist.get(r["artist_id"], 0) + 1
    kept = [r for r in records if r["artist_id"] != "other"]
    open_img = [r for r in kept if r["rights_status"] == "open_confirmed" and r["image_width"] and r["image_height"]]
    author_hits = {w["query"]: w["hits_reported_by_source"] for w in walked if w["query"].startswith("author:")}
    return {
        "version": 1,
        "source": "Paris Musées collections (parismuseescollections.paris.fr + apicollections.parismusees.paris.fr IIIF)",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coverage": {
            "queries": [
                {
                    "query": w["query"],
                    "url": SITE + w["path"],
                    "hits_reported_by_source": w["hits_reported_by_source"],
                    "pages": w["pages"],
                    **(
                        {"cards_not_benoist_on_card": w["cards_not_benoist_on_card"]}
                        if "cards_not_benoist_on_card" in w
                        else {}
                    ),
                }
                for w in walked
            ],
            "pages_walked": sum(len(w["pages"]) for w in walked),
            "hits_total_reported_by_source": sum(v or 0 for v in author_hits.values()),
            "hits_total_note": "Sum over the two author queries; the same notice can match both when Philippe and Félix are co-named. Series/text queries are reported separately and are not added.",
            "records_kept": len(kept),
            "records_by_artist_id": by_artist,
            "records_not_benoist_dropped": by_artist.get("other", 0),
            "unique_compositions": grouping["unique_compositions"],
            "impressions": len(kept),
            "known_before_count": sum(1 for r in kept if r["known_before"]),
            "open_confirmed_with_image_size": len(open_img),
            "http_requests": fetch.requests,
            "blocked": fetch.blocked,
            "notes": [
                "No images downloaded. image_width/height are canvas values from the IIIF manifest; the image resource is the '4k' derivative (height capped near 2160 px), so they are NOT the pixel size of the museum's master scan.",
                "rights_status open_confirmed only when every canvas states CC0 in Droits/Copyright of the manifest.",
                "Accession (inventory number) is not published on the public notice or manifest unless a label containing 'inventaire' exists; null otherwise.",
                "Search pages list authors by exact authority form; Philippe and Félix are matched by exact name, never by surname alone.",
            ],
        },
        "duplicate_groups": grouping["groups"],
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--cache-dir", default=None, help="cache raw responses here so a re-run can resume")
    ap.add_argument("--max-pages", type=int, default=20, help="page cap for author queries")
    ap.add_argument("--series-max-pages", type=int, default=6, help="page cap for series/text queries")
    ap.add_argument("--no-series", action="store_true", help="author queries only")
    args = ap.parse_args(argv)
    result = run(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({result['coverage']['records_kept']} records)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
