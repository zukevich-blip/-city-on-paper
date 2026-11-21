"""Parsing-only tests for tools/world/search_bnf_europeana_ia.py (inline fixtures, no network)."""

from tools.world import search_bnf_europeana_ia as s

SRU_XML = """<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/"
  xmlns:mxc="info:lc/xmlns/marcxchange-v2">
<srw:version>1.2</srw:version>
<srw:numberOfRecords>59</srw:numberOfRecords>
<srw:records>
<srw:record><srw:recordData>
<mxc:record format="UNIMARC" id="ark:/12148/cb46541666t" type="Bibliographic">
<mxc:leader>     ckm  22        450 </mxc:leader>
<mxc:datafield tag="200" ind1="1" ind2=" ">
<mxc:subfield code="a">Le Château d'Eau</mxc:subfield>
<mxc:subfield code="i">Marché aux Fleurs</mxc:subfield>
<mxc:subfield code="e">[estampe]</mxc:subfield>
<mxc:subfield code="f">Hoffbauer del.</mxc:subfield>
<mxc:subfield code="g">Ph. Benoist del. et lith.</mxc:subfield>
</mxc:datafield>
<mxc:datafield tag="214" ind1=" " ind2="0">
<mxc:subfield code="a">Paris</mxc:subfield><mxc:subfield code="d">1838</mxc:subfield>
</mxc:datafield>
<mxc:datafield tag="215" ind1=" " ind2=" ">
<mxc:subfield code="a">1 estampe</mxc:subfield><mxc:subfield code="c">lithographie</mxc:subfield>
</mxc:datafield>
<mxc:datafield tag="607" ind1=" " ind2=" ">
<mxc:subfield code="a">Paris (France)</mxc:subfield><mxc:subfield code="x">Place de la République</mxc:subfield>
</mxc:datafield>
<mxc:datafield tag="700" ind1=" " ind2="|">
<mxc:subfield code="3">14962134</mxc:subfield><mxc:subfield code="a">Benoist</mxc:subfield>
<mxc:subfield code="b">Philippe</mxc:subfield><mxc:subfield code="f">1813-1905</mxc:subfield>
<mxc:subfield code="4">510</mxc:subfield>
</mxc:datafield>
<mxc:datafield tag="930" ind1=" " ind2=" ">
<mxc:subfield code="a">VA-290 (5)-FOL</mxc:subfield>
<mxc:subfield code="c">Richelieu - Estampes et photographie - Magasin</mxc:subfield>
</mxc:datafield>
</mxc:record></srw:recordData></srw:record>
<srw:record><srw:recordData>
<mxc:record format="UNIMARC" id="ark:/12148/cb11111111x" type="Bibliographic">
<mxc:leader>     cam  22        450 </mxc:leader>
<mxc:datafield tag="200" ind1="1" ind2=" ">
<mxc:subfield code="a">Angers pittoresque</mxc:subfield>
<mxc:subfield code="f">Felix Benoist</mxc:subfield>
</mxc:datafield>
<mxc:datafield tag="700" ind1=" " ind2="|">
<mxc:subfield code="3">11891235</mxc:subfield><mxc:subfield code="a">Benoist</mxc:subfield>
<mxc:subfield code="b">Félix</mxc:subfield><mxc:subfield code="f">1818-1896</mxc:subfield>
<mxc:subfield code="4">070</mxc:subfield>
</mxc:datafield>
</mxc:record></srw:recordData></srw:record>
<srw:record><srw:recordData>
<mxc:record format="UNIMARC" id="ark:/12148/cb22222222x" type="Bibliographic">
<mxc:leader>     cam  22        450 </mxc:leader>
<mxc:datafield tag="200" ind1="1" ind2=" ">
<mxc:subfield code="a">Histoire d'un autre Benoist</mxc:subfield>
</mxc:datafield>
<mxc:datafield tag="700" ind1=" " ind2="|">
<mxc:subfield code="3">99999999</mxc:subfield><mxc:subfield code="a">Benoist</mxc:subfield>
<mxc:subfield code="b">Charles</mxc:subfield>
</mxc:datafield>
</mxc:record></srw:recordData></srw:record>
</srw:records>
<srw:nextRecordPosition>4</srw:nextRecordPosition>
</srw:searchRetrieveResponse>"""


