"""Read-only connectors to public museum / library / archive APIs.

Rules enforced here (Issue #6, section 3):
* metadata only - image bytes are never downloaded by the harvester;
* every request goes through ``Http``: per-host delay, global request budget,
  on-disk cache, honest error capture. 401/403 and proxy refusals are recorded
  and never retried or worked around; 429/5xx get at most two polite retries
  that honour ``Retry-After``;
* every record starts in the ``candidate`` state for attribution, licensing,
  geo and viewpoint; search hits are never "approved" images;
* a record is kept only if all query tokens occur in its own metadata
  (several APIs return unrelated objects for a query they cannot match).
"""

from __future__ import annotations

import hashlib
import html
import http.client
import json
import os
import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

USER_AGENT = (
    "CityOnPaperResearch/0.2 (read-only metadata research; "
    "https://github.com/zukevich-blip/-city-on-paper)"
)
SCHEMA_ID = "city-on-paper/candidate-v2"


class ProviderError(Exception):
    def __init__(self, provider: str, url: str, status: int | None, message: str):
        super().__init__(f"{provider}: HTTP {status}: {message}")
        self.provider, self.url, self.status, self.message = provider, url, status, message

    def as_dict(self) -> dict[str, Any]:
        return {"provider": self.provider, "url": redact(self.url),
                "status": self.status, "message": self.message[:300]}


def redact(url: str) -> str:
    """Never write API keys into exported files."""
    return re.sub(r"(wskey|api_key|apikey|key|token)=[^&]+", r"\1=REDACTED", url)


