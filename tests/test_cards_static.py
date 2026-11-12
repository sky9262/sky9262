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
    assert "AI・セキュリティエンジニア" in jp and "古き社に、新しい知性を。" in jp
    assert "Where ancient spirits meet artificial minds." in en
    body = en[en.index("summon --engineer"):]  # skip the <title>
    pos = [body.index(s) for s in ("Akash Kumar", "アカシュ・クマァ", "AI & Security Engineer", "Where ancient")]
    assert pos == sorted(pos)


def test_scene_gif_paths():
    assert ART_DIR.name == "art" and ART_DIR.parent.name == "build"


# ---------------------------------------------------------------- plaques (絵馬)

from scripts.shrine.cards.plaque import (  # noqa: E402
    DETAIL_W, DETAIL_X, LEFT, MIN_SIZE, PL, PR, RIGHT, detail_lines, plaque_height, render_plaque,
)
from scripts.shrine.content import NDA, active_plaques  # noqa: E402
from scripts.shrine.metrics import text_width  # noqa: E402

PLAQUE_CASES = [(i, p.id, lang) for i, p in enumerate(active_plaques()) for lang in ("jp", "en")]
PLAQUE_IDS = [f"{pid}-{lang}" for _, pid, lang in PLAQUE_CASES]


def _plaque(pid: str):
    return next(p for p in active_plaques() if p.id == pid)


def _compact(s: str) -> str:
    return re.sub(r"\s+", "", s)


@pytest.mark.parametrize("index,pid,lang", PLAQUE_CASES, ids=PLAQUE_IDS)
def test_plaque_all(fonts, index, pid, lang):
    p = _plaque(pid)
    svg = render_plaque(p, lang, index, fonts)
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, 500)
    assert_min_text(svg, 360)
    assert re.search(r'viewBox="0 0 420 \d+"', svg)
    seen = visible_strings(svg)
    body = _compact(seen.split("\n", 1)[1])  # skip <title>; wrapped lines rejoin without spaces
    assert _compact(p.title(lang)) in body and _compact(p.subtitle(lang)) in body
    for line in p.lines(lang).split("\n"):
        assert _compact(line) in body, line  # every detail line, never truncated
    for tag in p.tags:
        assert tag in seen
    assert "@font-face" in svg
    for emoji in ("🔒", "🌐", "★", "⛩"):
        assert emoji not in svg  # drawn as icon paths, never emoji glyphs


@pytest.mark.parametrize("index,pid,lang", PLAQUE_CASES, ids=PLAQUE_IDS)
def test_plaque_no_flip(fonts, index, pid, lang):
    """Owner edit 2: everything shows at once; the board does not flip or swing."""
    svg = render_plaque(_plaque(pid), lang, index, fonts)
    assert "scaleX(0)" not in svg
    assert 'class="front"' not in svg and 'class="back"' not in svg
    assert ".front{" not in svg and ".back{" not in svg
    assert 'class="sway"' not in svg  # the board hangs still; only the shide flutter


def test_plaque_shared_height(fonts):
    h = plaque_height()
    assert 480 <= h <= 600
    for i, p in enumerate(active_plaques()):
        for lang in ("jp", "en"):
            svg = render_plaque(p, lang, i, fonts)
            assert f'viewBox="0 0 420 {h}"' in svg, (p.id, lang)
    live = render_plaque(_plaque("phisheye"), "jp", 4, fonts, stars=12345, forks=6789)
    assert f'viewBox="0 0 420 {h}"' in live


def test_plaque_stagger(fonts):
    p = active_plaques()[0]
    svg = render_plaque(p, "en", 3, fonts)
    assert re.search(r'class="sheen"[^>]*animation-delay:-4.5s', svg)
    assert re.search(r'class="spin"[^>]*animation-delay:-4.5s', svg)  # motif phase
    assert re.search(r'class="toriiGlow"[^>]*animation-delay:-4.5s', svg)  # lantern glow
    assert ".rope path:nth-child(n+3){animation-delay:-4.5s}" in svg  # shide flutter
    assert re.search(r'class="tassel"[^>]*animation-delay:-5.5s', svg)  # cord tassel (-1 s own phase)
    assert "animation-delay:-4.5s" not in render_plaque(p, "en", 0, fonts)


