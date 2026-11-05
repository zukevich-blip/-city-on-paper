"""Offline unit tests for global archival print finder and licensing."""
import json
from pathlib import Path

from tools.curation.build_world_graphics import classify, label_quality, normalize, source_city_title

ROOT = Path(__file__).resolve().parents[1]


def fixture(rights="Public domain"):
    return {
        "ns": 6, "pageid": 32145, "title": "File:Vista de Buenos Aires - Charles Henri Pellegrini.jpg",
        "imageinfo": [{
            "mime": "image/jpeg", "width": 2000, "height": 1300,
            "url": "https://upload.wikimedia.org/wikipedia/commons/4/40/sample.jpg",
            "thumburl": "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/40/sample.jpg/1000px-sample.jpg",
            "descriptionurl": (
                "https://commons.wikimedia.org/wiki/File:Vista_de_Buenos_Aires_-_Charles_Henri_Pellegrini.jpg"
            ),
            "extmetadata": {
                "LicenseShortName": {"value": rights},
                "Copyrighted": {"value": "False"},
                "Artist": {"value": "Charles Henri Pellegrini"},
            },
        }],
    }


def city(name="Буэнос-Айрес", region="Латинская Америка", q="Buenos Aires lithograph"):
    return {"name": name, "region": region, "country": "Аргентина", "query": q}


def test_licensed_historic_city_artwork_normalization():
    work, rank = normalize(fixture(), city())
    assert work["rights"] == "public_domain_commons"
    assert work["license_label"] == "Public domain"
    assert work["license_url"].startswith("https://commons.wikimedia.org/")
    assert work["maker"] == "Charles Henri Pellegrini"
    assert work["city"] == "Буэнос-Айрес"
    assert work["image"].startswith("https://thumb.wikimedia.org/")
    assert work["original_url"].startswith("https://upload.wikimedia.org/")
    assert work["original_viewpoint_verified"] is False
    assert work["medium"] == "Городская графика"
    assert work["quality_tier"] == "экранное"
    assert rank >= 3


def test_commons_cc0_and_attribution_are_not_confused_with_public_domain():
    image = fixture("CC0")
    image["imageinfo"][0]["extmetadata"]["Copyrighted"]["value"] = "True"
    work, _ = normalize(image, city())
    assert work["rights"] == "cc0"
    assert work["license_url"] == "https://creativecommons.org/publicdomain/zero/1.0/"
    image["imageinfo"][0]["extmetadata"]["LicenseShortName"]["value"] = "Copyrighted"
    assert normalize(image, city()) is None


def test_wrong_city_and_portraits_are_rejected():
    assert normalize(fixture(), city("Париж", "Европа", "Paris lithograph")) is None
    x = fixture()
    x["title"] = "File:Portrait of Lady Buenos Aires - lithograph.jpg"
    assert normalize(x, city()) is None
    x = fixture()
    x["imageinfo"][0]["width"] = 350
    assert normalize(x, city()) is None


def test_technique_quality_and_real_world_registry():
    assert classify("Paris chromolithograph.jpg") == "Литография"
    assert classify("Kyoto woodblock print.jpg") == "Ксилография"
    assert label_quality(850) == "невысокое"
    assert label_quality(2700) == "высокое"
    registry = json.loads((ROOT / "data/curation/world-cities-v1.json").read_text(encoding="utf-8"))
    assert len(registry["cities"]) >= 120
    assert len({x["name"] for x in registry["cities"]}) == len(registry["cities"])
    assert len({x["region"] for x in registry["cities"]}) == 6
    assert source_city_title("View of the city of Rome", {
        "name": "Рим", "query": "Rome city lithograph"
    })


def test_curation_blocks_wrong_city_and_promotional_cards():
    bad = fixture()
    bad["title"] = "File:Mostra di Louise Nevelson a Palazzo Fava, Bologna 05.jpg"
    assert normalize(bad, {"name": "Болонья", "country": "Италия", "region": "Европа",
                           "query": "Bologna city lithograph"}) is None
    bad["title"] = "File:Algiers, from the City Flags series (N6) for Cigarettes Brands.jpg"
    assert normalize(bad, {"name": "Алжир", "country": "Алжир", "region": "Африка",
                           "query": "Algiers city lithograph"}) is None
    bad["title"] = "File:Bank of Toronto, City of London, Ontario, Canada (1897).jpg"
    assert normalize(bad, {"name": "Торонто", "country": "Канада", "region": "Северная Америка",
                           "query": "Toronto city lithograph"}) is None


def test_historic_maps_are_labelled_without_treating_them_as_lithographs():
    assert classify("Admiralty Chart No 2434 Cartagena Harbour") == "Архивный план / карта"
    assert classify("Sanborn Fire Insurance Map Mexico City") == "Архивный план / карта"
