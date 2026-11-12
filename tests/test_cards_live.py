"""Live activity cards (千本鳥居 · 活動): rendered with RuntimeFonts from fixture data."""
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from helpers import assert_min_text, assert_no_external, assert_under, assert_valid_svg
from scripts.generate.github_data import load_fixture
from scripts.shrine.fonts import FONT_DIR, RuntimeFonts
from scripts.shrine.svg import visible_strings

FIX = Path(__file__).parent / "fixtures" / "github"
ROOT_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "common"
NOW = datetime(2026, 11, 12, 0, 0, tzinfo=timezone.utc)
LANGS = ("jp", "en")
LAYOUTS = ("desktop", "phone")
# rendered width -> minimum SVG units (12 px rendered); asserted via assert_min_text too
MIN_UNITS = {"desktop": 17, "phone": 20, "small": 14}
RENDERED = {"desktop": 846, "phone": 360, "small": 360}
STATS = ("contrib", "month", "peak", "stars")

from scripts.shrine.cards import live  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return load_fixture(FIX)


@pytest.fixture(scope="module")
def rfonts():
    if not list(FONT_DIR.glob("runtime-*.woff2")):
        pytest.skip("runtime fonts not generated")
    return RuntimeFonts()


def _sizes(svg: str) -> list[float]:
    from scripts.shrine.svg import font_sizes

    return [s for s, deco in font_sizes(svg) if not deco]


def _check(svg: str, kind: str) -> None:
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, 500)
    assert_min_text(svg, RENDERED[kind])
    assert min(_sizes(svg)) >= MIN_UNITS[kind]


def _all_cards(data, fonts):
    """(name, kind, svg) for every live card x language x layout."""
    out = []
    for lang in LANGS:
        for layout in LAYOUTS:
            out.append((f"torii-{layout}-{lang}", layout, live.render_torii_path(data, lang, layout, fonts)))
            out.append((f"feed-{layout}-{lang}", layout, live.render_week(data, NOW, lang, layout, fonts)))
        for k in STATS:
            out.append((f"stat-{k}-{lang}", "small", live.render_stat(k, data, lang, fonts)))
        out.append((f"enso-{lang}", "small", live.render_enso(data, lang, fonts)))
        out.append((f"hours-{lang}", "small", live.render_hours(data, lang, fonts)))
    return out


# ---------------------------------------------------------------- every card


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("layout", LAYOUTS)
def test_torii(data, rfonts, lang, layout):
    svg = live.render_torii_path(data, lang, layout, rfonts)
    _check(svg, layout)
    w, h = (1200, 300) if layout == "desktop" else (600, 420)
    assert f'viewBox="0 0 {w} {h}"' in svg
    assert svg.count('class="gate') == (53 if layout == "desktop" else 26)
    total = f"{data.total_year:,}"
    assert total in visible_strings(svg)
    assert live.LABELS["torii_total"][lang] in visible_strings(svg)


def _last7(data):
    return data.days[-7:]  # the fixture ends on NOW's date


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("layout", LAYOUTS)
def test_week(data, rfonts, lang, layout):
    svg = live.render_week(data, NOW, lang, layout, rfonts)
    _check(svg, layout)
    assert f'viewBox="0 0 {1200 if layout == "desktop" else 600} ' in svg
    assert svg.count('class="slip"') == 7
    vis = visible_strings(svg)
    days = _last7(data)
    # oldest first, today last: dates in order
    dates = [f"{d.month}/{d.day}" for d, _ in days]
    pos = [vis.index(t) for t in dates]
    assert pos == sorted(pos)
    names = live.L("weekdays", lang).split(",")
    for d, c in days:
        assert names[d.weekday()] in vis
        assert f"{c:,}" in vis
    assert live.L("week_total", lang) in vis
    assert f"{sum(c for _, c in days):,}" in vis
    assert live.L("week_today", lang) in vis


def test_week_fortune_tiers():
    assert [live.fortune_tier(n) for n in (0, 1, 9, 10, 29, 30, 49, 50, 500)] == [
        "休", "小吉", "小吉", "中吉", "中吉", "吉", "吉", "大吉", "大吉",
    ]


