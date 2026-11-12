import re

import pytest

from helpers import assert_min_text, assert_no_external, assert_under, assert_valid_svg
from scripts.shrine.cards.hero import ART_DIR, render_hero, scene_gif
from scripts.shrine.svg import visible_strings

CASES = [(lang, layout) for lang in ("jp", "en") for layout in ("desktop", "phone")]
IDS = [f"{lang}-{layout}" for lang, layout in CASES]
WIDTH = {"desktop": 846, "phone": 360}
VIEWBOX = {"desktop": "0 0 1200 500", "phone": "0 0 600 760"}


def _check_hero(svg: str, lang: str, layout: str, kb: int) -> None:
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, kb)
    assert_min_text(svg, WIDTH[layout])
    assert f'viewBox="{VIEWBOX[layout]}"' in svg
    seen = visible_strings(svg)
    assert "アカシュ・クマァ" in seen
    if lang == "en":
        assert "Akash Kumar" in seen
    assert "⛩" not in svg  # icons only, never the emoji
    assert "▌" not in svg  # the cursor is a drawn rect
    assert "@font-face" in svg and 'font-family="Shrine Serif"' in svg


@pytest.mark.parametrize("lang,layout", CASES, ids=IDS)
def test_hero(fonts, lang, layout):
    """Code-drawn fallback scene: no art needed, fits the normal 500 KB budget."""
    svg = render_hero(lang, layout, fonts)
    _check_hero(svg, lang, layout, 500)
    assert "<image" not in svg
    assert 'id="torii"' in svg and "class=\"pf\"" in svg


@pytest.mark.parametrize("lang,layout", CASES, ids=IDS)
def test_hero_gif(fonts, lang, layout):
    gif = scene_gif(layout)
    if gif is None:
        pytest.skip("scripts/build/art/*.gif absent")
    svg = render_hero(lang, layout, fonts, gif)
    _check_hero(svg, lang, layout, 1536)
    assert svg.count("data:image/gif;base64,") == 1
    assert re.search(r'<image [^>]*clip-path="url\(#', svg), "scene must be clipped to rounded corners"
    assert re.search(r'<clipPath id="[^"]+"><rect [^>]*rx="16"', svg)


def test_hero_text_order_and_lang(fonts):
    jp = visible_strings(render_hero("jp", "desktop", fonts))
    en = visible_strings(render_hero("en", "desktop", fonts))
    assert "AIエンジニア" in jp and "古き社に、新しい知性を。" in jp
    assert "Where ancient spirits meet artificial minds." in en
    body = en[en.index("summon --engineer"):]  # skip the <title>
    pos = [body.index(s) for s in ("Akash Kumar", "アカシュ・クマァ", "AI Engineer", "Where ancient")]
    assert pos == sorted(pos)


def test_scene_gif_paths():
    assert ART_DIR.name == "art" and ART_DIR.parent.name == "build"
