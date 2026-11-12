import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FILES = {"jp": ROOT / "README.md", "en": ROOT / "README-EN.md"}
OUT = "https://raw.githubusercontent.com/sky9262/sky9262/"
JP_CHARS = re.compile(r"[぀-ヿ一-鿿]")
HERO_SVG = re.compile(r"hero-[a-z]+\.svg$")
LIVE = re.compile(r'(?:src|srcset)="(https://[^"]+)"')


def _read(lang: str) -> str:
    return FILES[lang].read_text(encoding="utf-8")


def _srcs(text: str) -> list[str]:
    return re.findall(r'(?:src|srcset)="([^"]+)"', text)


def test_readme_assets_exist():
    for lang in FILES:
        for s in _srcs(_read(lang)):
            if s.startswith("http"):
                continue
            assert (ROOT / s).exists(), f"{lang}: missing {s}"


def test_readme_output_urls():
    for lang in FILES:
        text = _read(lang)
        live = [u for u in _srcs(text) if u.startswith(OUT)]
        assert live, f"{lang}: no live images"
        assert all("/output-test/" in u for u in live), live
        assert f"/{lang}/plaque-phisheye.svg" in text
        for name in ("torii-desktop", "torii-phone", "feed-desktop", "feed-phone",
                     "stat-contrib", "stat-streak", "stat-stars", "stat-followers",
                     "enso", "hours"):
            assert f"/{lang}/{name}.svg" in text, name


def test_toggle_links():
    assert 'href="README-EN.md"' in _read("jp")
    assert 'href="README.md"' in _read("en")
    assert "README.md" not in _read("jp").replace("README-EN.md", "")


def test_alt_language():
    for lang in FILES:
        alts = re.findall(r'alt="([^"]*)"', _read(lang))
        assert alts
        for a in alts:
            assert a, "empty alt"
            if lang == "jp":
                assert JP_CHARS.search(a), a
            else:
                assert a.isascii(), a
    for lang in FILES:
        text = _read(lang)
        assert text.count("<img") == len(re.findall(r'<img [^>]*alt="', text))


def test_no_pending_plaques():
    for lang in FILES:
        text = _read(lang)
        assert "client_a" not in text and "oss_b" not in text


def test_structure():
    for lang in FILES:
        text = _read(lang)
        assert text.count('media="(max-width: 600px)"') == 6  # hero, can-do, stack, torii, feed, connect
    assert len(re.findall(r"<picture>", _read("jp"))) == len(
        re.findall(r"<picture>", _read("en"))
    )


def test_assets_budget():
    files = [f for f in (ROOT / "assets").rglob("*") if f.is_file()]
    assert files
    for f in files:
        rel = f.relative_to(ROOT / "assets").as_posix()
        limit = 1536 if re.fullmatch(r"(jp|en)/hero-[a-z]+\.svg", rel) else 500
        assert f.stat().st_size <= limit * 1024, f"{rel}: {f.stat().st_size} B > {limit} KB"


@pytest.mark.network
def test_github_renders_picture():
    r = subprocess.run(
        ["gh", "api", "markdown", "-f", "mode=gfm", "-F", f"text=@{FILES['jp']}"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert 'media="(max-width: 600px)"' in r.stdout