def test_plaque_overflow_guard(fonts):
    """An unbreakable line wider than its column fails the build, never renders clipped."""
    import dataclasses

    from scripts.shrine.content import T

    p = _plaque("scout")
    long_word = "Supercalifragilisticexpialidocious-and-then-some-more"
    bad_lines = dataclasses.replace(p, lines=T(p.lines.jp, p.lines.en + "\n" + long_word))
    with pytest.raises(ValueError):
        detail_lines(bad_lines, "en")
    with pytest.raises(ValueError):
        render_plaque(bad_lines, "en", 0, fonts)
    bad_title = dataclasses.replace(p, title=T(p.title.jp, long_word))
    with pytest.raises(ValueError):
        render_plaque(bad_title, "en", 0, fonts)
    bad_sub = dataclasses.replace(p, subtitle=T(long_word, p.subtitle.en))
    with pytest.raises(ValueError):
        render_plaque(bad_sub, "jp", 0, fonts)


def test_plaque_padding():
    assert LEFT - PL >= 34 and PR - RIGHT >= 34


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
    # titles may wrap, so compare their first words
    assert body_jp.index("ドローン") < body_jp.index("Drone")
    assert body_en.index("Drone") < body_en.index("ドローン")


@pytest.mark.parametrize("index,pid,lang", PLAQUE_CASES, ids=PLAQUE_IDS)
def test_detail_lines_fit(index, pid, lang):
    """Every detail line is wrapped to the padded text width at >= 14 units, untruncated."""
    p = _plaque(pid)
    size, items = detail_lines(p, lang)
    assert size >= MIN_SIZE == 14
    assert DETAIL_X + DETAIL_W <= RIGHT
    originals = p.lines(lang).split("\n")
    if lang == "jp":  # one marked item per line
        assert len(items) == len(originals)
        for pieces, line in zip(items, originals):
            assert _compact("".join(pieces)) == _compact(line)
    else:  # one paragraph, wrapped by metrics.wrap()
        assert len(items) == 1
        assert " ".join(items[0]) == " ".join(originals)
        _assert_arrow_glue(items[0])
    width = DETAIL_W if lang == "jp" else RIGHT - LEFT
    for piece in (x for item in items for x in item):
        assert text_width(piece, size) <= width, piece


def test_metrics_match_fonts():
    """The stdlib width table agrees with the real Noto Serif JP advances."""
    pytest.importorskip("fontTools")
    from conftest import SERIF_DIR
    from fontTools.ttLib import TTFont

    if not (SERIF_DIR / "NotoSerifJP-Regular.ttf").exists():
        pytest.skip("font sources absent")
    text = "".join(p.lines(lang) + p.title(lang) for p in active_plaques() for lang in ("jp", "en"))
    text += NDA("jp") + NDA("en")
    from scripts.shrine.content import CANDO, SECTION, STACK

    for lang in ("jp", "en"):
        text += "".join(t(lang) + l(lang) for _, t, l in CANDO)
        text += "".join(g(lang) + "".join(tools) for g, tools in STACK)
        text += SECTION["cando"](lang) + SECTION["stack"](lang)
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


# ---------------------------------------------------------------- line wrapping

from scripts.shrine.metrics import wrap  # noqa: E402


