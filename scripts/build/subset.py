"""Build-time font subsetting (dev only: needs fontTools + brotli)."""
from __future__ import annotations

import string
from io import BytesIO
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

from scripts.shrine.fonts import FACES, FONT_DIR, font_face

SOURCES = {
    "serif": "NotoSerifJP-{}.ttf",
    "mono": "JetBrainsMono-{}.ttf",
}
# 2010-01-01 UTC in the font epoch; keeps builds byte-identical
FIXED_TIMESTAMP = 3345148800
WEIGHT_NAME = {400: "Regular", 700: "Bold"}


def subset_woff2(ttf: Path, text: str) -> bytes:
    opts = Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.notdef_outline = True
    opts.hinting = False
    font = TTFont(str(ttf), recalcTimestamp=False)
    sub = Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    font["head"].created = font["head"].modified = FIXED_TIMESTAMP
    font.flavor = "woff2"
    buf = BytesIO()
    font.save(buf)
    return buf.getvalue()


class SubsetFonts:
    def __init__(self, serif_dir: Path, mono_dir: Path) -> None:
        self.dirs = {"serif": Path(serif_dir), "mono": Path(mono_dir)}

    def _bytes(self, stem: str, weight: int, text: str) -> bytes:
        name = SOURCES[stem].format(WEIGHT_NAME[weight])
        return subset_woff2(self.dirs[stem] / name, text)

    def css(self, text: str) -> str:
        return "\n".join(
            font_face(fam, w, self._bytes(stem, w, text)) for fam, stem, w in FACES
        )


def build_runtime_fonts(
    out_dir: Path = FONT_DIR,
    text: str = "",
    *,
    serif_dir: Path,
    mono_dir: Path,
) -> None:
    """Write runtime-{serif,mono}-{400,700}.woff2 for printable ASCII + text."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    chars = string.printable.strip() + " " + text
    sf = SubsetFonts(serif_dir, mono_dir)
    for _fam, stem, w in FACES:
        (out_dir / f"runtime-{stem}-{w}.woff2").write_bytes(sf._bytes(stem, w, chars))
