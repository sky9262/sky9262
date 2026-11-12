import re

from helpers import assert_no_external, assert_valid_svg
from scripts.shrine.content import CANDO, LINKS, STACK
from scripts.shrine.icons import BRAND, GLYPH, TEXT_ONLY, icon, on_dark
from scripts.shrine.svg import document


def test_every_stack_tool_resolved_or_textonly():
    tools = [t for _, items in STACK for t in items]
    missing = [t for t in tools if t not in BRAND and t not in TEXT_ONLY]
    assert not missing
    assert set(BRAND) <= set(tools)
    assert not TEXT_ONLY & set(BRAND)


def test_brand_entries_wellformed():
    for name, (d, hx) in BRAND.items():
        assert re.fullmatch(r"#[0-9a-fA-F]{6}", hx), name
        assert d.startswith("M") and len(d) > 40, name


def test_glyphs_cover_needed_ids():
    need = {"lock", "globe", "torii", "bell", "star", "fork", "hf", "mail"}
    need |= {i for i, _, _ in CANDO} | {i for i, _, _ in LINKS}
    assert need <= set(GLYPH)


def test_icon_fragment_valid():
    frags = [icon(n, 10, 10, 24) for n in list(GLYPH) + list(BRAND)]
    frags.append(icon("lock", 0, 0, 24, "#ffcf7a"))
    svg = document(400, 100, "".join(frags), title="icons")
    assert_valid_svg(svg)
    assert_no_external(svg)


def test_icon_fragment_shape():
    f = icon("lock", 5, 6, 48, "#fff")
    assert f.startswith("<g transform=") and "translate(5,6)" in f
    assert "scale(2)" in f and 'fill="#fff"' in f


def test_on_dark():
    assert on_dark("#000000") == "#e8e4f5"
    assert on_dark("#3776AB") == "#3776AB"
    assert on_dark("#ffffff") == "#ffffff"
