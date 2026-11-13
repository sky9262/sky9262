"""Dev-only: downscale the owner's TryHackMe badge images into committed build inputs.

    python -m scripts.build.thm_art <dir with <slug>.png>    # -> scripts/build/art/thm/<slug>.png

The originals are TryHackMe's public badge images
(https://assets.tryhackme.com/img/badges/<slug>.png, 425x500 RGBA), downloaded once
by hand. Each is scaled with LANCZOS to THM_PX tall and quantised to a palette PNG
with alpha, so the shelf card embeds ten of them well under its 500 KB budget.
Pillow is a dev dependency (requirements-dev.txt); nothing under scripts/shrine
imports this module.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

from scripts.shrine.content import THM_BADGES

THM_PX = 144
OUT = Path(__file__).resolve().parent / "art" / "thm"


def shrink(src: Path, dst: Path, px: int = THM_PX) -> None:
    im = Image.open(src).convert("RGBA")
    w = round(im.width * px / im.height)
    im = im.resize((w, px), Image.LANCZOS)
    im.quantize(colors=256, method=Image.Quantize.FASTOCTREE).save(dst, optimize=True)


def main(src_dir: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, _name in THM_BADGES:
        shrink(Path(src_dir) / f"{slug}.png", OUT / f"{slug}.png")
        print(OUT / f"{slug}.png")


if __name__ == "__main__":
    main(sys.argv[1])
