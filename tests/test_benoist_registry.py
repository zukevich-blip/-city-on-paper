from tools.world import build_benoist_registry as reg


def test_philippe_and_felix_are_never_merged():
    assert reg.artist_id(["Benoist, Philippe (1813-1905)"]) == "philippe-benoist"
    assert reg.artist_id(["Félix Benoist"]) == "felix-benoist"
    assert reg.artist_id(["Ph. Benoist"]) == "philippe-benoist"
    assert reg.artist_id(["F. Benoist"]) == "felix-benoist"
    assert reg.artist_id(["Benoist"]) == "uncertain-benoist"
    assert reg.artist_id(["Philippe Benoist", "Félix Benoist"]) == "uncertain-benoist"
    assert reg.artist_id(["x"], "felix-benoist") == "felix-benoist"


def test_same_sheet_from_two_museums_is_one_work_but_two_artists_stay_apart():
    a = {
        "artist_id": "philippe-benoist",
        "original_title": "Vues de Paris (26) / Notre-Dame",
        "series": "Vues de Paris",
    }
    b = {"artist_id": "philippe-benoist", "original_title": "Notre-Dame. / Cathédrale", "series": "Vues de Paris"}
    c = {"artist_id": "felix-benoist", "original_title": "Notre-Dame", "series": "Vues de Paris"}
    assert reg.group_key(a) != reg.group_key(c)
    assert reg.group_key({**a, "duplicate_hint": "paris|notre-dame"}) == reg.group_key(
        {**b, "duplicate_hint": "paris|notre-dame"}
    )


def test_urls_of_one_record_compare_equal():
    assert reg.norm_url("https://www.parismuseescollections.paris.fr/en/node/1?x=2") == reg.norm_url(
        "http://parismuseescollections.paris.fr/node/1/"
    )


def test_public_registry_carries_no_image_files_or_private_paths():
    _, public = reg.build()
    text = str(public)
    assert "private-archive" not in text and "image_url" not in text
    assert all(w["image"] is None or w["image"].startswith("img/benoist/") for w in public["works"])
    s = public["summary"]
    assert s["discovered_records"] >= s["unique_works"] and s["unique_works"] > 0
