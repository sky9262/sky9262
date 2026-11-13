"""Where the dev-only font sources (full TTFs) live. Stdlib only.

SHRINE_SERIF_DIR: NotoSerifJP-{Regular,Bold}.ttf (default ~/.cache/shrine-fonts/serif)
SHRINE_MONO_DIR:  JetBrainsMono-{Regular,Bold}.ttf (default ~/.cache/shrine-fonts)
See scripts/shrine/fonts/README.md for where to get them.
"""
from __future__ import annotations

import os
from pathlib import Path

CACHE = Path.home() / ".cache" / "shrine-fonts"
REQUIRED = {
    "serif": ("NotoSerifJP-Regular.ttf", "NotoSerifJP-Bold.ttf"),
    "mono": ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf"),
}
ENV = {"serif": "SHRINE_SERIF_DIR", "mono": "SHRINE_MONO_DIR"}


def _dir(env: str, default: Path) -> Path:
    v = os.environ.get(env, "").strip()
    return Path(v).expanduser() if v else default


def serif_dir() -> Path:
    return _dir(ENV["serif"], CACHE / "serif")


def mono_dir() -> Path:
    return _dir(ENV["mono"], CACHE)


def missing() -> list[Path]:
    """Every required TTF that is not there (empty when the build can run)."""
    dirs = {"serif": serif_dir(), "mono": mono_dir()}
    return [dirs[k] / f for k, files in REQUIRED.items() for f in files if not (dirs[k] / f).is_file()]