def test_classify_keeps_philippe_felix_and_others_apart():
    assert s.classify_benoist("[estampe] / Ph. Benoist del. et lith.")[0] == "philippe-benoist"
    assert s.classify_benoist("Benoist, Philippe (1813-1905). Dessinateur")[0] == "philippe-benoist"
    assert s.classify_benoist("Contes de Bretagne / [lithogr. de] Félix Benoist")[0] == "felix-benoist"
    assert s.classify_benoist("Benoist, Félix (1818-1896)")[0] == "felix-benoist"
    assert s.classify_benoist("Guillaume-Philippe Benoist, graveur")[0] == "other"
    assert s.classify_benoist("Antoine Benoist (1721-1770)")[0] == "other"
    assert s.classify_benoist("Benoist")[0] == "uncertain-benoist"
    assert s.classify_benoist("Philippe Benoist et Félix Benoist")[0] == "uncertain-benoist"
    assert s.classify_benoist("Rien à voir")[0] is None
    # video credit 'Benoîst Philippe, réal' is a modern namesake, not the lithographer
    assert s.classify_benoist("La combustion des gaz / Benoîst Philippe, réal")[0] != "philippe-benoist"


def test_norm_role_and_statement_roles():
    assert s.norm_role("Dessinateur") == "designer"
    assert s.norm_role("Drawer") == "designer"
    assert s.norm_role("Lithographe") == "lithographer"
    assert s.norm_role("Imprimeur") == "printer"
    assert s.norm_role(None) == "unspecified"
    assert s.role_set_from_statement("Ph. Benoist del. et lith.") == ["designer", "lithographer"]


def test_rights_status_never_treats_no_known_restrictions_as_open():
    assert s.rights_status("http://rightsstatements.org/vocab/NoC-OKLR/1.0/") == "link_only"
    assert s.rights_status("No known restrictions on publication") == "link_only"
    assert s.rights_status("https://creativecommons.org/publicdomain/zero/1.0/") == "open_confirmed"
    assert s.rights_status("http://creativecommons.org/publicdomain/mark/1.0/deed.de") == "open_confirmed"
    assert s.rights_status("https://creativecommons.org/licenses/by-sa/4.0/") == "open_confirmed"
    assert s.rights_status("https://creativecommons.org/licenses/by-nc/4.0/") == "link_only"
    assert s.rights_status(None) == "unknown"


def test_duplicate_hint_groups_impressions():
    a = s.duplicate_hint("La Madeleine : [estampe] / Ph. Benoist del.", "Paris dans sa splendeur", None)
    b = s.duplicate_hint("La Madeleine [dessin]", "Paris dans sa splendeur", None)
    c = s.duplicate_hint("Le Louvre", "Paris dans sa splendeur", None)
    assert a == b
    assert a != c
    assert s.plate_of("Palais-Royal, planche 12") == "12"
    assert s.series_of("Paris dans sa splendeur : monuments") == "Paris dans sa splendeur"
    assert s.series_of("España artística y monumental, vol. 2") == "España artística y monumental"


def test_parse_bnf_sru_and_records():
    total, nxt, recs, diag = s.parse_bnf_sru(SRU_XML)
    assert (total, nxt, len(recs), diag) == (59, 4, 3, None)
    r0, why0 = s.parse_bnf_record(recs[0], "q")
    assert why0 is None
    assert r0["record_id"] == "bnf:cb46541666t"
    assert r0["artist_id"] == "philippe-benoist"
    assert r0["attribution_confidence"] == "high"
    assert r0["object_type"] == "print"
    assert r0["date_as_stated"] == "1838"
    assert r0["record_url"] == "https://catalogue.bnf.fr/ark:/12148/cb46541666t"
    assert r0["rights_status"] == "unknown" and r0["image_url"] is None
    assert r0["participants"][0]["role_as_stated"].endswith("Ph. Benoist del. et lith.")
    assert r0["participants"][0]["role_normalized"] == "designer"
    assert "VA-290" in r0["accession"]
    assert r0["city"] == "Paris (France)"
    r1, _ = s.parse_bnf_record(recs[1])
    assert r1["artist_id"] == "felix-benoist" and r1["object_type"] == "book"
    r2, why2 = s.parse_bnf_record(recs[2])
    assert r2 is None and why2 == "other_benoist"


