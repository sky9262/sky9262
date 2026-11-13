"""Build-time conversion of the owner's hero banner video into scene GIFs (dev only: needs ffmpeg).

Source: art-src/banner-raw.mp4 (ChatGPT art, git-excluded): 1920x1080, 24 fps, 5 s,
a moonlit torii right of centre with open sky on the left. Outputs are committed
build inputs in scripts/build/art/, embedded by scripts.shrine.cards.hero.

The clip is drawn to loop, but its last frame lands about two frame steps short
of its first. After decimating to OUT_FPS, the last XFADE output frames are
dissolved into the first XFADE frames (alpha (k+1)/XFADE, so the dissolve
completes on the last frame) and those opening frames are dropped: the GIF ends
on exactly frame XFADE-1 and wraps to frame XFADE, a normal one-frame step. XFADE=3 at 12 fps is the final 6 frames of the 24 fps source.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ART_DIR = Path(__file__).resolve().parent / "art"
OUT_FPS = 12
XFADE = 3  # output frames (= 6 source frames at 24 fps)

# layout -> (crop w:h:x:y in source pixels, output w:h)
CROPS = {
    # Full width, from just above the moon down to the lantern and torii bases.
    "desktop": ("1920:800:0:60", "1200:500"),
    # Torii, moon, both lanterns, their bases and some lit ground (the phone card
    # fades the bottom edge into the name block); 1200x860 matches 600x430.
    "phone": ("1200:860:720:50", "600:430"),
}

PALETTE = (
    "split[a][b];"
    "[a]palettegen=max_colors=128:stats_mode=diff[p];"
    "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle"
)


def _probe(src: Path) -> tuple[int, float]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames,r_frame_rate", "-of", "json", str(src)],
        capture_output=True, check=True, text=True,
    ).stdout
    st = json.loads(out)["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    return int(st["nb_read_frames"]), int(num) / int(den)


def filter_graph(crop: str, size: str, frames: int, fps: float, xfade: int = XFADE) -> str:
    """Crop/scale to OUT_FPS, crossfade the tail into the head, then a 128-colour GIF palette."""
    n = round(frames * OUT_FPS / fps)  # output frames before the crossfade
    w, h = size.split(":")
    # blend's N is not reliably 0-based, so alpha keys off the tail's own timestamp.
    alpha = f"(round(T*{OUT_FPS})+1)/{xfade}"
    return (
        f"[0:v]crop={crop},scale={w}:{h}:flags=lanczos,fps={OUT_FPS},split=3[x0][x1][x2];"
        f"[x0]trim=start_frame={xfade}:end_frame={n - xfade},setpts=PTS-STARTPTS[mid];"
        f"[x1]trim=start_frame={n - xfade},setpts=PTS-STARTPTS[tail];"
        f"[x2]trim=end_frame={xfade},setpts=PTS-STARTPTS[head];"
        f"[tail][head]blend=all_expr='A+(B-A)*{alpha}'[fade];"
        f"[mid][fade]concat=n=2:v=1:a=0,{PALETTE}"
    )


def build_scene_gifs(src: Path, out_dir: Path = ART_DIR) -> dict[str, Path]:
    """Write hero-scene-{desktop,phone}.gif into out_dir; returns layout -> path."""
    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames, fps = _probe(src)
    out: dict[str, Path] = {}
    for layout, (crop, size) in CROPS.items():
        dest = out_dir / f"hero-scene-{layout}.gif"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(src),
             "-filter_complex", filter_graph(crop, size, frames, fps),
             "-loop", "0", str(dest)],
            check=True,
        )
        out[layout] = dest
    return out


if __name__ == "__main__":
    import sys

    root = Path(__file__).resolve().parents[2]
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "art-src" / "banner-raw.mp4"
    for layout, path in build_scene_gifs(src).items():
        print(f"{layout}: {path} ({path.stat().st_size / 1024:.0f} KB)")
