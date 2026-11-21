"""Pure-parsing tests for tools/world/search_parismusees.py (inline fixtures, no network)."""
# ruff: noqa: E501

from __future__ import annotations

from tools.world import search_parismusees as sp

SEARCH_HTML = """
<div>68 résultats trouvés</div>
<div class="item-list"><ul><li class="pager-current pager-item first">1</li>
<li class="pager-item last"><a href="/fr/recherche/AND/auteur/Benoist%2C%20Philippe?page=2">2</a></li></ul></div>
<article id="node-1048782" class="node" about="/fr/maison-de-balzac/oeuvres/la-halle">
<a href="/x"><h3>La Halle et la fontaine.</h3></a>
<div class="auteur-nom">Benoist, Philippe (1813 - 1905)</div>
<div class="auteur-nom">Hoffbauer, Fédor (1839 - 1922)</div>
<div class="field field-name-field-musee"><div class="field-items"><div class="field-item even">Maison de Balzac</div></div></div>
</article>
<article id="node-9" class="node" about="/fr/musee-carnavalet/oeuvres/autre">
<h3>Autre</h3><div class="auteur-nom">Benoist, Félix (1818 - 1896)</div>
</article>
"""

RECORD_HTML = """
<link rel="canonical" href="https://www.parismuseescollections.paris.fr/fr/musee-carnavalet/oeuvres/vues-de-paris-11" />
<link rel="shortlink" href="https://www.parismuseescollections.paris.fr/fr/node/647240" />
<h1>Vues de Paris./ (11)./ Le Boulevard des Italiens.</h1>
<a href="https://creativecommons.org/publicdomain/zero/1.0/" class="licence cc0">CC0</a>
<span class="droits">CC0 Paris Musées / Musée Carnavalet</span>
<section id="infos-secondaires-detail"><h2>Informations détaillées</h2>
<div class="field-label">Auteur(s)<span>:&nbsp;</span></div><div class="field-items">
<div class="auteur-complet"><a href="/a">Benoist, Philippe</a> (Genève, en 1813 - en 1905), dessinateur-lithographe</div>
<div class="auteur-complet"><a href="/b">Bry, Auguste</a> (1805 - 1880), imprimeur-lithographe</div>
<div class="auteur-complet"><a href="/c">Gihaut Frères</a>, editeur</div></div>
<div class="field autres-titres"><div class="field-label">Autre titre :</div>
<div class="field-items titres">Couvent des Chartreux. / B. (Titre de la série)</div></div>
<div class="field-label">Type(s) d'objet(s)<span>:</span></div><div class="field-items"><a href="/fr/recherche/type/oeuvre/ET/types-objet/estampe-1">Estampe</a></div>
<div class="field-label">Dénomination(s)<span>:</span></div><div class="field-items"><a href="/fr/recherche/type/oeuvre/ET/denominations/x-2">Illustration de livre</a></div>
<div class="field-label">Matériaux et techniques<span>:</span></div><div class="field-items"><a href="/fr/recherche/type/oeuvre/ET/materiaux-technique/litho-3">Lithographie</a></div>
<div class="field-label">Institution<span>:&nbsp;</span></div><div class="field-items">Musée Carnavalet, Histoire de Paris</div>
<div class="field-label">Numéro d'inventaire<span>:</span></div><div class="field-items">CARGTOP029820</div>
<div class="field-label">IIIF Manifest: </div>
<div class="field-items"><a href="https://apicollections.parismusees.paris.fr/iiif/320291197/manifest">m</a></div>
</section>
"""

MANIFEST = {
    "label": "x",
    "metadata": [{"label": "Auteur", "value": ["Benoist, Philippe"]}],
    "sequences": [
        {
            "canvases": [
                {
                    "@id": "c1",
                    "width": 2895,
                    "height": 2160,
                    "metadata": [
                        {"label": "Droits", "value": "CC0 Paris Musées"},
                        {"label": "Copyright", "value": "https://creativecommons.org/publicdomain/zero/1.0/"},
                    ],
                    "images": [{"resource": {"@id": "https://example.invalid/i.jpg"}}],
                }
            ]
        }
    ],
}


def test_search_page_total_cards_pager():
    r = sp.parse_search_page(SEARCH_HTML)
    assert r["total"] == 68
    assert r["max_page"] == 2
    assert [c["node"] for c in r["cards"]] == ["1048782", "9"]
    assert r["cards"][0]["authors"][0] == "Benoist, Philippe (1813 - 1905)"
    assert r["cards"][0]["museum"] == "Maison de Balzac"


def test_search_page_without_total():
    assert sp.parse_search_page("<html></html>") == {"total": None, "cards": [], "max_page": 1}


def test_split_author_line_variants():
    a = sp.split_author_line("Benoist, Philippe (Genève, en 1813 - en 1905), dessinateur-lithographe")
    assert a == {
        "name": "Benoist, Philippe",
        "life_data": "Genève, en 1813 - en 1905",
        "role_as_stated": "dessinateur-lithographe",
    }
    assert sp.split_author_line("Gihaut Frères, editeur")["role_as_stated"] == "editeur"
    bare = sp.split_author_line("Benoist, Philippe")
    assert bare["name"] == "Benoist, Philippe" and bare["role_as_stated"] is None


