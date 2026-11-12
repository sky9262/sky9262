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


# ---------------------------------------------------------------- plaques (絵馬)

from scripts.shrine.cards.plaque import INNER_W, MIN_SIZE, back_text, render_plaque  # noqa: E402
from scripts.shrine.content import NDA, active_plaques  # noqa: E402
from scripts.shrine.metrics import text_width  # noqa: E402

PLAQUE_CASES = [(i, p.id, lang) for i, p in enumerate(active_plaques()) for lang in ("jp", "en")]
PLAQUE_IDS = [f"{pid}-{lang}" for _, pid, lang in PLAQUE_CASES]


def _plaque(pid: str):
    return next(p for p in active_plaques() if p.id == pid)


@pytest.mark.parametrize("index,pid,lang", PLAQUE_CASES, ids=PLAQUE_IDS)
def test_plaque_all(fonts, index, pid, lang):
    p = _plaque(pid)
    svg = render_plaque(p, lang, index, fonts)
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, 500)
    assert_min_text(svg, 360)
    assert 'viewBox="0 0 420 360"' in svg
    seen = visible_strings(svg)
    assert p.title(lang) in seen and p.subtitle(lang) in seen
    for line in p.lines(lang).split("\n"):
        assert line in seen
    for tag in p.tags:
        assert tag in seen
    assert "@font-face" in svg
    for emoji in ("🔒", "🌐", "★", "⛩"):
        assert emoji not in svg  # drawn as icon paths, never emoji glyphs
    # prototype flip keyframes, verbatim
    assert "@keyframes front{0%,40%{transform:scaleX(1)}45%,95%{transform:scaleX(0)}100%{transform:scaleX(1)}}" in svg
    assert "@keyframes back{0%,45%{transform:scaleX(0)}50%,90%{transform:scaleX(1)}95%,100%{transform:scaleX(0)}}" in svg
    assert "rotate(1.4deg)" in svg  # shared sway, not the prototype's 1.2


def test_plaque_stagger(fonts):
    p = active_plaques()[0]
    svg = render_plaque(p, "en", 3, fonts)
    assert svg.count("animation-delay:-4.5s") >= 2  # front and back faces
    assert re.search(r'class="front"[^>]*animation-delay:-4.5s', svg)
    assert re.search(r'class="back"[^>]*animation-delay:-4.5s', svg)
    assert "animation-delay:-4.5s" not in render_plaque(p, "en", 0, fonts)


@pytest.mark.parametrize("lang", ["jp", "en"])
def test_client_back_has_nda(fonts, lang):
    for i, p in enumerate(active_plaques()):
        seen = visible_strings(render_plaque(p, lang, i, fonts))
        if p.kind == "client":
            assert NDA(lang) in seen, p.id
        else:
            assert NDA(lang) not in seen, p.id


def test_stars_stamp(fonts):
    p = _plaque("phisheye")
    seen = visible_strings(render_plaque(p, "en", 4, fonts, stars=87, forks=24))
    assert "87" in seen and "24 forks" in seen
    bare = visible_strings(render_plaque(p, "en", 4, fonts))
    assert "87" not in bare and "24" not in bare


def test_stamp_kinds(fonts):
    seen = {p.stamp: visible_strings(render_plaque(p, "jp", i, fonts)) for i, p in enumerate(active_plaques())}
    assert "本番" in seen["prod"] and "PROD" in seen["prod"]
    assert "HF" in seen["hf"]


def test_jp_title_primary(fonts):
    p = _plaque("drone")
    jp = visible_strings(render_plaque(p, "jp", 3, fonts))
    en = visible_strings(render_plaque(p, "en", 3, fonts))
    body_jp, body_en = jp.split("\n", 1)[1], en.split("\n", 1)[1]  # skip <title>
    # the long EN title may wrap onto two lines on the front, so compare its first words
    assert body_jp.index("ドローン編隊自動生成エンジン") < body_jp.index("Drone Light-Show")
    assert body_en.index("Drone Light-Show") < body_en.index("ドローン編隊自動生成エンジン")


@pytest.mark.parametrize("index,pid,lang", PLAQUE_CASES, ids=PLAQUE_IDS)
def test_back_lines_fit(index, pid, lang):
    """Every back line fits the plaque's inner width at >= 14 units, untruncated."""
    p = _plaque(pid)
    size, lines = back_text(p, lang)
    assert size >= MIN_SIZE == 14
    assert lines == p.lines(lang).split("\n")
    for line in lines:
        assert text_width(line, size) <= INNER_W, line


def test_metrics_match_fonts():
    """The stdlib width table agrees with the real Noto Serif JP advances."""
    pytest.importorskip("fontTools")
    from conftest import SERIF_DIR
    from fontTools.ttLib import TTFont

    if not (SERIF_DIR / "NotoSerifJP-Regular.ttf").exists():
        pytest.skip("font sources absent")
    text = "".join(p.lines(lang) + p.title(lang) for p in active_plaques() for lang in ("jp", "en"))
    text += NDA("jp") + NDA("en")
    for weight, name in ((400, "Regular"), (700, "Bold")):
        f = TTFont(str(SERIF_DIR / f"NotoSerifJP-{name}.ttf"))
        cmap, hm = f.getBestCmap(), f["hmtx"]
        for ch in set(text) - {"\n"}:
            assert text_width(ch, 1000, weight=weight) == pytest.approx(hm[cmap[ord(ch)]][0]), (ch, weight)


def test_plaque_stdlib_only():
    """The CI generator imports plaque.py without fontTools."""
    code = (
        "import sys; sys.modules['fontTools'] = None\n"
        "from scripts.shrine.cards.plaque import render_plaque\n"
        "from scripts.shrine.content import active_plaques\n"
        "from scripts.shrine.fonts import RuntimeFonts\n"
        "p = [p for p in active_plaques() if p.id == 'phisheye'][0]\n"
        "svg = render_plaque(p, 'en', 4, RuntimeFonts(), stars=87, forks=24)\n"
        "assert '24 forks' in svg\n"
    )
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