def test_week_stamps_and_glow(data, rfonts):
    svg = live.render_week(data, NOW, "jp", "desktop", rfonts)
    vis = visible_strings(svg)
    for _d, c in _last7(data):
        assert live.fortune_tier(c) in vis
    assert svg.count('class="slip"') == 7
    assert svg.count('class="peakday"') == 1  # the busiest day glows, once


def test_week_all_zero(data, rfonts):
    zero = replace(data, days=[(d, 0) for d, _ in data.days], total_year=0)
    for lang in LANGS:
        for layout in LAYOUTS:
            svg = live.render_week(zero, NOW, lang, layout, rfonts)
            _check(svg, layout)
            assert svg.count('class="slip"') == 7
            assert visible_strings(svg).count("休") == 7
            assert 'class="peakday"' not in svg


def test_week_today_zero_and_missing_days(data, rfonts):
    today0 = replace(data, days=data.days[:-1] + [(data.days[-1][0], 0)])
    for layout in LAYOUTS:
        svg = live.render_week(today0, NOW, "en", layout, rfonts)
        _check(svg, layout)
        assert svg.count('class="slip"') == 7
    # no data for the last days (e.g. the calendar ends earlier): those days read 0
    short = replace(data, days=data.days[:-3])
    vis = visible_strings(live.render_week(short, NOW, "jp", "desktop", rfonts))
    assert "11/12" in vis and vis.count("休") >= 3
    assert live.week_counts(data.days, NOW) == [c for _, c in _last7(data)]
    assert live.week_counts([], NOW) == [0] * 7


def test_week_has_no_repo_names(data, rfonts):
    svg = live.render_week(data, NOW, "en", "desktop", rfonts) + live.render_week(data, NOW, "jp", "phone", rfonts)
    for e in data.events:
        assert e.repo.split("/")[-1] not in svg
    for name, _ in data.recent_repos:
        assert name.split("/")[-1] not in svg


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("kind", STATS)
def test_stat(data, rfonts, lang, kind):
    svg = live.render_stat(kind, data, lang, rfonts)
    _check(svg, "small")
    assert 'viewBox="0 0 410 200"' in svg
    vis = visible_strings(svg)
    number = {
        "contrib": f"{data.total_year:,}",
        "month": f"{sum(c for _, c in data.days[-30:]):,}",
        "peak": f"{max(c for _, c in data.days):,}",
        "stars": f"{data.stars:,}",
    }[kind]
    assert number in vis


def test_stat_month_and_peak_values(data, rfonts):
    assert live.last_days_total(data.days, 30) == 530
    from datetime import date

    assert live.peak_day(data.days) == (date(2026, 10, 15), 75)
    jp = visible_strings(live.render_stat("month", data, "jp", rfonts))
    assert "530" in jp and "1日平均 17.7" in jp
    en = visible_strings(live.render_stat("month", data, "en", rfonts))
    assert "avg 17.7 a day" in en
    assert "2026年10月15日" in visible_strings(live.render_stat("peak", data, "jp", rfonts))
    assert "Oct 15, 2026" in visible_strings(live.render_stat("peak", data, "en", rfonts))


def test_stat_peak_ties_take_latest_and_zero_has_no_date(data, rfonts):
    from datetime import date

    days = [(date(2026, 1, 1), 5), (date(2026, 2, 1), 5), (date(2026, 1, 15), 1)]
    assert live.peak_day(days) == (date(2026, 2, 1), 5)
    assert live.peak_day([]) is None
    zero = replace(data, days=[(d, 0) for d, _ in data.days], total_year=0)
    for lang in LANGS:
        for kind in STATS:
            svg = live.render_stat(kind, zero, lang, rfonts)
            _check(svg, "small")
    assert live.L("stat_peak_none", "jp") in visible_strings(live.render_stat("peak", zero, "jp", rfonts))


def test_old_stat_kinds_gone(data, rfonts):
    for kind in ("streak", "followers"):
        with pytest.raises(KeyError):
            live.render_stat(kind, data, "jp", rfonts)
    assert not hasattr(live, "render_feed")


@pytest.mark.parametrize("lang", LANGS)
def test_enso(data, rfonts, lang):
    svg = live.render_enso(data, lang, rfonts)
    _check(svg, "small")
    assert 'viewBox="0 0 410 410"' in svg
    vis = visible_strings(svg)
    for name, _b, _c in data.languages[:5]:
        assert name in vis
    assert live.LABELS["other"][lang] in vis
    assert svg.count('class="arc') == 6