def test_parse_bnf_sru_diagnostic():
    xml = (
        '<?xml version="1.0"?><srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/" '
        'xmlns:sd="http://www.loc.gov/zing/srw/diagnostic/"><srw:numberOfRecords>0</srw:numberOfRecords>'
        "<srw:diagnostics><sd:diagnostic><sd:message>Index non supporté</sd:message></sd:diagnostic>"
        "</srw:diagnostics></srw:searchRetrieveResponse>"
    )
    total, nxt, recs, diag = s.parse_bnf_sru(xml)
    assert (total, nxt, recs, diag) == (0, None, [], "Index non supporté")


EUROPEANA_ITEM = {
    "id": "/9200518/ark__12148_btv1b77429702",
    "title": ["Reims. [Statue] : [dessin] / [Philippe Benoist]", "Reims. [Statue] : [dessin] / [Philippe Benoist]"],
    "dcCreator": [
        "Benoist, Philippe (1813-1905). Dessinateur",
        "Benoist, Philippe (1813-1905). Drawer",
        "Benoist, Philippe (1813-1905). Dessinateur",
    ],
    "dataProvider": ["National Library of France"],
    "edmIsShownAt": ["http://gallica.bnf.fr/ark:/12148/btv1b77429702"],
    "edmIsShownBy": ["http://gallica.bnf.fr/iiif/ark:/12148/btv1b77429702/f1/full/512,/0/native.jpg"],
    "rights": ["http://rightsstatements.org/vocab/NoC-OKLR/1.0/"],
    "type": "IMAGE",
    "year": ["1842"],
}


def test_parse_europeana_structured_drawing():
    rec, why = s.parse_europeana_item(EUROPEANA_ITEM, "who:x")
    assert why is None
    assert rec["record_id"] == "europeana:/9200518/ark__12148_btv1b77429702"
    assert rec["artist_id"] == "philippe-benoist"
    assert rec["object_type"] == "drawing"
    assert rec["attribution_confidence"] == "high"
    assert rec["rights_status"] == "link_only"
    assert rec["image_url"] is None  # not open_confirmed: no file URL kept
    assert rec["record_url"].startswith("http://gallica.bnf.fr/ark:/12148/btv1b")
    assert {p["role_normalized"] for p in rec["participants"]} == {"designer"}
    assert len(rec["participants"]) == 1  # FR/EN duplicates folded


def test_parse_europeana_felix_and_other_and_open_rights():
    felix = {
        "id": "/x/1",
        "title": ["Angers : vue / F. Benoist"],
        "dcCreator": ["Benoist, Félix (1818-1896). Lithographe"],
        "edmIsShownAt": ["https://example.org/1"],
        "edmIsShownBy": ["https://example.org/1.jpg"],
        "rights": ["https://creativecommons.org/publicdomain/zero/1.0/"],
        "type": "IMAGE",
    }
    rec, _ = s.parse_europeana_item(felix)
    assert rec["artist_id"] == "felix-benoist"
    assert rec["rights_status"] == "open_confirmed" and rec["image_url"] == "https://example.org/1.jpg"
    other = {"id": "/x/2", "title": ["Portrait"], "dcCreator": ["Benoist, Antoine (1721-1770)"]}
    assert s.parse_europeana_item(other) == (None, "other_benoist")
    assert s.parse_europeana_item({"id": "/x/3", "title": ["Nothing"]}) == (None, "no_benoist")
    gp = {"id": "/x/4", "title": ["Gravure"], "dcCreator": ["Benoist, Guillaume-Philippe (1725-1770)"]}
    assert s.parse_europeana_item(gp)[0] is None