def test_wrap_never_truncates_and_fits():
    jp = "自律型AIのガードレール、テナント分離、監査ログ。GCPのIAPとCloud Armor（WAF）による防御。"
    lines = wrap(jp, 17.2, 330)
    assert "".join(l.replace(" ", "") for l in lines) == jp.replace(" ", "")
    for line in lines:
        assert text_width(line, 17.2) <= 330
    en = "Guardrails for autonomous AI, tenant isolation, audit logs; GCP IAP and Cloud Armor WAF."
    lines = wrap(en, 17.2, 330)
    assert " ".join(lines) == en
    assert all(text_width(l, 17.2) <= 330 for l in lines)


def test_wrap_kinsoku():
    """No line starts with closing punctuation or ends with an opening bracket."""
    text = "社内文書を根拠に回答するRAG（LangChain）と、LoRA・QLoRAによる追加学習。" * 3
    for width in (120, 160, 200, 260, 330):
        for line in wrap(text, 17.2, width):
            assert line[0] not in "、。・）", (width, line)
            assert line[-1] != "（", (width, line)


def test_wrap_keeps_katakana_words():
    lines = wrap(
        "拡散モデルによるポートレート生成の研究、GLBモデルをパーティクルに変えるThree.jsの演出、"
        "再利用できるエージェントスキルの開発。",
        17.2,
        330,
    )
    assert not any(l.startswith("ト") or l.endswith("ェン") for l in lines), lines


_NO_START_SYMBOLS = ("→", "–", "—", "%", "）")


def _assert_arrow_glue(lines):
    for line in lines:
        assert not line.startswith(_NO_START_SYMBOLS), lines
        assert not line.endswith("→"), lines


@pytest.mark.parametrize("width", [150, 170, 200, 240])
def test_wrap_glues_arrows_and_units_en(width):
    text = "Mesh rate 38.4% → 3.6%. Background removal 2.99 s → 0.5 s."
    lines = wrap(text, 16, width)
    assert " ".join(lines) == text
    _assert_arrow_glue(lines)
    for line in lines:  # a bare unit never strands at the start of a line
        assert not re.match(r"(s|m)\b", line), lines
        assert not re.search(r"\d$", line) or not line.endswith(("2.99", "0.5", "1.5")), lines
    joined = "\n".join(lines)
    assert "2.99 s" in joined and "0.5 s" in joined


def test_wrap_unit_glue_examples():
    lines = wrap("Mesh rate 38.4% → 3.6%. Background removal 2.99 s → 0.5 s.", 16, 150)
    assert "→ 0.5 s." not in lines
    _assert_arrow_glue(lines)
    lines = wrap("Mesh rate 38.4% → 3.6%. Background removal 2.99 s → 0.5 s.", 16, 170)
    assert not any(l.startswith("s ") or l.endswith("2.99") for l in lines), lines
    lines = wrap("formation: exact count, ≥1.5 m apart.", 16, 120)
    assert not any(l.endswith("1.5") for l in lines), lines


@pytest.mark.parametrize("width", [100, 130, 160])
def test_wrap_glues_arrows_jp(width):
    lines = wrap("論点の判定 8〜24秒 → 1.5〜2.5秒", 15, width)
    _assert_arrow_glue(lines)
    assert not any(l.startswith("〜") for l in lines), lines


def test_wrap_keeps_okurigana_compound():
    lines = wrap("文字誤り率（CER）44.3% → 31.2%", 15, 120)
    assert any("文字誤り率" in l for l in lines), lines
    _assert_arrow_glue(lines)


# ---------------------------------------------------------------- what I can do (我が道)

from scripts.shrine.cards.cando import BODY_SIZE, TEXT_W, body_lines, render_cando, title_fit  # noqa: E402
from scripts.shrine.content import CANDO, SECTION, STACK  # noqa: E402

CANDO_VIEWBOX = {"desktop": "0 0 1200 560", "phone": "0 0 600 1286"}  # phone: 3- and 4-line charms need more than the planned 1180
MIN_UNITS = {"desktop": 17, "phone": 20}


def _norm(seen: str, lang: str) -> str:
    """Visible text with wrapped lines rejoined (JP lines join directly, EN with a space)."""
    if lang == "jp":
        return seen.replace("\n", "")
    return " ".join(seen.split())


