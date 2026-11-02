"""Stdlib-only validator for curated catalog records (data/catalog/works/*.json).

Checks a practical subset of schemas/artwork.schema.json:
  * required top-level / nested fields present;
  * enum values (title kind, agent role/certainty, theme tags, place precision, redistribution, review status);
  * id pattern, file name == id, ids unique across the directory;
  * every review state other than ``candidate`` carries at least one evidence URL;
  * ``verified`` attribution needs at least one agent with an evidence_url.

Usage: python3 -m tools.catalog.validate [works_dir] [--schema schemas/artwork.schema.json]
Exit code 0 = no errors.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKS = ROOT / "data" / "catalog" / "works"
DEFAULT_SCHEMA = ROOT / "schemas" / "artwork.schema.json"
URL_RE = re.compile(r"^https?://\S+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_enums(schema_path: Path = DEFAULT_SCHEMA) -> dict[str, set[str]]:
    s = json.loads(schema_path.read_text(encoding="utf-8"))
    p = s["properties"]
    agent = p["agents"]["items"]["properties"]
    return {
        "title_kind": set(p["titles"]["items"]["properties"]["kind"]["enum"]),
        "role": set(agent["role"]["enum"]),
        "certainty": set(agent["certainty"]["enum"]),
        "theme": set(p["theme_tags"]["items"]["enum"]),
        "precision": set(p["place"]["properties"]["precision"]["enum"]),
        "redistribution": set(p["rights"]["properties"]["redistribution"]["enum"]),
        "status": set(s["$defs"]["state"]["properties"]["status"]["enum"]),
        "required": set(s["required"]),
        "review_required": set(p["review"]["required"]),
        "rights_required": set(p["rights"]["required"]),
        "holding_required": set(p["holding"]["required"]),
    }


def validate_record(rec: dict, enums: dict[str, set[str]]) -> list[str]:
    errs: list[str] = []
    rid = rec.get("id", "<no id>")

    def err(msg: str) -> None:
        errs.append(f"{rid}: {msg}")

    for key in sorted(enums["required"] - rec.keys()):
        err(f"missing required field '{key}'")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", str(rec.get("id", ""))):
        err("id does not match ^[a-z0-9][a-z0-9-]*$")

    titles = rec.get("titles") or []
    if not titles:
        err("titles must contain at least one entry")
    for t in titles:
        if not t.get("text") or not t.get("lang"):
            err("title without text/lang")
        if t.get("kind") not in enums["title_kind"]:
            err(f"title kind '{t.get('kind')}' not in enum")

    for a in rec.get("agents") or []:
        if not a.get("name"):
            err("agent without name")
        if a.get("role") not in enums["role"]:
            err(f"agent role '{a.get('role')}' not in enum")
        if a.get("certainty") not in enums["certainty"]:
            err(f"agent certainty '{a.get('certainty')}' not in enum")
        if a.get("wikidata") and not re.match(r"^Q[0-9]+$", a["wikidata"]):
            err(f"bad wikidata id '{a['wikidata']}'")
        if a.get("evidence_url") and not URL_RE.match(a["evidence_url"]):
            err(f"bad agent evidence_url '{a['evidence_url']}'")

    for tag in rec.get("theme_tags") or []:
        if tag not in enums["theme"]:
            err(f"theme tag '{tag}' not in enum")

    place = rec.get("place") or {}
    if place.get("precision") is not None and place["precision"] not in enums["precision"]:
        err(f"place precision '{place['precision']}' not in enum")
    if ("lat" in place) != ("lon" in place):
        err("place has lat without lon (or vice versa)")
    if "lat" in place and place.get("precision") in (None, "city", "unknown"):
        err("coordinates given but precision is city/unknown: drop coordinates or justify precision")

    holding = rec.get("holding") or {}
    for key in sorted(enums["holding_required"] - holding.keys()):
        err(f"holding missing '{key}'")
    if holding.get("object_url") and not URL_RE.match(holding["object_url"]):
        err("holding.object_url is not an http(s) URL")

    rights = rec.get("rights") or {}
    for key in sorted(enums["rights_required"] - rights.keys()):
        err(f"rights missing '{key}'")
    if rights.get("checked") and not DATE_RE.match(rights["checked"]):
        err("rights.checked is not YYYY-MM-DD")
    if rights.get("redistribution") not in enums["redistribution"]:
        err(f"rights.redistribution '{rights.get('redistribution')}' not in enum")

    review = rec.get("review") or {}
    for key in sorted(enums["review_required"] - review.keys()):
        err(f"review missing '{key}'")
    for aspect, state in review.items():
        if not isinstance(state, dict):
            err(f"review.{aspect} is not an object")
            continue
        status = state.get("status")
        if status not in enums["status"]:
            err(f"review.{aspect}.status '{status}' not in enum")
        if status not in ("candidate", None):
            urls = state.get("evidence_urls") or []
            if not urls and status != "not_applicable":
                err(f"review.{aspect} is '{status}' but has no evidence_urls")
            for u in urls:
                if not URL_RE.match(u):
                    err(f"review.{aspect} evidence url '{u}' is not http(s)")
        if state.get("date") and not DATE_RE.match(state["date"]):
            err(f"review.{aspect}.date is not YYYY-MM-DD")
    if review.get("attribution", {}).get("status") == "verified":
        if not any(a.get("evidence_url") for a in rec.get("agents") or []):
            err("attribution verified but no agent has an evidence_url")
    return errs


def validate_dir(works_dir: Path = DEFAULT_WORKS, schema_path: Path = DEFAULT_SCHEMA) -> tuple[int, list[str]]:
    enums = load_enums(schema_path)
    errors: list[str] = []
    seen: dict[str, str] = {}
    files = sorted(works_dir.glob("*.json"))
    for f in files:
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{f.name}: invalid JSON ({exc})")
            continue
        rid = rec.get("id", "")
        if f.stem != rid:
            errors.append(f"{f.name}: file name does not match id '{rid}'")
        if rid in seen:
            errors.append(f"{rid}: duplicate id (also in {seen[rid]})")
        seen[rid] = f.name
        errors.extend(validate_record(rec, enums))
    return len(files), errors


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    schema = DEFAULT_SCHEMA
    if "--schema" in args:
        i = args.index("--schema")
        schema = Path(args[i + 1])
        del args[i:i + 2]
    works = Path(args[0]) if args else DEFAULT_WORKS
    n, errors = validate_dir(works, schema)
    for e in errors:
        print("ERROR", e)
    print(f"{n} records, {len(errors)} errors")
    return 1 if errors or n == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