def test_normalise_role():
    assert sp.normalise_role("dessinateur-lithographe") == ("designer", ["lithographer"])
    assert sp.normalise_role("imprimeur-lithographe") == ("printer", ["lithographer"])
    assert sp.normalise_role("editeur") == ("publisher", [])
    assert sp.normalise_role(None) == ("unspecified", [])
    assert sp.normalise_role("mystère") == ("unspecified", [])


def test_parse_record_page():
    p = sp.parse_record_page(RECORD_HTML)
    assert p["node"] == "647240"
    assert p["title"].startswith("Vues de Paris")
    assert p["manifest"].endswith("/iiif/320291197/manifest")
    assert p["inventory"] == "CARGTOP029820"
    assert p["techniques"] == ["Lithographie"]
    assert [a["role_as_stated"] for a in p["authors"]] == [
        "dessinateur-lithographe",
        "imprimeur-lithographe",
        "editeur",
    ]
    assert sp.series_title_on_sheet(p["other_titles"]).startswith("Couvent des Chartreux")


def test_parse_manifest_and_rights():
    m = sp.parse_manifest(MANIFEST)
    cv = m["canvases"][0]
    assert (cv["width"], cv["height"]) == (2895, 2160)
    assert sp.rights_from_canvases(m["canvases"])[0] == "open_confirmed"


def test_rights_require_every_canvas_cc0():
    good = {"droits": "CC0 x", "copyright": "https://creativecommons.org/publicdomain/zero/1.0/"}
    bad = {"droits": "Paris Musées", "copyright": None}
    assert sp.rights_from_canvases([good, bad])[0] == "rights_pending"
    assert sp.rights_from_canvases([])[0] == "unknown"
    assert sp.rights_from_canvases([{"droits": "© Musée, tous droits réservés", "copyright": None}])[0] == "link_only"


def test_page_cc0_label_alone_is_not_open_confirmed():
    page = sp.parse_record_page(RECORD_HTML)
    page["manifest"] = None
    rec = sp.build_record({"node": "1"}, page, None, ["q"], {"iiif": set(), "url_slug": set(), "node": set()})
    assert rec["rights_status"] == "unknown"
    assert rec["image_width"] is None and rec["image_height"] is None
    assert "not confirmed by a manifest" in rec["rights_statement"]


def test_artist_classification_never_conflates():
    def auth(*names):
        return [
            {"name": n.split("|")[0], "life_data": (n.split("|") + [None])[1], "role_as_stated": None} for n in names
        ]

    assert sp.classify_artist(auth("Benoist, Philippe|1813 - 1905"))[0] == "philippe-benoist"
    assert sp.classify_artist(auth("Benoist, Félix|1818 - 1896"))[0] == "felix-benoist"
    assert sp.classify_artist(auth("Benoist, Philippe|1813", "Benoist, Félix|1818"))[0] == "uncertain-benoist"
    assert sp.classify_artist(auth("Benoist, Guillaume Philippe"))[0] == "uncertain-benoist"
    assert sp.classify_artist(auth("Benoist, Antoine"))[0] == "uncertain-benoist"
    assert sp.classify_artist(auth("Ciceri, Eugène"))[0] == "other"
    assert sp.classify_artist(auth("Benoist, Philippe"))[1] == "medium"


def test_series_plate_and_duplicate_hint():
    assert sp.detect_series("Paris dans sa splendeur./ 51./ Parc de Monceaux.", []) == ("Paris dans sa splendeur", "51")
    assert sp.detect_series("Vues de Paris (11) / Le Boulevard", []) == ("Vues de Paris", "11")
    assert sp.detect_series("Château des Tuileries.", []) == (None, None)
    a = sp.make_duplicate_hint("Palais du Luxembourg. / Côté jardin.", None, None)
    b = sp.make_duplicate_hint("PALAIS DU LUXEMBOURG / Côté jardin", None, None)
    assert a == b
    assert sp.make_duplicate_hint(None, None, None) is None


def test_known_matching_and_grouping():
    known = {"iiif": {"320291197"}, "url_slug": set(), "node": set()}
    page = sp.parse_record_page(RECORD_HTML)
    r1 = sp.build_record({"node": "647240"}, page, sp.parse_manifest(MANIFEST), ["author:Benoist, Philippe"], known)
    assert r1["known_before"] is True
    assert r1["artist_id"] == "philippe-benoist" and r1["attribution_confidence"] == "high"
    assert r1["participants"][0]["role_normalized_also"] == ["lithographer"]
    assert r1["image_width"] == 2895
    r2 = dict(r1, record_id="parismusees:1", known_before=False)
    g = sp.group_duplicates([r1, r2])
    assert g["unique_compositions"] == 1 and g["groups"][0]["impressions"] == 2
    assert r2["impression_note"]
