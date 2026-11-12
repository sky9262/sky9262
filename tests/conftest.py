import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pytest

SERIF_DIR = Path("/Users/kumar.akash/Downloads/My Projects/portfolio-v2/public/fonts")
MONO_DIR = Path.home() / ".cache/shrine-fonts"


@pytest.fixture(scope="session")
def fonts():
    """Per-SVG subset fonts (dev only); skips when fontTools or the sources are absent."""
    pytest.importorskip("fontTools")
    pytest.importorskip("brotli")
    if not (SERIF_DIR / "NotoSerifJP-Regular.ttf").exists() or not (
        MONO_DIR / "JetBrainsMono-Regular.ttf"
    ).exists():
        pytest.skip("font sources absent")
    from scripts.build.subset import SubsetFonts

    return SubsetFonts(SERIF_DIR, MONO_DIR)
