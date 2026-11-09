"""GeoNames worldwide 15k extract parser: no network in tests, no false artwork claims."""
import io
import zipfile

import pytest

from tools.maps.import_geonames_major_cities import parse


def fake_zip():
    def line(geoid, name, iso, pop, feature="PPL", lat=45.1, lon=10.2):
        fields = [""] * 19
        fields[0] = str(geoid)
        fields[1], fields[2], fields[4], fields[5] = name, name, str(lat), str(lon)
        fields[6], fields[7], fields[8] = "P", feature, iso
        fields[10] = "02"
        fields[14] = str(pop)
        fields[17], fields[18] = "Europe/Rome", "2026-01-01"
        return "\t".join(fields)

    lines = [
        line(1, "Roma", "IT", 2500000),
        line(2, "Città piccola", "IT", 16000),
        line(3, "Capitale piccola", "VA", 1000, feature="PPLC"),
        line(4, "District X", "IT", 1000000, feature="PPLX"),
        line(5, "Invalid geographic coords", "IT", 300000, lat=95),
        line(1, "Duplicate", "IT", 500000),
    ]
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("cities15000.txt", "\n".join(lines) + "\n")
    return b.getvalue()


def test_major_city_candidates_are_populations_not_verified_atlas_objects():
    doc, summary = parse(fake_zip(), min_population=250000, max_cities=100)
    assert summary["number_of_major_city_candidates"] == 2
    assert summary["countries_with_candidates"] == 2
    assert doc["source_license"] == "CC BY 4.0"
    assert doc["publication_status"].startswith("research_only")
    ids = [r["geonames_id"] for r in doc["cities"]]
    assert ids == [1, 3]
    assert all(r["artworks_verified"] == 0 for r in doc["cities"])
    assert all(r["historic_maps_georeferenced"] == 0 for r in doc["cities"])
    assert doc["cities"][0]["source_url"] == "https://www.geonames.org/1/"


def test_bad_archive_and_bad_thresholds_are_rejected():
    with pytest.raises(ValueError, match="15,000"):
        parse(fake_zip(), min_population=200)
    with pytest.raises(zipfile.BadZipFile):
        parse(b"not a zip file")
    x = io.BytesIO()
    with zipfile.ZipFile(x, "w") as z:
        z.writestr("not-the-expected-file.txt", "x")
    with pytest.raises(ValueError, match="cities15000.txt"):
        parse(x.getvalue())


def test_population_threshold_can_be_raised_without_fake_gps():
    doc, _ = parse(fake_zip(), min_population=3000000, max_cities=100)
    assert [x["name"] for x in doc["cities"]] == ["Capitale piccola"]
    assert all(x["identity_status"].startswith("gazetteer_candidate") for x in doc["cities"])