@pytest.mark.parametrize("lang,layout", CASES, ids=IDS)
def test_cando(fonts, lang, layout):
    svg = render_cando(lang, layout, fonts)
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, 500)
    assert_min_text(svg, WIDTH[layout])
    assert f'viewBox="{CANDO_VIEWBOX[layout]}"' in svg
    seen = visible_strings(svg)
    joined = _norm(seen, lang)
    for _, title, line in CANDO:
        assert title(lang) in seen
        if lang == "jp":  # a JP line may wrap at an inner space ("Cloud Armor")
            assert line(lang).replace(" ", "") in joined.replace(" ", "")
        else:
            assert line(lang) in joined
    for part in SECTION["cando"](lang).split(" · "):
        assert part in seen
    assert "@font-face" in svg
    for emoji in ("🤖", "📚", "⚡", "🎨", "🛡"):
        assert emoji not in svg
    # five tiles, each swaying with its own delay
    delays = re.findall(r'class="sway[^"]*"[^>]*animation-delay:(-?[\d.]+)s', svg)
    assert len(delays) == 5 and len(set(delays)) == 5


@pytest.mark.parametrize("lang,layout", CASES, ids=IDS)
def test_cando_text_fits(lang, layout):
    size = BODY_SIZE[layout]
    assert size >= MIN_UNITS[layout]
    for (_, _, line), lines in zip(CANDO, body_lines(lang, layout)):
        if layout == "desktop":
            assert len(lines) <= 4, lines
        sep = "" if lang == "jp" else " "
        assert sep.join(lines).replace(" ", "") == line(lang).replace(" ", "")
        for l in lines:
            assert text_width(l, size) <= TEXT_W[layout], l
    for _, title, _ in CANDO:
        ts, ls = title_fit(title(lang), layout)
        assert ts >= MIN_UNITS[layout] + 3  # titles stay clearly larger than the body
        assert text_width(title(lang), ts, weight=700, letter_spacing=ls) <= TEXT_W[layout]


# ---------------------------------------------------------------- tech stack (道具)

from scripts.shrine.cards.stack import plan, render_stack  # noqa: E402
from scripts.shrine.icons import BRAND, TEXT_ONLY  # noqa: E402

TOOLS = [t for _, items in STACK for t in items]


@pytest.mark.parametrize("lang,layout", CASES, ids=IDS)
def test_stack(fonts, lang, layout):
    svg = render_stack(lang, layout, fonts)
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, 500)
    assert_min_text(svg, WIDTH[layout])
    w = 1200 if layout == "desktop" else 600
    h, _ = plan(lang, layout)
    assert f'viewBox="0 0 {w} {h}"' in svg
    seen = visible_strings(svg)
    flat = " ".join(seen.split())
    for tool in TOOLS:
        assert tool in flat, tool
    other = "en" if lang == "jp" else "jp"
    for label, _ in STACK:
        assert label(lang) in seen
        assert label(other) not in seen
    for part in SECTION["stack"](lang).split(" · "):
        assert part in seen
    for tool in BRAND:
        assert BRAND[tool][0] in svg, tool  # real logo path
    assert "@font-face" in svg
    assert "@keyframes lightup" in svg


@pytest.mark.parametrize("lang,layout", CASES, ids=IDS)
def test_stack_lightup_sequence(fonts, lang, layout):
    svg = render_stack(lang, layout, fonts)
    _, tiles = plan(lang, layout)
    anims = re.findall(r"animation:lightup \.6s ease-out ([\d.]+)s both", svg)
    assert len(anims) == len(TOOLS) == len(tiles)
    expected = sorted(f"{round(0.15 * t.k, 2):g}" for t in tiles)
    assert sorted(anims) == expected
    assert max(float(a) for a in anims) + 0.6 <= 3.0  # fully lit within 3 s


