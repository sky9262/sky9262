"""Font embedding interface and the stdlib-only runtime font set."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Protocol

FONT_DIR = Path(__file__).resolve().parent / "fonts"

# (css family, file stem, weight)
FACES = (
    ("Shrine Serif", "serif", 400),
    ("Shrine Serif", "serif", 700),
    ("Shrine Mono", "mono", 400),
    ("Shrine Mono", "mono", 700),
)


class FontSet(Protocol):
    def css(self, text: str) -> str: ...


def font_face(family: str, weight: int, woff2: bytes) -> str:
    b64 = base64.b64encode(woff2).decode("ascii")
    return (
        f'@font-face{{font-family:"{family}";font-weight:{weight};font-style:normal;'
        f'src:url(data:font/woff2;base64,{b64}) format("woff2")}}'
    )


class RuntimeFonts:
    """Reads prebuilt scripts/shrine/fonts/runtime-*.woff2; css() ignores text."""

    def __init__(self, font_dir: Path = FONT_DIR) -> None:
        self.font_dir = Path(font_dir)

    def css(self, text: str = "") -> str:
        return "\n".join(
            font_face(fam, w, (self.font_dir / f"runtime-{stem}-{w}.woff2").read_bytes())
            for fam, stem, w in FACES
        )
