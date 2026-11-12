"""Static build: python -m scripts.build [--output-branch output|output-test]."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from scripts.build.readme import FILE, render_readme
from scripts.build.subset import SubsetFonts, build_runtime_fonts
from scripts.shrine import content, labels
from scripts.shrine.cards.achievement import render_achievement
from scripts.shrine.cards.button import render_button, render_toggle
from scripts.shrine.cards.cando import render_cando
from scripts.shrine.cards.connect import render_connect
from scripts.shrine.cards.hero import render_hero
from scripts.shrine.cards.plaque import render_plaque
from scripts.shrine.cards.stack import render_stack
from scripts.shrine.fonts import FONT_DIR

ROOT = Path(__file__).resolve().parent.parent.parent
ART = Path(__file__).resolve().parent / "art"
SERIF_DIR = Path(os.environ.get(
    "SHRINE_SERIF_DIR", "/Users/kumar.akash/Downloads/My Projects/portfolio-v2/public/fonts"))
MONO_DIR = Path(os.environ.get("SHRINE_MONO_DIR", Path.home() / ".cache/shrine-fonts"))
LANGS = ("jp", "en")
LAYOUTS = ("desktop", "phone")
LIVE_PLAQUE = "phisheye"


def runtime_text() -> str:
    """Every string the live cards can render: labels plus the phishEye plaque."""
    parts: list[str] = []
    for table in labels.LABELS.values():
        parts += [str(v) for v in table.values()]
    p = next(p for p in content.PLAQUES if p.id == LIVE_PLAQUE)
    for t in (p.title, p.subtitle, p.lines, content.NDA):
        parts += [t.jp, t.en]
    parts += p.tags + [p.years]
    parts += ["★", "⑂"]
    return "".join(parts)


def _write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def build(output_branch: str) -> None:
    build_runtime_fonts(FONT_DIR, runtime_text(), serif_dir=SERIF_DIR, mono_dir=MONO_DIR)
    fonts = SubsetFonts(SERIF_DIR, MONO_DIR)
    assets = ROOT / "assets"
    for lang in LANGS:
        d = assets / lang
        for layout in LAYOUTS:
            gif = ART / f"hero-scene-{layout}.gif"
            _write(d / f"hero-{layout}.svg", render_hero(
                lang, layout, fonts, gif.read_bytes() if gif.exists() else None))
            _write(d / f"cando-{layout}.svg", render_cando(lang, layout, fonts))
            _write(d / f"stack-{layout}.svg", render_stack(lang, layout, fonts))
            _write(d / f"connect-{layout}.svg", render_connect(lang, layout, fonts))
        for i, p in enumerate(content.active_plaques()):
            if p.id != LIVE_PLAQUE:
                _write(d / f"plaque-{p.id}.svg", render_plaque(p, lang, i, fonts))
        for aid, _t, _d in content.ACHIEVEMENTS:
            _write(d / f"achievement-{aid}.svg", render_achievement(aid, lang, fonts))
        _write(d / "toggle.svg", render_toggle(lang, fonts))
        _write(ROOT / FILE[lang], render_readme(lang, output_branch))
    for lid, _label, _url in content.LINKS:
        _write(assets / "common" / f"btn-{lid}.svg", render_button(lid, fonts))


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m scripts.build")
    ap.add_argument("--output-branch", choices=("output", "output-test"), default="output")
    build(ap.parse_args().output_branch)


if __name__ == "__main__":
    main()
