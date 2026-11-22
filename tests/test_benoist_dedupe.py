"""Pure tests for tools.world.benoist_dedupe: fixtures only, no network, no repository data."""

from __future__ import annotations

from tools.world import benoist_dedupe as d


def rec(rid, title, artist="philippe-benoist", **kw):
    base = {
        "record_id": rid,
        "artist_id": artist,
        "original_title": title,
        "institution": kw.pop("institution", "Musée X"),
        "participants": kw.pop("participants", []),
    }
    base.update(kw)
    return base


def test_title_tokens_drop_statement_of_responsibility_but_keep_series_subtitle():
    bnf = d.title_tokens("Senlis. Détails [de balustrades] pris dans la cathédrale : [dessin] / [Philippe Benoist]")
    assert "benoist" not in bnf and "senli" in bnf
    a = d.title_tokens("Les grands aspects du nouveau Paris / Nouvelle église de la Trinité / Chaussée d'Antin.")
    b = d.title_tokens("Les grands aspects du nouveau Paris / Nouvel Opéra. / Façade principale")
    assert a != b and "trinite" in a and "opera" in b


def test_series_phrase_and_volume_marker_are_not_title_tokens():
    assert d.title_tokens("Paris dans sa Splendeur (volume I)") == frozenset()
    assert d.volume_of("Paris dans sa Splendeur (volume II)") == "ii"


def test_philippe_and_felix_never_match_even_with_identical_titles():
    a = d.features(rec("a:1", "Palais et jardin du Luxembourg vue générale", artist="philippe-benoist"))
    b = d.features(rec("b:1", "Palais et jardin du Luxembourg vue générale", artist="felix-benoist"))
    assert d.compare(a, b) is None


def test_uncertain_pair_with_known_artist_is_capped_at_medium():
    a = d.features(rec("a:1", "Hôtel de Ville cour d'honneur façade", artist="felix-benoist", institution="BnF"))
    b = d.features(rec("b:1", "Hôtel de Ville cour d'honneur façade", artist="uncertain-benoist", institution="BnF"))
    assert d.compare(a, b)["confidence"] == "medium"


def test_guillaume_philippe_and_antoine_benoist_are_excluded():
    g = rec("a:1", "Vue de la place", participants=[{"name": "Benoist, Guillaume Philippe"}])
    n = rec("b:1", "Vue de la place", participants=[{"name": "Antoine Benoist"}])
    ok = rec("c:1", "Vue de la place")
    assert d.features(g)["excluded"] and d.features(n)["excluded"] and not d.features(ok)["excluded"]
    assert d.compare(d.features(g), d.features(ok)) is None


def test_same_ark_is_high_across_europeana_and_gallica():
    a = d.features(rec("europeana:/9200518/ark__12148_btv1b53026653k", "La Madeleine intérieur"))
    b = d.features(rec("gallica:btv1b53026653k", "Madeleine"))
    res = d.compare(a, b)
    assert res["confidence"] == "high" and "btv1b53026653k" in res["evidence"][0]


def test_exact_distinctive_title_same_institution_is_high():
    a = d.features(rec("bnf:cb1", "Palais de l'Élysée (Façade sur le Parc) [estampe]", institution="BnF"))
    b = d.features(
        rec("eu:1", "Palais de l'Élysée (Façade sur le Parc) : [estampe]", institution="National Library of France")
    )
    assert d.compare(a, b)["confidence"] == "high"


def test_cross_institution_exact_title_without_corroboration_is_only_medium():
    a = d.features(rec("pm:1", "Cirque de l'Impératrice aux Champs-Élysées", institution="Carnavalet"))
    b = d.features(rec("eu:1", "Cirque de l'Impératrice aux Champs Élysées : [estampe]", institution="BnF"))
    assert d.compare(a, b)["confidence"] == "medium"


def test_conflicts_block_every_match():
    base = "Église de la Madeleine façade principale"
    a = d.features(rec("a:1", base, series="Vues de Paris", plate_number="7"))
    assert d.compare(a, d.features(rec("b:1", base, series="Vues de Paris", plate_number="8"))) is None
    assert d.compare(a, d.features(rec("c:1", base, series="Promenade dans Paris"))) is None
    early = d.features(rec("d:1", base, date_as_stated="1830"))
    late = d.features(rec("e:1", base, date_as_stated="1875"))
    assert d.compare(early, late) is None
    assert d.compare(d.features(rec("f:1", "Cathédrale vue intérieur nef chœur")),
                     d.features(rec("g:1", "Cathédrale vue extérieur nef chœur"))) is None