@pytest.mark.parametrize("lang", LANGS)
def test_hours(data, rfonts, lang):
    svg = live.render_hours(data, lang, rfonts)
    _check(svg, "small")
    assert 'viewBox="0 0 410 410"' in svg
    vis = visible_strings(svg)
    for k in ("asa", "hiru", "yu", "yoru"):
        assert live.LABELS[f"hour_{k}"][lang] in vis
    assert live.LABELS["public_commits"][lang] in vis


# ---------------------------------------------------------------- behaviour


def test_fit():
    assert live.fit("short", 28) == "short"
    s = live.fit("y" * 40, 28)
    assert len(s) == 28 and s.endswith("…")
    assert live.fit("z" * 28, 28) == "z" * 28


def test_private_names_never_rendered(data, rfonts):
    for name, _kind, svg in _all_cards(data, rfonts):
        for p in data.private_repo_names:
            assert p not in svg, (name, p)


def test_torii_all_zero_renders(data, rfonts):
    zero = replace(data, days=[(d, 0) for d, _ in data.days], total_year=0)
    for lang in LANGS:
        for layout in LAYOUTS:
            svg = live.render_torii_path(zero, lang, layout, rfonts)
            assert_valid_svg(svg)
            assert svg.count('class="gate') == (53 if layout == "desktop" else 26)
    svg = live.render_torii_path(zero, "jp", "desktop", rfonts)
    heights = [float(h) for h in re.findall(r'data-h="([\d.]+)"', svg)]
    assert len(heights) == 53 and set(heights) == {8.0}


def test_torii_gate_height_formula(data, rfonts):
    svg = live.render_torii_path(data, "en", "desktop", rfonts)
    weeks = live.weekly(data.days, 53)
    top = max(1, max(weeks))
    heights = [float(h) for h in re.findall(r'data-h="([\d.]+)"', svg)]
    assert heights == [pytest.approx(8 + 72 * w / top, abs=0.01) for w in weeks]
    assert sum(weeks) <= data.total_year


def test_torii_weekly_shapes(data):
    w = live.weekly(data.days, 53)
    assert len(w) == 53
    assert len(live.weekly(data.days, 26)) == 26
    assert w[-26:] == live.weekly(data.days, 26)
    assert live.weekly([], 53) == [0] * 53


def test_torii_kitsune(data, rfonts):
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x03\x00\x08\xfc\x02\xfe\xa7\x9a\xa0"
        b"\xa0\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    for layout in LAYOUTS:
        svg = live.render_torii_path(data, "jp", layout, rfonts, kitsune_png=png)
        assert_valid_svg(svg)
        assert_no_external(svg)
        assert "data:image/png;base64," in svg
    assert "data:image/png" not in live.render_torii_path(data, "jp", "desktop", rfonts)


def test_torii_kitsune_animated(data, rfonts):
    """The guardian sheet (8 frames in one row) is stepped through and sits clear of the labels."""
    from test_sprites import synthetic_sheet

    sheet = synthetic_sheet(8, 1, 160)
    for layout in LAYOUTS:
        for lang in LANGS:
            svg = live.render_torii_path(data, lang, layout, rfonts, kitsune_png=sheet)
            _check(svg, layout)
            assert "steps(8)" in svg
        x, y, w, h = live.kitsune_box(layout)
        cfg, sz = live.TORII[layout], live.TORII_SIZES[layout]
        assert x + w <= cfg["w"] - 8 and y + h <= cfg["base"] + 26  # on the path, inside the card
        assert y + h <= live.MONTH_Y[layout] - sz["now"]  # above the "this week" label
        if layout == "desktop":
            assert y >= 100 + 8  # below the year total and its label (right column)
        else:
            assert y >= 184 + 8  # below the centred year total
    # the real sheet fits the torii card budget
    real = ROOT_ASSETS / "kitsune-sheet.png"
    if real.exists():
        for layout in LAYOUTS:
            assert_under(live.render_torii_path(data, "jp", layout, rfonts, kitsune_png=real.read_bytes()), 500)