@pytest.mark.parametrize("lang,layout", CASES, ids=IDS)
def test_stack_layout(lang, layout):
    """Every lantern sits inside the card and no two overlap; brand tools carry a logo."""
    h, tiles = plan(lang, layout)
    w = 1200 if layout == "desktop" else 600
    assert [t.name for t in tiles] == TOOLS
    for t in tiles:
        assert 0 < t.x and t.x + t.w < w and 0 < t.y and t.y + t.h < h, t
        assert t.logo == (t.name not in TEXT_ONLY)
    for i, a in enumerate(tiles):
        for b in tiles[i + 1:]:
            apart = a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y
            assert apart, (a.name, b.name)


# ---------------------------------------------------------------- natural Japanese line breaks

PARTICLES = ("は", "が", "を", "に", "で", "と", "の", "も", "へ", "や", "から", "まで", "より")
SMALL_KANA = set("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶー")
HIRAGANA = {chr(c) for c in range(0x3041, 0x3097)}


@pytest.mark.parametrize("layout", ["desktop", "phone"])
def test_cando_jp_lines_start_naturally(layout):
    """No wrapped JP line starts with a particle, small kana or a hiragana continuation."""
    for lines in body_lines("jp", layout):
        for prev, line in zip(lines, lines[1:]):
            assert not line.startswith(PARTICLES), (prev, line)
            assert line[0] not in SMALL_KANA, (prev, line)
            if prev[-1] not in "、。":
                assert line[0] not in HIRAGANA, (prev, line)


@pytest.mark.parametrize("lang,layout", CASES, ids=IDS)
def test_cando_keeps_compounds_and_names(lang, layout):
    lines = [l for ls in body_lines(lang, layout) for l in ls]
    if lang == "jp":
        assert any("テナント分離" in l for l in lines), lines
    assert any("Cloud Armor" in l for l in lines), lines
    assert any("Apple Silicon" in l for l in lines), lines


@pytest.mark.parametrize("layout", ["desktop", "phone"])
def test_cando_rag_line_not_split_before_wa(layout):
    rag = body_lines("jp", layout)[1]
    assert not any(l.startswith("は") for l in rag), rag
    assert any("モデルでは" in l for l in rag), rag


def test_wrap_no_break_names():
    text = "Guardrails and tenant isolation behind GCP IAP and Cloud Armor, on Apple Silicon with Hugging Face."
    for width in range(140, 420, 7):
        joined = "\n".join(wrap(text, 17.2, width))
        for name in ("Cloud Armor", "Apple Silicon", "Hugging Face"):
            assert name in joined, (width, joined)


def test_wrap_prefers_extra_line_to_bad_break():
    """A compound or a particle split is worse than one more line."""
    text = "LoRA・QLoRAによる追加学習。Whisperのアニメ音声モデルでは文字誤り率を44.3%から31.2%に改善。"
    for width in range(240, 520, 6):
        lines = wrap(text, 20, width)
        for prev, line in zip(lines, lines[1:]):
            assert line[0] not in HIRAGANA or prev[-1] in "、。", (width, lines)
            assert not (prev.endswith("音") and line.startswith("声")), (width, lines)


# ---------------------------------------------------------------- achievements (奉納額)

from scripts.shrine.cards.achievement import EMBLEM, TEXT_W as ACH_TEXT_W, render_achievement, title_lines  # noqa: E402
from scripts.shrine.content import ACHIEVEMENTS, CONNECT, LINKS, TOGGLE  # noqa: E402
from scripts.shrine.icons import GLYPH  # noqa: E402

ACH_CASES = [(aid, lang) for aid, _, _ in ACHIEVEMENTS for lang in ("jp", "en")]
ACH_IDS = [f"{aid}-{lang}" for aid, lang in ACH_CASES]
EMOJI = ("🏆", "🥇", "🎖", "🚩", "🏅", "⭐", "★", "⛩", "🔔", "✉", "🌐")


