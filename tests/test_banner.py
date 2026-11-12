import shutil
import struct
import subprocess
from array import array
from pathlib import Path
from statistics import median

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "banner-raw.mp4"
SIZES = {"desktop": (1200, 500), "phone": (600, 430)}


def _gif_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:10]
    assert head[:6] in (b"GIF87a", b"GIF89a")
    return struct.unpack("<HH", head[6:10])


def _frame_steps(path: Path) -> list[float]:
    """Low-frequency brightness step between consecutive frames, incl. last -> first.

    Frames are area-averaged to 48x20 and read as float, so 1-level rounding and
    dither noise do not mask a pop at the loop wrap.
    """
    w, h = 48, 20
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf",
         f"scale={w}:{h}:flags=area,format=grayf32le", "-f", "rawvideo", "-"],
        capture_output=True, check=True,
    ).stdout
    vals = array("f")
    vals.frombytes(raw)
    n = w * h
    frames = [vals[i:i + n] for i in range(0, len(vals), n)]
    frames.append(frames[0])  # the loop wrap
    return [
        255 * sum(abs(a - b) for a, b in zip(f, g)) / n for f, g in zip(frames, frames[1:])
    ]


def test_build_scene_gifs(tmp_path):
    if not shutil.which("ffmpeg") or not SRC.exists():
        pytest.skip("ffmpeg or art-src/banner-raw.mp4 absent")
    from scripts.build.banner import build_scene_gifs

    out = build_scene_gifs(SRC, tmp_path)
    assert set(out) == {"desktop", "phone"}
    for layout, path in out.items():
        assert path.name == f"hero-scene-{layout}.gif"
        assert _gif_size(path) == SIZES[layout]
        assert path.stat().st_size <= 1.1 * 1024 * 1024, f"{path.name} too big"
        steps = _frame_steps(path)
        assert len(steps) >= 40
        typical = median(steps[:-1])
        # seamless loop: the wrap is no bigger a jump than a typical frame step,
        # and the tail -> head dissolve before it has no hard pop either
        assert steps[-1] <= 1.25 * typical, (steps[-1], typical)
        assert max(steps) <= 3.5 * typical, (max(steps), typical)