def test_thousands_separators(data, rfonts):
    big = replace(data, total_year=12345, stars=1234, followers=1000)
    assert "12,345" in visible_strings(live.render_stat("contrib", big, "en", rfonts))
    assert "1,234" in visible_strings(live.render_stat("stars", big, "jp", rfonts))
    assert "12,345" in visible_strings(live.render_torii_path(big, "jp", "phone", rfonts))


def test_labels_complete():
    for key, table in live.LABELS.items():
        assert set(table) == {"jp", "en"}, key
        assert all(v.strip() for v in table.values()), key
    for k in ("asa", "hiru", "yu", "yoru"):
        assert live.LABELS[f"hour_{k}"]["jp"] in "朝昼夕夜"
    assert live.LABELS["public_commits"]["jp"] == "公開コミット"
    assert live.LABELS["public_commits"]["en"] == "public commits"


def test_enso_handles_few_languages(data, rfonts):
    one = replace(data, languages=[("Python", 100, "#3572A5")])
    svg = live.render_enso(one, "en", rfonts)
    assert_valid_svg(svg)
    none = replace(data, languages=[])
    assert_valid_svg(live.render_enso(none, "jp", rfonts))


def test_hours_handles_no_commits(data, rfonts):
    svg = live.render_hours(replace(data, commit_times=[]), "jp", rfonts)
    assert_valid_svg(svg)


# ---------------------------------------------------------------- fonts


def _face_cmaps():
    pytest.importorskip("fontTools")
    pytest.importorskip("brotli")
    from fontTools.ttLib import TTFont

    out = {}
    for fam, stem in (("Shrine Serif", "serif"), ("Shrine Mono", "mono")):
        for w in (400, 700):
            out[(fam, w)] = set(TTFont(FONT_DIR / f"runtime-{stem}-{w}.woff2").getBestCmap())
    return out


def _texts(svg: str):
    """(family, weight, text) for every text run, with inherited font attributes."""
    out = []

    def walk(el, fam, w):
        tag = el.tag.rsplit("}", 1)[-1]
        fam = el.get("font-family", fam)
        fw = el.get("font-weight")
        w = int(fw) if fw else w
        if tag in ("text", "tspan") and el.text:
            out.append((fam, w, el.text))
        for c in el:
            walk(c, fam, w)
            if tag in ("text", "tspan") and c.tail and c.tail.strip():
                out.append((fam, w, c.tail))

    walk(ET.fromstring(svg), None, 400)
    return out


def test_live_text_within_runtime_glyphs(data, rfonts):
    cmaps = _face_cmaps()
    serif_any = cmaps[("Shrine Serif", 400)] & cmaps[("Shrine Serif", 700)]
    zero = replace(data, days=[(d, 0) for d, _ in data.days], total_year=0)
    extra = [live.render_week(zero, NOW, lang, layout, rfonts) for lang in LANGS for layout in LAYOUTS] + [
        live.render_stat("peak", zero, lang, rfonts) for lang in LANGS
    ]
    svgs = [s for _n, _k, s in _all_cards(data, rfonts)] + extra
    for svg in svgs:
        runs = _texts(svg)
        assert runs
        for fam, w, text in runs:
            assert fam in ("Shrine Serif", "Shrine Mono"), (fam, text)
            cmap = cmaps[(fam, 700 if w >= 600 else 400)]
            missing = {c for c in text if ord(c) not in cmap and not c.isspace()}
            assert not missing, (fam, w, text, missing)
        # the <title> is in the runtime set too
        title = ET.fromstring(svg).find("{http://www.w3.org/2000/svg}title").text or ""
        assert not {c for c in title if ord(c) not in serif_any and not c.isspace()}, title


def test_live_stdlib_only():
    code = (
        "import sys; sys.modules['fontTools'] = None\n"
        "from pathlib import Path\n"
        "from datetime import datetime, timezone\n"
        "from scripts.generate.github_data import load_fixture\n"
        "from scripts.shrine.cards import live\n"
        "from scripts.shrine.fonts import RuntimeFonts\n"
        "d = load_fixture(Path('tests/fixtures/github'))\n"
        "f = RuntimeFonts()\n"
        "live.render_torii_path(d, 'en', 'desktop', f)\n"
        "live.render_week(d, datetime.now(timezone.utc), 'en', 'phone', f)\n"
        "live.render_hours(d, 'jp', f)\n"
    )
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
