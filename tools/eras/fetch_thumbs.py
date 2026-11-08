#!/usr/bin/env python3
"""Self-host small preview copies (500 px, Wikimedia's own standard thumbnail) of open-rights Commons images.

Why: upload.wikimedia.org answers 429 to many visitors (shared mobile IPs, many images per page), so cards showed
empty frames. The preview is Wikimedia's own downscale of the same file — no crop, no recolouring; the card keeps the
credit, rights label and a link to the original record. Resumable: files already present are kept.

Usage: python tools/eras/fetch_thumbs.py [curation.json ...]
Writes eras/thumbs/<key>.jpg and eras/data/thumbs.json {commons_file_name: "thumbs/<key>.jpg"}.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "eras" / "thumbs"
MAP = ROOT / "eras" / "data" / "thumbs.json"
UA = "CityOnPaperThumbs/1.0 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)"
MAX_BYTES = 1_500_000


def commons_name(url: str) -> str | None:
    """Return the decoded Commons file name for any upload/thumb URL form, else None."""
    p = urllib.parse.urlparse(url or "")
    if p.scheme != "https" or p.netloc not in ("upload.wikimedia.org", "thumb.wikimedia.org"):
        return None
    parts = p.path.split("/")
    if "commons" not in parts:
        return None
    i = parts.index("commons")
    rest = parts[i + 1:]
    if rest and rest[0] == "thumb":
        rest = rest[1:]
    if len(rest) < 3:
        return None
    return urllib.parse.unquote(rest[2])


def key(name: str) -> str:
    return hashlib.sha1(name.encode("utf-8")).hexdigest()[:16]


def get(url: str) -> bytes | None:
    for attempt in range(4):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                if not r.headers.get("Content-Type", "").startswith("image/"):
                    return None
                data = r.read(MAX_BYTES + 1)
                return data if len(data) <= MAX_BYTES else None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(8 * (attempt + 1))
                continue
            return None
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5)
    return None


def collect(paths: list[Path]) -> list[str]:
    names = []
    atlas = json.loads((ROOT / "eras" / "data" / "atlas.json").read_text("utf-8"))
    for c in atlas["cities"]:
        for w in c.get("works", []):
            names.append(commons_name(w.get("image")))
    for p in paths:
        d = json.loads(p.read_text("utf-8"))
        for it in d if isinstance(d, list) else d.get("items", []):
            names.append(commons_name(it.get("image")))
    seen, out = set(), []
    for n in names:
        if n and n not in seen and not n.lower().endswith((".svg", ".pdf", ".tif", ".tiff", ".djvu")):
            seen.add(n)
            out.append(n)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    old = json.loads(MAP.read_text("utf-8")) if MAP.exists() else {}
    names = collect([Path(a) for a in sys.argv[1:]])
    result, miss = {}, []
    for i, n in enumerate(names):
        if i % 25 == 0:
            print(f"{i}/{len(names)}", flush=True)
        f = OUT / f"{key(n)}.jpg"
        if f.exists():
            result[n] = f"thumbs/{f.name}"
            continue
        q = urllib.parse.quote(n.replace(" ", "_"))
        h = hashlib.md5(n.replace(" ", "_").encode("utf-8")).hexdigest()
        base = f"https://thumb.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/500px-{q}"
        data = get(base)
        time.sleep(0.7)
        if data and data[:3] == b"\xff\xd8\xff" or (data and data[:8] == b"\x89PNG\r\n\x1a\n"):
            f.write_bytes(data)
            result[n] = f"thumbs/{f.name}"
        else:
            miss.append(n)
            if n in old:
                result[n] = old[n]
    MAP.write_text(json.dumps(dict(sorted(result.items())), ensure_ascii=False, indent=0) + "\n", "utf-8")
    print(f"{len(result)} thumbnails, {len(miss)} missing")
    for n in miss[:20]:
        print("  missing:", n)


if __name__ == "__main__":
    main()