def _ach(aid: str):
    return next(a for a in ACHIEVEMENTS if a[0] == aid)


@pytest.mark.parametrize("aid,lang", ACH_CASES, ids=ACH_IDS)
def test_achievement(fonts, aid, lang):
    _, title, detail = _ach(aid)
    svg = render_achievement(aid, lang, fonts)
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, 500)
    assert_min_text(svg, 360)  # 410 viewBox shown at 360 px: >= 14 units
    assert 'viewBox="0 0 410 200"' in svg
    seen = visible_strings(svg)
    assert _norm(seen, lang).replace(" ", "").count(title(lang).replace(" ", "")) >= 1
    assert detail(lang) in seen
    assert "@font-face" in svg
    for e in EMOJI:
        assert e not in svg
    assert re.search(r'class="sway"', svg)


@pytest.mark.parametrize("aid,lang", ACH_CASES, ids=ACH_IDS)
def test_achievement_title_fits(aid, lang):
    """Long titles wrap (never truncate) and every line fits the text column at >= 14."""
    _, title, _ = _ach(aid)
    size, lines = title_lines(aid, lang)
    assert size >= 14
    assert 1 <= len(lines) <= 3
    sep = "" if lang == "jp" else " "
    assert sep.join(lines).replace(" ", "") == title(lang).replace(" ", "")
    for line in lines:
        assert text_width(line, size, weight=700) <= ACH_TEXT_W, line


def test_wrap_no_line_starts_with_dash():
    """A spaced dash stays with both neighbours whenever the phrase around it fits a line."""
    for text, phrase in (
        ("AWS認定 デベロッパー – アソシエイト", "デベロッパー – アソシエイト"),
        ("AWS Certified Developer – Associate", "Developer – Associate"),
    ):
        for width in range(int(text_width(phrase, 20, weight=700)) + 1, 420, 4):
            lines = wrap(text, 20, width, weight=700)
            assert not any(l.startswith(("–", "—")) or l.endswith(("–", "—")) for l in lines), (width, lines)


def test_achievement_emblems(fonts):
    assert set(EMBLEM) == {aid for aid, _, _ in ACHIEVEMENTS}
    assert EMBLEM["squid_ctf"] in ("trophy", "medal", "flag")
    assert EMBLEM["knight_ctf"] in ("trophy", "medal", "flag")
    assert EMBLEM["aws_dev"] == EMBLEM["agentforce"] == "seal"
    assert EMBLEM["tryhackme"] == "thm"
    assert EMBLEM["jlpt"] == "pass"
    assert "合格" in visible_strings(render_achievement("jlpt", "en", fonts))
    assert GLYPH["tryhackme"] in render_achievement("tryhackme", "jp", fonts)
    # each tablet sways on its own phase
    delays = {re.search(r'class="sway"[^>]*animation-delay:(-?[\d.]+)s', render_achievement(a, "jp", fonts)).group(1)
              for a, _, _ in ACHIEVEMENTS}
    assert len(delays) == len(ACHIEVEMENTS)


def test_achievement_unknown_id(fonts):
    with pytest.raises(KeyError):
        render_achievement("nope", "jp", fonts)


# ---------------------------------------------------------------- connect (ご縁)

from scripts.shrine.cards.connect import render_connect  # noqa: E402

CONNECT_VIEWBOX = {"desktop": "0 0 1200 360", "phone": "0 0 600 560"}


