import base64
import re

import pytest

from conftest import MONO_DIR, SERIF_DIR
from scripts.shrine.svg import document, embed_fonts

TEXT = "アカシュ・クマァ Akash"


def _subset():
    pytest.importorskip("fontTools")
    pytest.importorskip("brotli")
    if not (SERIF_DIR / "NotoSerifJP-Regular.ttf").exists() or not (
        MONO_DIR / "JetBrainsMono-Regular.ttf"
    ).exists():
        pytest.skip("font sources absent")
    from scripts.build.subset import SubsetFonts

    return SubsetFonts(SERIF_DIR, MONO_DIR)


def _woffs(css: str) -> list[bytes]:
    return [base64.b64decode(m) for m in re.findall(r"base64,([A-Za-z0-9+/=]+)", css)]


def test_subset_covers_used_glyphs():
    from io import BytesIO

    from fontTools.ttLib import TTFont

    css = _subset().css(TEXT)
    faces = _woffs(css)
    assert len(faces) == 4
    serif = TTFont(BytesIO(faces[0]))
    cmap = serif.getBestCmap()
    for ch in TEXT:
        assert ord(ch) in cmap, ch
    mono = TTFont(BytesIO(faces[2])).getBestCmap()
    for ch in "Akash":
        assert ord(ch) in mono


def test_subset_is_small():
    css = _subset().css(TEXT)
    assert len(css.encode()) < 60 * 1024, len(css.encode())


def test_embed_fonts_injects_face_once():
    svg = document(
        200, 60, '<text x="0" y="20" font-size="16">アカシュ Akash</text>', title="t"
    )
    out = embed_fonts(svg, _subset())
    assert out.count('@font-face{font-family:"Shrine Serif";font-weight:400') == 1
    assert out.count('@font-face{font-family:"Shrine Mono";font-weight:700') == 1
    assert out.count("<style>") == 1


def test_embed_fonts_collects_only_text_nodes():
    seen = []

    class Spy:
        def css(self, text):
            seen.append(text)
            return ""

    svg = document(
        100, 40, '<text x="0" y="9">ab<tspan>cd</tspan></text><g aria-label="zz"/>', title="Title"
    )
    embed_fonts(svg, Spy())
    assert "abcd" in seen[0] and "zz" not in seen[0] and "Title" not in seen[0]


def test_build_runtime_fonts_and_runtime_reads(tmp_path):
    pytest.importorskip("fontTools")
    from scripts.build.subset import build_runtime_fonts

    _subset()
    build_runtime_fonts(tmp_path, "桜", serif_dir=SERIF_DIR, mono_dir=MONO_DIR)
    names = sorted(p.name for p in tmp_path.glob("runtime-*.woff2"))
    assert names == [
        "runtime-mono-400.woff2", "runtime-mono-700.woff2",
        "runtime-serif-400.woff2", "runtime-serif-700.woff2",
    ]
    from scripts.shrine.fonts import RuntimeFonts

    css = RuntimeFonts(tmp_path).css("ignored")
    assert css.count("@font-face") == 4


def test_runtime_fonts_reads_files():
    from scripts.shrine.fonts import FONT_DIR, RuntimeFonts

    if not list(FONT_DIR.glob("runtime-*.woff2")):
        pytest.skip("runtime fonts not generated")
    css = RuntimeFonts().css("x")
    assert '@font-face{font-family:"Shrine Serif";font-weight:400' in css
    assert css.count("base64,") == 4


def test_font_source_dirs_from_env(monkeypatch, tmp_path):
    from scripts.build import sources

    monkeypatch.delenv("SHRINE_SERIF_DIR", raising=False)
    monkeypatch.delenv("SHRINE_MONO_DIR", raising=False)
    assert sources.serif_dir() == sources.CACHE / "serif"
    assert sources.mono_dir() == sources.CACHE
    monkeypatch.setenv("SHRINE_SERIF_DIR", str(tmp_path / "s"))
    monkeypatch.setenv("SHRINE_MONO_DIR", str(tmp_path / "m"))
    assert sources.serif_dir() == tmp_path / "s"
    assert len(sources.missing()) == 4


def test_build_fails_clearly_without_font_sources(monkeypatch, tmp_path, capsys):
    pytest.importorskip("fontTools")
    from scripts.build import __main__ as b

    monkeypatch.setenv("SHRINE_SERIF_DIR", str(tmp_path / "nope"))
    monkeypatch.setenv("SHRINE_MONO_DIR", str(tmp_path / "nope"))
    monkeypatch.setattr("sys.argv", ["scripts.build", "--output-branch", "output-test"])
    with pytest.raises(SystemExit) as ei:
        b.main()
    assert ei.value.code == 2
    err = capsys.readouterr().err
    assert "font sources missing" in err and "SHRINE_SERIF_DIR" in err
    assert "NotoSerifJP-Regular.ttf" in err
