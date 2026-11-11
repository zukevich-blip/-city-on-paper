"""Historical engraving museum identity: proof-safe labels and source-verified composition."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DESIGNED = (
    "index.html",
    "cities/index.html",
    "atlas/index.html",
    "stories/index.html",
    "stories/paris-on-paper/index.html",
    "experience/index.html",
)

def test_engraving_layer_is_shared_across_six_original_museum_rooms():
    for name in DESIGNED:
        html = (ROOT / name).read_text(encoding="utf-8")
        assert '<body class="cop-engraved">' in html, name
        assert "assets/hybrid/tokens.css" in html, name
        assert "assets/hybrid/engraving.css" in html, name
        assert html.index("tokens.css") < html.index("engraving.css"), name
        assert html.count("engraving.css") == 1, name

def test_imprint_is_ours_and_not_forged_museum_institution_stamp():
    for name in ("index.html", "cities/index.html", "atlas/index.html"):
        html = (ROOT / name).read_text(encoding="utf-8")
        assert 'class="cop-imprint"' in html, name
        assert 'class="cop-signet" aria-hidden="true">ГБ</span>' in html, name
        assert 'class="cop-engraved-line" aria-hidden="true"' in html, name
        assert "Verified Source" not in html, name
        assert "Authenticity Guaranteed" not in html, name

def test_css_does_not_recolour_or_track_originals():
    css = (ROOT / "assets/hybrid/engraving.css").read_text(encoding="utf-8")
    tokens = (ROOT / "assets/hybrid/tokens.css").read_text(encoding="utf-8")
    assert "filter:none" in css
    assert "mix-blend-mode:normal" in css
    assert "@import" not in css
    assert not re.search(r"url\s*\(\s*['\"]?https?://", css)
    assert "@font-face" not in css
    assert "var(--cop-titling)" in css
    for variable in ("--cop-titling:", "--cop-sanguine:", "--cop-engraved-rule:",
                     "--cop-card:", "--cop-matte:"):
        assert variable in tokens
    assert "prefers-reduced-motion" in css
    assert "focus-visible" in css

def test_documented_distinction_between_editing_and_source_authentication():
    doc = (ROOT / "docs/design/ENGRAVING_MUSEUM_DESIGN_SYSTEM_20261111.md").read_text(encoding="utf-8")
    for item in ("candidate", "seed_only", "rights_class=open", "Library of Congress", "320, 390, 820"):
        assert item in doc
    cities = (ROOT / "cities/index.html").read_text(encoding="utf-8")
    assert 'Три исторических свидетельства · разные техники' in cities
    assert "1883" in cities and "1846" in cities
    atlas = (ROOT / "atlas/index.html").read_text(encoding="utf-8")
    assert "без геопривязки" in atlas
