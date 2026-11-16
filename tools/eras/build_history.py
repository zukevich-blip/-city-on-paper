#!/usr/bin/env python3
"""Build eras/data/history.json from the historian's research files (data/history/cities.json, masters.json).

Validation (fail closed): every chapter needs at least one https source; timeline items and facts without an https
source are dropped; texts are stored as plain text (the page escapes them).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "history"
OUT = ROOT / "eras" / "data" / "history.json"


def ok(u) -> bool:
    return isinstance(u, str) and u.startswith("https://")


def sources(lst) -> list[dict]:
    return [{"title": str(s.get("title") or "")[:140], "url": s["url"]} for s in lst or [] if ok(s.get("url"))]


def build() -> dict:
    cities, masters = [], []
    f = SRC / "cities.json"
    for c in (json.loads(f.read_text("utf-8")).get("cities", []) if f.exists() else []):
        chapters = [{"title": ch["title"], "text": ch["text"], "sources": sources(ch.get("sources"))}
                    for ch in c.get("chapters", [])
                    if ch.get("title") and ch.get("text") and sources(ch.get("sources"))]
        if not c.get("city") or not chapters:
            continue
        fact = c.get("did_you_know") or {}
        cities.append({
            "city": c["city"], "tagline": c.get("tagline", ""), "intro": c.get("intro", ""), "chapters": chapters,
            "timeline": sorted(({"year": t["year"], "text": t["text"], "source_url": t["source_url"]}
                                for t in c.get("timeline", []) if ok(t.get("source_url")) and t.get("text")),
                               key=lambda t: str(t["year"])),
            "did_you_know": fact if ok(fact.get("source_url")) else None})
    f = SRC / "masters.json"
    for m in (json.loads(f.read_text("utf-8")).get("masters", []) if f.exists() else []):
        if m.get("bio") and sources(m.get("sources")):
            masters.append({k: m.get(k) or "" for k in ("name", "name_ru", "years", "role", "bio", "uncertain")}
                           | {"sources": sources(m.get("sources"))})
    return {"version": "2026-11-16", "note": "Тексты составлены по открытым источникам; ссылки даны у каждой главы.",
            "cities": cities, "masters": masters}


if __name__ == "__main__":
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(len(d["cities"]), "city histories,", len(d["masters"]), "masters")