def test_different_volumes_do_not_match():
    a = d.features(rec("a:1", "Paris dans sa splendeur Histoire volume I grand carrousel Louis", object_type="print"))
    b = d.features(rec("b:1", "Paris dans sa splendeur Histoire volume II grand carrousel Louis", object_type="print"))
    assert d.compare(a, b) is None


def test_books_are_capped_at_medium():
    t = "Nice et Savoie sites pittoresques monuments description histoire"
    a = d.features(rec("bnf:cb1", t, institution="BnF", object_type="book"))
    b = d.features(rec("bnf:cb2", t, institution="BnF", object_type="book"))
    assert d.compare(a, b)["confidence"] == "medium"


def test_same_institution_with_different_wording_is_not_proposed():
    a = d.features(rec("a:1", "Le Louvre et la Seine vue prise du Pont-Neuf", institution="BnF"))
    b = d.features(rec("b:1", "Vue de la Seine prise du Louvre la Cité et le Pont-Neuf", institution="BnF"))
    assert d.compare(a, b) is None


def test_plate_placeholders_are_excluded_from_grouping():
    p = rec("heidelberg:audiganne1861bd3/0100", "Planche 71 (plate in Paris dans sa splendeur, Band 3)")
    assert d.features(p)["excluded"]


def test_propose_groups_counts_strict_high_and_likely_and_never_auto_merges():
    records = [
        rec("bnf:cb1", "Palais de l'Élysée (Façade sur le Parc) [estampe]", institution="BnF", duplicate_hint="e|"),
        rec("eu:1", "Palais de l'Élysée (Façade sur le Parc) : [estampe]", institution="National Library of France",
            duplicate_hint="e2|"),
        rec("pm:1", "Cirque de l'Impératrice aux Champs-Élysées", institution="Carnavalet", duplicate_hint="c1|"),
        rec("eu:2", "Cirque de l'Impératrice aux Champs Élysées : [estampe]", institution="BnF", duplicate_hint="c2|"),
        rec("x:1", "Totally unrelated mountain landscape sketch", institution="Y", duplicate_hint="u|"),
        rec("rij:1", "Palais de l'Élysée (Façade sur le Parc)", artist="felix-benoist", institution="Rijksmuseum",
            duplicate_hint="r|"),
    ]
    out = d.propose_groups(records)
    s = out["summary"]
    assert s["records"] == 6
    assert s["unique_works_strict"] == 6
    assert s["unique_works_after_high"] == 5  # Élysée BnF + Europeana (same institution, exact title)
    assert s["unique_works_likely"] == 4  # + the Cirque pair (cross-institution, medium)
    assert [g["confidence"] for g in out["high_groups"]] == ["high"]
    assert [g["confidence"] for g in out["medium_groups"]] == ["medium"]
    assert all(g["auto_merge"] is False for g in out["high_groups"] + out["medium_groups"])
    all_members = {m["record_id"] for g in out["high_groups"] + out["medium_groups"] for m in g["members"]}
    assert "x:1" not in all_members


def test_medium_groups_use_complete_linkage_not_chains():
    # a~b and b~c are similar, a~c is not: they must not collapse into one group.
    a = rec("a:1", "Eglise saint sulpice parvis fontaine nord", institution="A")
    b = rec("b:1", "Eglise saint sulpice parvis fontaine", institution="B")
    c = rec("c:1", "Eglise saint sulpice parvis fontaine nord est", institution="C")
    out = d.propose_groups([a, b, c])
    feats = {r["record_id"]: d.features(r) for r in (a, b, c)}
    for g in out["high_groups"] + out["medium_groups"]:
        ids = [m["record_id"] for m in g["members"]]
        for i, x in enumerate(ids):
            for y in ids[i + 1 :]:
                assert d.compare(feats[x], feats[y]) is not None  # every pair in a group is itself supported


def test_strict_key_matches_registry_rule():
    from tools.world.build_benoist_registry import group_key

    r = {"artist_id": "philippe-benoist", "duplicate_hint": "x|y|3", "original_title": "T"}
    assert d.strict_key(r) == group_key(r)
    r2 = {"artist_id": "felix-benoist", "original_title": "Vues de Paris Notre-Dame (3)", "series": "S",
          "plate_number": 4}
    assert d.strict_key(r2) == group_key(r2)


def test_unique_by_record_id_keeps_first():
    rows = [{"record_id": "a", "n": 1}, {"record_id": "a", "n": 2}, {"record_id": "b", "n": 3}]
    assert [r["n"] for r in d.unique_by_record_id(rows)] == [1, 3]