def test_parse_europeana_title_statement_only_is_medium_or_low():
    it = {
        "id": "/x/5",
        "title": ["Le Château d'Eau : [estampe] / Ph. Benoist del. et lith."],
        "edmIsShownAt": ["https://example.org/5"],
        "type": "IMAGE",
    }
    rec, _ = s.parse_europeana_item(it)
    assert rec["artist_id"] == "philippe-benoist"
    assert rec["attribution_confidence"] == "low"
    assert rec["participants"][0]["role_as_stated"] == "Ph. Benoist del. et lith."
    assert rec["participants"][0]["role_normalized"] == "designer"


MANIFEST = {
    "license": "http://creativecommons.org/publicdomain/mark/1.0/deed.de",
    "metadata": [
        {"label": "Author", "value": ["Audiganne, Armand; Benoist, Philippe [Ill.]"]},
        {"label": "Date", "value": ["1861"]},
        {"label": "Shelfmark", "value": ["Heidelberg, UB, GF 146 RES::1"]},
    ],
    "sequences": [
        {
            "canvases": [
                {"@id": "https://digi.ub.uni-heidelberg.de/diglit/iiif/audiganne1861bd1/canvas/0001", "label": "a"},
                {
                    "@id": "https://digi.ub.uni-heidelberg.de/diglit/iiif/audiganne1861bd1/canvas/0101",
                    "label": "Planche 16",
                    "width": 2986,
                    "height": 4572,
                    "images": [{"resource": {"@id": "https://digi.ub.uni-heidelberg.de/diglitData/image/x/16.jpg"}}],
                },
            ]
        }
    ],
}


def test_parse_heidelberg_manifest_does_not_assign_plates_to_benoist():
    recs = s.parse_heidelberg_manifest(MANIFEST, "audiganne1861bd1", "Band 1")
    assert [r["object_type"] for r in recs] == ["volume", "page_in_book"]
    vol, plate = recs
    assert vol["artist_id"] == "philippe-benoist" and "NOT a whole-volume" in vol["attribution_note"]
    assert plate["artist_id"] == "uncertain-benoist"
    assert plate["participants"] == []
    assert plate["verification_status"] == "search_hit_only"
    assert plate["plate_number"] == "16"
    assert plate["image_width"] == 2986 and plate["image_height"] == 4572
    assert plate["record_url"].endswith("/audiganne1861bd1/0101")
    assert plate["rights_status"] == "open_confirmed"
    assert plate["series"] == "Paris dans sa splendeur"


def test_parse_ia_item_flags_namesake_and_series_only():
    toscane = {
        "metadata": {
            "identifier": "toscane0000beno",
            "title": "Toscane",
            "creator": "Benoist, Philippe, 1813-approximately 1905",
            "date": "2006-01-01T00:00:00Z",
        }
    }
    rec, _ = s.parse_ia_item(toscane)
    assert rec["artist_id"] == "uncertain-benoist" and "WARNING" in rec["attribution_note"]
    series = {"metadata": {"identifier": "pds1", "title": "Paris dans sa splendeur", "date": "1861"}}
    rec2, _ = s.parse_ia_item(series)
    assert rec2["artist_id"] == "uncertain-benoist" and rec2["attribution_confidence"] == "low"
    assert s.parse_ia_item({"metadata": {"identifier": "z", "title": "Biology", "creator": "Raymond Benoist"}}) == (
        None,
        "other_benoist",
    )
    cooking = {"metadata": {"identifier": "q", "title": "Cooking", "creator": "X"}}
    assert s.parse_ia_item(cooking) == (None, "no_benoist")