@pytest.mark.parametrize("lang,layout", CASES, ids=IDS)
def test_connect(fonts, lang, layout):
    svg = render_connect(lang, layout, fonts)
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, 500)
    assert_min_text(svg, WIDTH[layout])
    assert min(s for s, deco in font_sizes(svg) if not deco) >= MIN_UNITS[layout]
    assert f'viewBox="{CONNECT_VIEWBOX[layout]}"' in svg
    seen = visible_strings(svg)
    joined = _norm(seen, lang)
    for key in ("heading", "bell", "signoff"):
        assert CONNECT[key](lang) in joined, key
    for part in SECTION["connect"](lang).split(" · "):
        assert part in seen
    assert re.search(r'class="sway"', svg)  # the bell and its rope swing
    assert "<a " not in svg and "<a>" not in svg  # links are the separate buttons
    for lid, _, _ in LINKS:
        assert GLYPH[lid] in svg, lid  # decorative row of link glyphs
    for e in EMOJI:
        assert e not in svg
    assert "@font-face" in svg


# ---------------------------------------------------------------- link buttons and language toggle

from scripts.shrine.cards.button import render_button, render_toggle  # noqa: E402
from scripts.shrine.svg import font_sizes  # noqa: E402


@pytest.mark.parametrize("lid,label", [(l, lab) for l, lab, _ in LINKS], ids=[l for l, _, _ in LINKS])
def test_button(fonts, lid, label):
    svg = render_button(lid, fonts)
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, 500)
    assert_min_text(svg, 220)  # shown at native width
    assert 'viewBox="0 0 220 56"' in svg
    assert label in visible_strings(svg)
    assert GLYPH[lid] in svg
    assert "@font-face" in svg
    for e in EMOJI:
        assert e not in svg
    for other in ("English", "日本語"):
        assert other not in svg  # language-neutral


def test_buttons_cover_links(fonts):
    svgs = {lid: render_button(lid, fonts) for lid, _, _ in LINKS}
    assert len(svgs) == 7 and len(set(svgs.values())) == 7
    with pytest.raises(KeyError):
        render_button("myspace", fonts)


@pytest.mark.parametrize("lang", ["jp", "en"])
def test_toggle(fonts, lang):
    svg = render_toggle(lang, fonts)
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, 500)
    assert_min_text(svg, 180)
    assert 'viewBox="0 0 180 44"' in svg
    assert TOGGLE(lang) in visible_strings(svg)
    assert TOGGLE("en" if lang == "jp" else "jp") not in visible_strings(svg)
    assert "@font-face" in svg


def test_misc_cards_stdlib_only():
    """The CI generator can rebuild these cards without fontTools."""
    code = (
        "import sys; sys.modules['fontTools'] = None\n"
        "from scripts.shrine.fonts import RuntimeFonts\n"
        "from scripts.shrine.cards.achievement import render_achievement\n"
        "from scripts.shrine.cards.connect import render_connect\n"
        "from scripts.shrine.cards.button import render_button, render_toggle\n"
        "f = RuntimeFonts()\n"
        "render_achievement('jlpt', 'jp', f); render_connect('en', 'phone', f)\n"
        "render_button('gmail', f); render_toggle('jp', f)\n"
    )
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_misc_metrics_match_fonts():
    """Width table / one-em fallback agree with Noto Serif JP for the new cards' text."""
    pytest.importorskip("fontTools")
    from conftest import SERIF_DIR
    from fontTools.ttLib import TTFont

    if not (SERIF_DIR / "NotoSerifJP-Regular.ttf").exists():
        pytest.skip("font sources absent")
    text = "".join(t.jp + t.en + d.jp + d.en for _, t, d in ACHIEVEMENTS)
    text += "".join(v.jp + v.en for v in CONNECT.values()) + TOGGLE.jp + TOGGLE.en
    text += "".join(lab for _, lab, _ in LINKS) + SECTION["connect"].jp + SECTION["connect"].en + "合格"
    for weight, name in ((400, "Regular"), (700, "Bold")):
        f = TTFont(str(SERIF_DIR / f"NotoSerifJP-{name}.ttf"))
        cmap, hm = f.getBestCmap(), f["hmtx"]
        for ch in set(text):
            assert text_width(ch, 1000, weight=weight) == pytest.approx(hm[cmap[ord(ch)]][0]), (ch, weight)
