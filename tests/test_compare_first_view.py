"""Keep the primary comparison artwork before advanced controls on small screens.

This is a regression check for the publicly observed mobile flow: on entry,
users reached several toolbars/help panels before the actual images.
"""
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "poc" / "compare" / "index.html"


class Audit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if props.get("id"):
            self.items.append((tag, props["id"]))
        if tag == "a" and props.get("href") == "#stage":
            self.items.append(("jump", props.get("data-i18n")))


def test_comparison_artwork_comes_before_advanced_tools_and_explanation():
    source = PAGE.read_text(encoding="utf-8")
    check = Audit()
    check.feed(source)
    ids = [item_id for _, item_id in check.items if item_id]
    for name in ("verdict", "zoomwrap", "stage", "alignBtn", "help", "credits"):
        assert ids.count(name) == 1, name
    assert ids.index("verdict") < ids.index("zoomwrap")
    assert ids.index("zoomwrap") < ids.index("alignBtn")
    assert ids.index("zoomwrap") < ids.index("help")
    assert ids.index("help") < ids.index("credits")


def test_mobile_jump_is_accessible_in_both_languages():
    source = PAGE.read_text(encoding="utf-8")
    check = Audit()
    check.feed(source)
    assert ("jump", "jump") in check.items
    assert 'jump: "К изображениям ↓"' in source
    assert 'jump: "Go to images ↓"' in source
    assert '#zoomwrap{scroll-margin-top:16px}' in source
