import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_book_copy_of_the_place_stories_is_the_researched_file():
    src = (ROOT / "data/stories/benoist-places-v1.json").read_text(encoding="utf-8")
    assert (ROOT / "book/places.json").read_text(encoding="utf-8") == src, (
        "cp data/stories/benoist-places-v1.json book/places.json"
    )
    assert [p["id"] for p in json.loads(src)["places"]] == [
        "madeleine",
        "notre-dame",
        "sainte-chapelle",
        "louvre-colonnade",
        "palais-royal",
        "tuileries",
    ]
