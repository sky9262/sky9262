import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pytest

from scripts.build import sources  # noqa: E402

# full TTFs for the dev-only subset tests: SHRINE_SERIF_DIR / SHRINE_MONO_DIR
SERIF_DIR = sources.serif_dir()
MONO_DIR = sources.mono_dir()


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
