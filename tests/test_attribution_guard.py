"""Guard for the unification: nothing is attributed to Benoist, dated or licensed by default.

Every sheet must carry the museum's own statement (creators or participants), a record page on a known holder host,
and one of the open licences confirmed on the file; every mapped place must say how it was found and be approximate.
"""
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OPEN = ("CC0", "CC0 Paris Musées", "Public Domain Mark", "CC BY 3.0")
HOSTS = {
    "parismuseescollections.paris.fr", "rijksmuseum.nl", "landesarchiv-bw.de", "cdm21055.contentdm.oclc.org",
    "ekm.ee", "muis.ee",
}


def _sheets():
    return json.loads((ROOT / "book/benoist-sheets.json").read_text(encoding="utf-8"))["sheets"]


def test_every_sheet_rests_on_a_museum_statement_and_an_open_licence():
    for s in _sheets():
        assert s["creators"] or s["participants"], f"{s['id']}: no museum statement about who made the sheet"
        assert s["rights"] in OPEN, f"{s['id']}: licence {s['rights']!r} is not a confirmed open one"
        assert s["rights_url"], f"{s['id']}: licence without a page"
        host = (urlparse(s["record_url"]).hostname or "").removeprefix("www.")
        known = host in HOSTS or host.endswith((".muis.ee", ".ekm.ee", ".rijksmuseum.nl"))
        assert known, f"{s['id']}: record page on unknown host {host}"


def test_benoist_is_never_invented_as_author_without_a_role_in_the_record():
    for s in _sheets():
        for c in s["creators"]:
            assert c["role_ru"], f"{s['id']}: creator {c['name']} has no stated role"


def test_places_state_their_evidence_and_stay_approximate():
    data = json.loads((ROOT / "book/sheet-places.json").read_text(encoding="utf-8"))
    for sid, e in data.get("sheets", data).items():
        p = e.get("place")
        if p:
            assert p.get("evidence"), f"{sid}: place without evidence"
            assert p.get("approximate") is True, f"{sid}: coordinates presented as exact"
