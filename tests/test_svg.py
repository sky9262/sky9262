import pytest

from helpers import assert_min_text, assert_no_external, assert_under, assert_valid_svg
from scripts.shrine.palette import PALETTE
from scripts.shrine.svg import (
    MOTION_CSS, document, esc, font_sizes, lantern, night_bg, petal_def,
    petals, rope, torii, visible_strings,
)

NS = 'xmlns="http://www.w3.org/2000/svg"'


def test_esc():
    assert esc('a&<b>"') == 'a&amp;&lt;b&gt;&quot;'


def test_document_is_valid_and_titled():
    svg = document(1200, 400, night_bg(1200, 400), title="Hero")
    assert_valid_svg(svg)
    assert "<title>Hero</title>" in svg
    assert 'viewBox="0 0 1200 400"' in svg


def test_font_sizes_inherit_from_group():
    svg = f'<svg {NS}><g font-size="14"><text>x</text></g></svg>'
    assert font_sizes(svg) == [(14.0, False)]


def test_font_sizes_marks_deco():
    svg = f'<svg {NS}><text class="deco" font-size="9">x</text><text font-size="20">y</text></svg>'
    assert font_sizes(svg) == [(9.0, True), (20.0, False)]


def test_visible_strings_skips_style_and_data_uri():
    svg = (
        f'<svg {NS}><style>.x{{}}</style><title>T</title>'
        '<image href="data:font/woff2;base64,QUJD" alt="A"/>'
        '<text>Hi</text></svg>'
    )
    out = visible_strings(svg)
    assert ".x{}" not in out and "data:" not in out and "QUJD" not in out
    assert "Hi" in out and "T" in out and "A" in out


def test_assert_min_text_flags_small():
    svg = f'<svg {NS} viewBox="0 0 1200 400"><text font-size="11">x</text></svg>'
    with pytest.raises(AssertionError):
        assert_min_text(svg, 846)
    ok = f'<svg {NS} viewBox="0 0 1200 400"><text font-size="18">x</text></svg>'
    assert_min_text(ok, 846)


def test_primitives_compose_valid():
    svg = document(
        1200, 400,
        night_bg(1200, 400) + torii(900, 128) + lantern(720, 300) + petals([(80, 1.2, 11, -2)]) + rope(300),
        title="t", defs=petal_def(), css=MOTION_CSS,
    )
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg)
    for k in ("fall", "dash", "pulse", "flicker", "breathe", "rise", "blink", "sway"):
        assert f"@keyframes {k}" in MOTION_CSS


def test_palette_tokens():
    assert PALETTE["night-0"] == "#070a1c" and PALETTE["vermilion"] == "#e8452c"
    assert PALETTE["wood-a"] == "#d8ad72" and PALETTE["wood-b"] == "#a7743a"