def test_parse_commons_pages():
    payload = {
        "query": {
            "pages": {
                "1": {
                    "title": "File:Rome dans sa grandeur - Ph. Benoist.jpg",
                    "imageinfo": [
                        {
                            "url": "https://upload.wikimedia.org/x.jpg",
                            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Rome.jpg",
                            "width": 1200,
                            "height": 800,
                            "extmetadata": {
                                "LicenseShortName": {"value": "Public domain"},
                                "Artist": {"value": "<a>Philippe Benoist</a>"},
                            },
                        }
                    ],
                }
            }
        }
    }
    recs = s.parse_commons_pages(payload, "Philippe Benoist", "philippe-benoist")
    assert recs[0]["record_id"].startswith("commons:File:")
    assert recs[0]["rights_status"] == "open_confirmed"
    assert recs[0]["image_width"] == 1200
    assert recs[0]["attribution_confidence"] == "low"
    assert recs[0]["series"] == "Rome dans sa grandeur"


def test_known_keys_and_marking():
    text = '{"a": "http://gallica.bnf.fr/ark:/12148/btv1b7741059m", "id": "europeana/9200518/ark__12148_btv1b77429702"}'
    keys = s.extract_keys(text)
    assert {"btv1b7741059m", "btv1b77429702"} <= keys
    rec, _ = s.parse_europeana_item(EUROPEANA_ITEM)
    new = {"record_id": "bnf:cb1", "record_url": "https://catalogue.bnf.fr/ark:/12148/cb1", "accession": None}
    assert s.mark_known([rec, new], keys) == 1
    assert rec["known_in_repo"] is True and rec["known_match"] == "btv1b77429702"
    assert new["known_in_repo"] is False


def test_summarize_new_unique_counts_each_duplicate_group_once():
    def mk(rid, hint, known):
        return {
            "record_id": rid,
            "duplicate_hint": hint,
            "known_in_repo": known,
            "artist_id": "philippe-benoist",
            "object_type": "print",
        }

    recs = [mk("bnf:1", "a||", False), mk("europeana:1", "a||", False), mk("europeana:2", "b||", True)]
    per = {}
    s.summarize(recs, per)
    assert per["bnf"]["summary"]["new_unique"] == 1
    assert per["europeana"]["summary"]["new_unique"] == 0
    assert per["europeana"]["summary"]["known_in_repo"] == 1
    assert s.group_duplicates(recs)["a||"] == ["bnf:1", "europeana:1"]


def test_authority_count_and_make_record_hides_non_open_image():
    assert s.bnf_authority_count("... auteur (51) Voir toutes ...") == 51
    r = s.make_record(
        record_id="x:1",
        artist_id="philippe-benoist",
        original_title="T",
        record_url="https://e/1",
        image_url="https://e/1.jpg",
        rights_statement="No known restrictions",
    )
    assert r["image_url"] is None and r["rights_status"] == "link_only"


def _bnf_rec(title, stmt, date, leader="     cam  22        450 "):
    xml = (
        '<mxc:record xmlns:mxc="info:lc/xmlns/marcxchange-v2" id="ark:/12148/cbX" type="Bibliographic">'
        f"<mxc:leader>{leader}</mxc:leader>"
        f'<mxc:datafield tag="200" ind1="1" ind2=" "><mxc:subfield code="a">{title}</mxc:subfield>'
        f'<mxc:subfield code="f">{stmt}</mxc:subfield></mxc:datafield>'
        f'<mxc:datafield tag="214" ind1=" " ind2="0"><mxc:subfield code="d">{date}</mxc:subfield></mxc:datafield>'
        "</mxc:record>"
    )
    import xml.etree.ElementTree as ET

    return ET.fromstring(xml)


def test_bnf_text_only_matches_are_filtered_to_nineteenth_century_or_graphic():
    modern, why = s.parse_bnf_record(_bnf_rec("Dahomey 1930", "Philippe Benoist, réal.", "1996"))
    assert modern is None and why == "text_only_not_nineteenth_century"
    old, why = s.parse_bnf_record(_bnf_rec("Vue de Rouen", "Ph. Benoist del.", "1850"))
    assert why is None and old["artist_id"] == "philippe-benoist" and old["attribution_confidence"] == "medium"
    surname, why = s.parse_bnf_record(_bnf_rec("Dico", "scénario, Benoist Simmat", "2010"))
    assert surname is None