@dataclass
class Http:
    cache_dir: Path | None = None
    budget: int = 200
    delay: float = 1.0
    timeout: int = 25
    offline: bool = False  # serve from cache only (tests / reproducible re-runs)
    _last: dict[str, float] = field(default_factory=dict)
    requests_made: int = 0
    cache_hits: int = 0

    def _cache_path(self, url: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / (hashlib.sha256(redact(url).encode()).hexdigest() + ".json")

    def get_json(self, provider: str, url: str, params: dict | None = None,
                 headers: dict | None = None) -> Any:
        if params:
            url = url + ("&" if "?" in url else "?") + urlencode(params, doseq=True)
        cpath = self._cache_path(url)
        if cpath and cpath.exists():
            self.cache_hits += 1
            return json.loads(cpath.read_text("utf-8"))
        if self.offline:
            raise ProviderError(provider, url, None, "offline mode and no cached response")
        if self.budget <= 0:
            raise ProviderError(provider, url, None, "request budget exhausted")
        host = urlparse(url).netloc
        hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        hdrs.update(headers or {})
        for attempt in range(3):
            wait = self.delay - (time.monotonic() - self._last.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            self.budget -= 1
            self.requests_made += 1
            self._last[host] = time.monotonic()
            try:
                with urlopen(Request(url, headers=hdrs), timeout=self.timeout) as resp:
                    raw = resp.read()
                data = json.loads(raw.decode("utf-8"))
                if cpath:
                    cpath.parent.mkdir(parents=True, exist_ok=True)
                    cpath.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
                return data
            except HTTPError as exc:
                retryable = exc.code in (429, 500, 502, 503, 504)
                if not retryable or attempt == 2 or self.budget <= 0:
                    raise ProviderError(provider, url, exc.code, str(exc.reason)) from None
                retry_after = exc.headers.get("Retry-After", "")
                time.sleep(min(int(retry_after) if retry_after.isdigit() else 5 * (attempt + 1), 30))
            except (URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
                if attempt == 2 or self.budget <= 0:
                    raise ProviderError(provider, url, None, f"network: {exc}") from None
                time.sleep(4 * (attempt + 1))
            except json.JSONDecodeError as exc:
                raise ProviderError(provider, url, None, f"not JSON: {exc}") from None
        raise ProviderError(provider, url, None, "unreachable")


# --------------------------------------------------------------------------- helpers

def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = "; ".join(clean(v) for v in value if v)
    return html.unescape(re.sub(r"<[^>]*>", "", str(value))).strip()


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokens(query: str) -> list[str]:
    return [t for t in re.findall(r"\w+", fold(query)) if len(t) > 1]


THEME_KEYWORDS = {
    # food culture / street life (multilingual, historical spellings included)
    "food_market": ["market", "=marché", "=marchés", "mercato", "mercado", "halle", "halles",
                    "markt", "rynek", "targ", "turgus", "рынок", "базар", "bazaar", "fish market",
                    "poissonnerie", "fruit", "vegetable", "legumes", "herbes"],
    "cafe_restaurant": ["cafe", "caffe", "coffee", "restaurant", "brasserie", "tavern", "taverne",
                        "auberge", "osteria", "trattoria", "cabaret", "kawiarnia",
                        "кафе", "трактир", "ресторан", "wine shop", "guinguette", "bill of fare", "=menu"],
    "bakery_shop": ["bakery", "boulangerie", "patisserie", "baker", "shop", "boutique", "shopfront",
                    "confectioner", "butcher", "boucherie", "grocer", "epicerie"],
    "architecture": ["church", "eglise", "cathedral", "cathedrale", "chateau", "castle", "palace",
                     "palais", "bridge", "pont", "tower", "tour", "basilica", "abbey", "abbaye",
                     "university", "gate", "porte", "town hall", "hotel de ville", "facade"],
    "square_street": ["place", "square", "piazza", "plaza", "street", "rue", "via", "boulevard",
                      "quai", "quay", "promenade", "canal", "port", "harbour", "ulica"],
    "city_view": ["view", "vue", "veduta", "vista", "panorama", "widok", "вид", "ansicht", "bird's-eye"],
}


def _has_word(word: str, folded: str, lower: str) -> bool:
    # "=word" is accent-sensitive: French "marché" (market) vs "marche" (march / walk)
    if word.startswith("="):
        return re.search(r"(?<!\w)" + re.escape(word[1:]) + r"(?!\w)", lower) is not None
    return re.search(r"(?<!\w)" + re.escape(fold(word)) + r"(?:s|es)?(?!\w)", folded) is not None


def theme_tags(text: str) -> list[str]:
    """Keyword hints only (multilingual). A curator confirms the theme from the image itself."""
    folded, lower = fold(text), unicodedata.normalize("NFC", text.lower())
    return [tag for tag, words in THEME_KEYWORDS.items() if any(_has_word(w, folded, lower) for w in words)]


OPEN_RIGHTS = ("publicdomain", "public domain", "cc0", "/licenses/by/", "/licenses/by-sa/",
               "noc-us", "/noc/", "nkc", "no known copyright", "no known restrictions")


def rights_category(statement: str, uri: str = "") -> str:
    """open = image reuse plausible after review; restricted = keep metadata/link only."""
    s = fold(f"{statement} {uri}")
    if any(k in s for k in ("inc/", "in copyright", "/inc", "noc-nc", "noc-oklr", "-nc", "non-commercial",
                            "/by-nc", "all rights reserved", "terms of use")):
        return "restricted"
    if any(k in s for k in OPEN_RIGHTS):
        return "open"
    return "unknown"


def record(provider: str, institution: str, source_id: Any, **kw: Any) -> dict[str, Any]:
    title = clean(kw.get("title"))
    creator = clean(kw.get("creator"))
    rights_statement = clean(kw.get("rights_statement"))
    rights_uri = kw.get("rights_uri") or ""
    cat = kw.get("rights_category") or rights_category(rights_statement, rights_uri)
    text_for_tags = " ".join(clean(kw.get(k)) for k in ("title", "description", "subjects", "place"))
    return {
        "schema": SCHEMA_ID,
        "id": f"{provider}:{source_id}",
        "provider": provider,
        "institution": clean(kw.get("institution_override")) or institution,
        "source_id": str(source_id),
        "object_number": clean(kw.get("object_number")),
        "title": title,
        "creator_display": creator,
        "date_display": clean(kw.get("date")),
        "medium": clean(kw.get("medium")),
        "place_display": clean(kw.get("place")),
        "description": clean(kw.get("description"))[:600],
        "subjects": clean(kw.get("subjects"))[:600],
        "source_url": kw.get("source_url") or "",
        "iiif_manifest": kw.get("iiif_manifest") or "",
        "iiif_image_service": kw.get("iiif_image_service") or "",
        # preview is a link to the provider's own derivative; we never mirror it
        "preview_url": (kw.get("preview_url") or "") if cat == "open" else "",
        "rights_statement": rights_statement,
        "rights_uri": rights_uri,
        "rights_category": cat,
        "rights_granularity": kw.get("rights_granularity") or "per-record (as reported by provider)",
        "lat": kw.get("lat"),
        "lon": kw.get("lon"),
        "theme_tags": theme_tags(text_for_tags),
        "status": {"attribution": "candidate", "licensing": "candidate",
                   "geo": "candidate" if kw.get("lat") is not None else "unknown",
                   "viewpoint": "not_checked"},
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "published": False,
    }


MATCH_FIELDS = ("title", "creator_display", "description", "subjects", "place_display", "medium")


def relevant(rec: dict[str, Any], query: str, fields: tuple[str, ...] = MATCH_FIELDS) -> bool:
    hay = fold(" ".join(str(rec.get(k, "")) for k in fields))
    return all(t in hay for t in tokens(query))


# --------------------------------------------------------------------------- providers

def met(http: Http, query: str, limit: int) -> list[dict]:
    base = "https://collectionapi.metmuseum.org/public/collection"
    ids = http.get_json("met", base + "/v1.1/search", {"q": query, "hasImages": "true"}).get("objectIDs") or []
    out = []
    for oid in ids[: limit * 2]:
        if len(out) >= limit:
            break
        d = http.get_json("met", f"{base}/v1/objects/{oid}")
        pd = bool(d.get("isPublicDomain"))
        out.append(record(
            "met", "The Metropolitan Museum of Art", oid,
            object_number=d.get("accessionNumber"), title=d.get("title"),
            creator=" ; ".join(x for x in [d.get("artistDisplayName"), d.get("artistRole"),
                                           d.get("artistDisplayBio")] if x),
            date=d.get("objectDate"), medium=d.get("medium"),
            place=", ".join(x for x in [d.get("city"), d.get("country")] if x),
            subjects=[t.get("term") for t in (d.get("tags") or []) if isinstance(t, dict)],
            description=d.get("creditLine"),
            source_url=d.get("objectURL") or f"https://www.metmuseum.org/art/collection/search/{oid}",
            preview_url=d.get("primaryImageSmall") if pd else "",
            rights_statement="Open Access (CC0)" if pd else "Not in Met Open Access",
            rights_uri="https://creativecommons.org/publicdomain/zero/1.0/" if pd else "",
            rights_category="open" if pd else "restricted"))
    return out


AIC_FIELDS = ("id,title,artist_display,date_display,image_id,is_public_domain,place_of_origin,"
              "medium_display,main_reference_number,credit_line,subject_titles,term_titles,"
              "classification_title,latitude,longitude")


def artic(http: Http, query: str, limit: int) -> list[dict]:
    # AIC asks clients to identify themselves with AIC-User-Agent; without it the edge returns 403.
    d = http.get_json("artic", "https://api.artic.edu/api/v1/artworks/search",
                      {"q": query, "limit": min(limit * 2, 50), "fields": AIC_FIELDS},
                      headers={"AIC-User-Agent": USER_AGENT})
    base = (d.get("config") or {}).get("iiif_url") or "https://www.artic.edu/iiif/2"
    out = []
    for o in d.get("data") or []:
        pd = o.get("is_public_domain") is True
        img = o.get("image_id")
        out.append(record(
            "artic", "Art Institute of Chicago", o["id"], object_number=o.get("main_reference_number"),
            title=o.get("title"), creator=o.get("artist_display"), date=o.get("date_display"),
            medium=o.get("medium_display"), place=o.get("place_of_origin"),
            subjects=(o.get("subject_titles") or []) + (o.get("term_titles") or []),
            description=o.get("credit_line"),
            source_url=f"https://www.artic.edu/artworks/{o['id']}",
            iiif_image_service=f"{base}/{img}" if img else "",
            preview_url=f"{base}/{img}/full/843,/0/default.jpg" if (img and pd) else "",
            rights_statement="Public domain artwork; image CC0 per AIC" if pd else "Not public domain",
            rights_uri="https://creativecommons.org/publicdomain/zero/1.0/" if pd else "",
            rights_category="open" if pd else "restricted",
            lat=o.get("latitude"), lon=o.get("longitude")))
    return out


def cleveland(http: Http, query: str, limit: int) -> list[dict]:
    d = http.get_json("cleveland", "https://openaccess-api.clevelandart.org/api/artworks/",
                      {"q": query, "has_image": 1, "limit": min(limit * 2, 50)})
    out = []
    for o in d.get("data") or []:
        cc0 = o.get("share_license_status") == "CC0"
        web = ((o.get("images") or {}).get("web") or {}).get("url")
        creators = "; ".join(c.get("description") or "" for c in o.get("creators") or [] if isinstance(c, dict))
        out.append(record(
            "cleveland", "Cleveland Museum of Art", o["id"], object_number=o.get("accession_number"),
            title=o.get("title"), creator=creators, date=o.get("creation_date"),
            medium=o.get("technique"), place=o.get("culture"), description=o.get("tombstone"),
            source_url=o.get("url") or f"https://www.clevelandart.org/art/{o.get('accession_number')}",
            preview_url=web if cc0 else "",
            rights_statement=o.get("share_license_status") or "",
            rights_uri="https://creativecommons.org/publicdomain/zero/1.0/" if cc0 else "",
            rights_category="open" if cc0 else "restricted"))
    return out


def commons(http: Http, query: str, limit: int) -> list[dict]:
    d = http.get_json("commons", "https://commons.wikimedia.org/w/api.php", {
        "action": "query", "format": "json", "generator": "search", "gsrsearch": query,
        "gsrnamespace": 6, "gsrlimit": min(limit * 2, 50), "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": 800})
    out = []
    for p in ((d.get("query") or {}).get("pages") or {}).values():
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}

        def get(k: str, meta: dict = meta) -> str:
            return clean((meta.get(k) or {}).get("value"))

        title = p.get("title", "").removeprefix("File:")
        lat, lon = get("GPSLatitude"), get("GPSLongitude")
        out.append(record(
            "commons", "Wikimedia Commons (aggregator; see 'Credit' for holding institution)", p.get("pageid"),
            title=get("ObjectName") or title, creator=get("Artist"), date=get("DateTimeOriginal") or get("DateTime"),
            description=get("ImageDescription"), subjects=get("Categories").replace("|", "; "),
            institution_override="", source_url=info.get("descriptionurl") or "",
            preview_url=info.get("thumburl") or "", rights_statement=get("LicenseShortName"),
            rights_uri=get("LicenseUrl"), lat=float(lat) if lat else None, lon=float(lon) if lon else None,
            rights_granularity="per-file; artwork vs. scan vs. photo rights must be read on the file page",
            object_number=f"{info.get('width')}x{info.get('height')}px"))
        out[-1]["credit"] = get("Credit")[:300]
    return out


def europeana_key() -> str:
    # api2demo is Europeana's documented public demo key (rate-limited); prefer your own.
    return os.environ.get("EUROPEANA_API_KEY", "api2demo")


def europeana(http: Http, query: str, limit: int) -> list[dict]:
    d = http.get_json("europeana", "https://api.europeana.eu/record/v2/search.json", {
        "wskey": europeana_key(), "query": query, "qf": "TYPE:IMAGE", "rows": min(limit * 2, 50),
        "profile": "rich"})
    out = []
    for o in d.get("items") or []:
        lang = o.get("dcTitleLangAware") or {}
        title = (lang.get("def") or o.get("title") or [""])[0]
        rights = (o.get("rights") or [""])[0]
        lat = (o.get("edmPlaceLatitude") or [None])[0]
        lon = (o.get("edmPlaceLongitude") or [None])[0]
        shown_at = (o.get("edmIsShownAt") or [""])[0]
        out.append(record(
            "europeana", "Europeana (aggregator)", o.get("id", "").strip("/"),
            institution_override=(o.get("dataProvider") or [""])[0],
            title=title, creator=o.get("dcCreator"), date=o.get("year"),
            description=o.get("dcDescription"),
            subjects=sum((v for v in (o.get("dcSubjectLangAware") or {}).values()), []),
            place=o.get("edmPlaceLabel") and [x.get("def") for x in o["edmPlaceLabel"]],
            source_url=shown_at or o.get("guid", "").split("?")[0],
            preview_url=(o.get("edmPreview") or [""])[0], rights_statement=rights, rights_uri=rights,
            lat=float(lat) if lat else None, lon=float(lon) if lon else None))
        out[-1]["europeana_url"] = o.get("guid", "").split("?")[0]
    return out


def loc(http: Http, query: str, limit: int) -> list[dict]:
    params = {"q": query, "fo": "json", "c": min(limit * 2, 50), "at": "results,pagination"}
    d = http.get_json("loc", "https://www.loc.gov/photos/", params)
    out = []
    for o in d.get("results") or []:
        imgs = [u.split("#")[0] for u in o.get("image_url") or []]
        restricted = o.get("access_restricted") is True
        out.append(record(
            "loc", "Library of Congress", (o.get("id") or "").rstrip("/").split("/")[-1],
            title=o.get("title"), creator=o.get("contributor"), date=o.get("date"),
            description=o.get("description"), subjects=o.get("subject"), place=o.get("location"),
            source_url=o.get("url") or o.get("id"), iiif_manifest=(o.get("url") or "") + "manifest.json",
            preview_url=imgs[-1] if imgs and not restricted else "",
            rights_statement="Rights advisory on item page (P&P); many 19th-c. prints: no known restrictions",
            rights_uri=(o.get("url") or "") + "#rights", rights_category="unknown" if not restricted else "restricted"))
    return out


def _la_lookup(obj: dict, aat: str) -> str:
    for ident in obj.get("identified_by") or []:
        if any(aat in (c.get("id") or "") for c in ident.get("classified_as") or []):
            return ident.get("content") or ""
    return ""


def rijksmuseum(http: Http, query: str, limit: int) -> list[dict]:
    """Rijksmuseum Linked Art search (2025+ data services). Creator search is field-based."""
    d = http.get_json("rijksmuseum", "https://data.rijksmuseum.nl/search/collection",
                      {"creator": query, "imageAvailable": "true"},
                      headers={"Accept": "application/ld+json"})
    out = []
    for item in (d.get("orderedItems") or [])[:limit]:
        o = http.get_json("rijksmuseum", item["id"], headers={"Accept": "application/ld+json"})
        img, rights = "", ""
        for so in o.get("subject_of") or []:
            for dobj in so.get("digitally_carried_by") or []:
                for ap in dobj.get("access_point") or []:
                    if "iiif.micr.io" in (ap.get("id") or "") and not img:
                        img = ap["id"]
                for r in dobj.get("referred_to_by") or []:
                    rights = rights or r.get("content") or ""
        titles = [i.get("content") for i in o.get("identified_by") or [] if i.get("type") == "Name"]
        agents = []
        for part in (o.get("produced_by") or {}).get("part") or []:
            for ab in part.get("assigned_by") or []:
                for ag in ab.get("assigned") or []:
                    if isinstance(ag, dict) and ag.get("type") in ("Person", "Group") and ag["id"] not in agents:
                        agents.append(ag["id"])
        names = []
        for aid in agents[:4]:
            try:
                a = http.get_json("rijksmuseum", aid, headers={"Accept": "application/ld+json"})
                names += [i.get("content") for i in a.get("identified_by") or [] if i.get("type") == "Name"][:1]
            except ProviderError:
                names.append(aid)
        number = _la_lookup(o, "300312355")
        rec = record(
            "rijksmuseum", "Rijksmuseum", item["id"].rsplit("/", 1)[-1], object_number=number,
            title=titles[0] if titles else "",
            creator="; ".join(n for n in names if n),  # production agents incl. publisher/printer
            description="; ".join(r.get("content", "") for r in o.get("referred_to_by") or [])[:600],
            source_url=f"https://www.rijksmuseum.nl/en/collection/{number}" if number else item["id"],
            preview_url=img.replace("/full/max/", "/full/800,/") if img else "",
            iiif_image_service=img.split("/full/")[0] if img else "",
            rights_statement=rights, rights_uri=rights)
        rec["production_agents_roles_unresolved"] = True
        out.append(rec)
    return out


def vam(http: Http, query: str, limit: int) -> list[dict]:
    d = http.get_json("vam", "https://api.vam.ac.uk/v2/objects/search",
                      {"q": query, "images_exist": 1, "page_size": min(limit * 2, 50)})
    out = []
    for o in d.get("records") or []:
        im = o.get("_images") or {}
        out.append(record(
            "vam", "Victoria and Albert Museum", o.get("systemNumber"), object_number=o.get("accessionNumber"),
            title=o.get("_primaryTitle") or o.get("objectType"),
            creator=(o.get("_primaryMaker") or {}).get("name"), date=o.get("_primaryDate"),
            place=o.get("_primaryPlace"), medium=o.get("objectType"),
            source_url=f"https://collections.vam.ac.uk/item/{o.get('systemNumber')}/",
            iiif_manifest=im.get("_iiif_presentation_url") or "",
            iiif_image_service=im.get("_iiif_image_base_url") or "",
            preview_url="",  # V&A image terms are non-commercial: keep link, do not redistribute
            rights_statement="V&A images: non-commercial use terms (not CC); metadata only here",
            rights_uri="https://www.vam.ac.uk/info/va-websites-terms-conditions",
            rights_category="restricted"))
    return out


def smithsonian(http: Http, query: str, limit: int) -> list[dict]:
    key = os.environ.get("SI_API_KEY") or os.environ.get("API_DATA_GOV_KEY") or "DEMO_KEY"
    d = http.get_json("smithsonian", "https://api.si.edu/openaccess/api/v1.0/search",
                      {"q": f"{query} AND online_media_type:Images", "rows": min(limit * 2, 50), "api_key": key})
    out = []
    for o in (d.get("response") or {}).get("rows") or []:
        c = o.get("content") or {}
        frs = c.get("freetext") or {}
        dn = c.get("descriptiveNonRepeating") or {}
        media = ((dn.get("online_media") or {}).get("media") or [{}])[0]
        usage = (media.get("usage") or {}).get("access", "")
        out.append(record(
            "smithsonian", dn.get("data_source") or "Smithsonian Institution", o.get("id"),
            title=o.get("title"), creator=[x.get("content") for x in frs.get("name") or []],
            date=[x.get("content") for x in frs.get("date") or []],
            source_url=dn.get("record_link") or "", preview_url=media.get("thumbnail") or "",
            rights_statement=usage, rights_uri="https://www.si.edu/openaccess",
            rights_category="open" if usage == "CC0" else "restricted"))
    return out


def panoramax(http: Http, bbox: str, limit: int) -> list[dict]:
    """Modern street-level photos (for pairing only). bbox = 'minlon,minlat,maxlon,maxlat'."""
    d = http.get_json("panoramax", "https://api.panoramax.xyz/api/search", {"bbox": bbox, "limit": limit})
    out = []
    for f in d.get("features") or []:
        p = f.get("properties") or {}
        lon, lat = (f.get("geometry") or {}).get("coordinates", [None, None])[:2]
        lic = p.get("license") or ""
        links = {lk.get("rel"): lk.get("href") for lk in f.get("links") or []}
        rec = record(
            "panoramax", "Panoramax (federated, OpenStreetMap France)", f.get("id"),
            title=f"Street-level photo {p.get('datetime', '')[:10]}",
            creator=(p.get("providers") or [{}])[0].get("name") if p.get("providers") else "",
            date=p.get("datetime"), source_url=links.get("self", ""),
            preview_url=((f.get("assets") or {}).get("thumb") or {}).get("href", ""),
            rights_statement=lic, rights_uri=links.get("license", ""),
            rights_category="open" if lic.upper().startswith(("CC-BY", "ETALAB", "CC0")) else "unknown",
            lat=lat, lon=lon)
        rec["kind"] = "modern_photo"
        rec["azimuth"] = p.get("view:azimuth")
        out.append(rec)
    return out


def wikidata_entities(http: Http, qids: list[str]) -> dict[str, dict]:
    """Entity alignment only (artists, places). Never a source of images."""
    q = ("SELECT ?p ?pLabel ?birth ?death ?ulan ?bnf WHERE { VALUES ?p { %s } "
         "OPTIONAL{?p wdt:P569 ?birth} OPTIONAL{?p wdt:P570 ?death} OPTIONAL{?p wdt:P245 ?ulan} "
         "OPTIONAL{?p wdt:P268 ?bnf} SERVICE wikibase:label { bd:serviceParam wikibase:language \"fr,en\". } }"
         .replace("%s", " ".join("wd:" + x for x in qids)))
    d = http.get_json("wikidata", "https://query.wikidata.org/sparql?format=json&query=" + quote(q))
    out: dict[str, dict] = {}
    for b in d["results"]["bindings"]:
        qid = b["p"]["value"].rsplit("/", 1)[-1]
        e = out.setdefault(qid, {"qid": qid, "label": b.get("pLabel", {}).get("value"),
                                 "birth": set(), "death": set(), "ulan": set(), "bnf": set()})
        for k in ("birth", "death", "ulan", "bnf"):
            if k in b:
                e[k].add(b[k]["value"][:10])
    return {k: {kk: sorted(vv) if isinstance(vv, set) else vv for kk, vv in v.items()} for k, v in out.items()}


PROVIDERS: dict[str, Callable[[Http, str, int], list[dict]]] = {
    "met": met, "artic": artic, "cleveland": cleveland, "commons": commons, "europeana": europeana,
    "loc": loc, "rijksmuseum": rijksmuseum, "vam": vam, "smithsonian": smithsonian,
}


# --------------------------------------------------------------------------- dedup

def dedup_key(rec: dict) -> str:
    """Cross-provider near-duplicate hint (same title+creator+date). Not an identity claim."""
    return hashlib.sha1(fold(f"{rec['title']}|{rec['creator_display'][:40]}|{rec['date_display']}")
                        .encode()).hexdigest()[:12]


def merge(records: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for r in records:
        if r["id"] in by_id:
            q = by_id[r["id"]].setdefault("search_queries", [])
            q.extend(x for x in r.get("search_queries", []) if x not in q)
            continue
        by_id[r["id"]] = r
    groups: dict[str, list[str]] = {}
    for r in by_id.values():
        r["dedup_group"] = dedup_key(r)
        groups.setdefault(r["dedup_group"], []).append(r["id"])
    for r in by_id.values():
        r["possible_duplicates"] = [x for x in groups[r["dedup_group"]] if x != r["id"]]
    return list(by_id.values())
