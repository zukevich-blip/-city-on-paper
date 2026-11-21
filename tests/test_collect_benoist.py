from tools.world import collect_benoist as cb


def test_is_philippe_benoist():
    assert cb.is_philippe_benoist("Benoist, Philippe (1813-1905). Dessinateur")
    assert cb.is_philippe_benoist("Ph. Benoist del. ; Imp. Lemercier")
    assert cb.is_philippe_benoist("Philippe (1813) Benoist")
    assert not cb.is_philippe_benoist("Guillaume Philippe Benoist")
    assert not cb.is_philippe_benoist("Benoist, J. L. (Production), 1801-1815")
    assert not cb.is_philippe_benoist("Benoist-Ginocchio Store")
    assert not cb.is_philippe_benoist("")


def test_rights_class():
    assert cb.rights_class("No known restrictions on publication.") == "open"
    assert cb.rights_class("http://creativecommons.org/publicdomain/zero/1.0/") == "open"
    assert cb.rights_class("http://creativecommons.org/licenses/by-nc-sa/4.0/") == "link"
    assert cb.rights_class("http://rightsstatements.org/vocab/NoC-OKLR/1.0/") == "link"
    assert cb.rights_class("http://rightsstatements.org/vocab/InC/1.0/") == "link"
    assert cb.rights_class(None) == "link"


def test_norm_url_and_known():
    assert cb.norm_url("http://www.Loc.gov/pictures/item/1/") == cb.norm_url("https://loc.gov/pictures/item/1")
    rec = cb.make_record(source="x", id="a", record_url="https://loc.gov/pictures/item/1/")
    assert cb.mark_known([rec], {"urls": {"loc.gov/pictures/item/1"}, "ids": set()}) == 1
    assert rec["known"] and rec["known_match"] == "record_url"


def test_image_only_with_open_rights():
    closed = cb.make_record(source="x", id="1", image_url="http://i/1.jpg", rights_statement="InC")
    assert closed["image_url"] is None
    opened = cb.make_record(source="x", id="2", image_url="http://i/2.jpg", rights_statement="CC0 1.0")
    assert opened["image_url"] == "http://i/2.jpg"


def test_parse_europeana():
    item = {
        "id": "/9200518/ark__x", "title": ["Tour de St Ouen : [dessin]"],
        "dcCreator": ["Benoist, Philippe (1813-1905). Dessinateur", "Benoist, Philippe (1813-1905). Drawer"],
        "dataProvider": ["National Library of France"], "year": ["1842"],
        "rights": ["http://rightsstatements.org/vocab/NoC-OKLR/1.0/"],
        "edmIsShownAt": ["http://gallica.bnf.fr/ark:/12148/x"], "edmIsShownBy": ["http://img/x.jpg"],
    }
    r = cb.parse_europeana_item(item)
    assert r["kind"] == "drawing" and r["rights_class"] == "link" and r["image_url"] is None
    assert r["creators"][0]["role_as_stated"] == "Dessinateur"
    other = {"id": "z", "title": ["Portrait"], "dcCreator": ["Guillaume Philippe Benoist"]}
    assert cb.parse_europeana_item(other) is None


def test_parse_europeana_free_text():
    item = {"id": "/542/i", "title": ["Das Münster"], "rights": ["http://creativecommons.org/licenses/by/3.0/"],
            "dcCreator": ["Gezeichnet von Chapuy; Lithografie von Philippe Benoist (1813-1905); Druck von Lemercier."],
            "edmIsShownBy": ["http://img/m.jpg"]}
    r = cb.parse_europeana_item(item)
    assert r["attribution_confidence"] == "medium"
    assert any("Lithografie von Philippe Benoist" in c["role_as_stated"] for c in r["creators"])
    assert r["image_url"] == "http://img/m.jpg"


def test_parse_loc_item():
    payload = {"item": {
        "title": "Paris. Jardin du Palais Royal", "link": "https://www.loc.gov/pictures/item/2016652451/",
        "stmt_of_responsibility": "Ph. Benoist del. ; Imp. Lemercier, Paris.",
        "related_names": [{"title": "Benoist, Philippe, 1813-approximately 1905", "role": "artist"}],
        "created_published_date": "[between 1845 and 1860]",
        "rights_information": "No known restrictions on publication.",
        "service_medium": "https://cdn.loc.gov/x.jpg", "reproduction_number": "LC-DIG-pga-14314",
        "notes": [{"note": "[Plate] 6."}], "mediums": [{"medium": "hand-colored lithograph"}],
    }}
    r = cb.parse_loc_item(payload)
    assert r["id"] == "loc-2016652451" and r["rights_class"] == "open" and r["image_url"]
    assert r["creators"][0]["role_as_stated"] == "artist"
    assert cb.parse_loc_item({"item": {"title": "Benoist house", "related_names": []}}) is None


def test_parse_met_not_public_domain():
    o = {"objectID": 1, "title": "Nouvelles Vues de Paris", "artistDisplayName": "Philippe Benoist",
         "artistRole": "Artist", "objectDate": "ca. 1850", "isPublicDomain": False, "primaryImage": "",
         "objectURL": "https://m/1", "accessionNumber": "50.576.1", "medium": "Lithographs", "creditLine": "Gift"}
    r = cb.parse_met_object(o)
    assert r["rights_class"] == "link" and r["image_url"] is None and r["accession_id"] == "50.576.1"


def test_parse_ia_ambiguous_name():
    d = {"identifier": "abc", "title": "Panorama", "creator": ["Indeitsev", "Benoist et Aubrun", "Lemercier"]}
    r = cb.parse_ia_doc(d)
    assert r["attribution_confidence"] == "medium"
    assert cb.parse_ia_doc({"identifier": "z", "creator": ["Smith"]}) is None


def test_parse_nga():
    obj = {"objectid": "60903", "title": "Paris dans sa Splendeur", "displaydate": "1863", "accessionnum": "1999.1.1",
           "medium": "lithograph", "classification": "Print", "series": "", "volume": "I"}
    roles = [{"role": "artist"}]
    img = {"openaccess": "1", "iiifurl": "https://api.nga.gov/iiif/abc"}
    r = cb.parse_nga(obj, roles, img)
    assert r["rights_class"] == "open" and r["image_url"].startswith("https://api.nga.gov/iiif/abc/")
    r2 = cb.parse_nga(obj, roles, {"openaccess": "0", "iiifurl": "x"})
    assert r2["image_url"] is None and r2["rights_class"] == "link"
