"""Dev-only: turn the owner's ChatGPT sprite art into small, clean sprite sheets.

    python -m scripts.build.sprites            # art-src/*-raw.png -> committed sheets

The raw art (art-src/, git-excluded) is a 4x2 grid of frames on transparency, but
the grid is not integer (443.5 px cells), nothing is fully opaque, a third of the
pixels are faint glow speckle in garbage colours, and the character drifts from
frame to frame. normalize_sheet() fixes all of that:

  1. alpha clean-up: alpha < ALPHA_FLOOR is zeroed (the speckle lives there), then
     alpha is soft-thresholded, ALPHA_FLOOR..ALPHA_FULL -> 0..255, so the body is
     fully opaque and the anti-aliased edge stays soft;
  2. the remaining fringe (alpha < FRINGE_HI) is recoloured from the nearest solid
     pixels, so no garbage colour survives on any background;
  3. frames are segmented by each cell's alpha (split at the emptiest line near the
     nominal cell border), not by fixed integer slicing;
  4. every frame is registered to frame 0: a shared baseline (lowest solid pixel,
     the feet) and the horizontal shift that best overlaps frame 0's silhouette;
  5. one shared square box around all frames is scaled with LANCZOS (premultiplied)
     to frame_px, laid out as one row (or the source grid), and quantised to a
     256-colour palette PNG with alpha.

Fallback: art on a flat #0b0e22 background (no alpha) is keyed out first.

Pillow and numpy are dev dependencies (requirements-dev.txt); nothing under
scripts/shrine imports this module.
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
ART_SRC = ROOT / "art-src"

ALPHA_FLOOR = 40  # below: glow speckle, zeroed
ALPHA_FULL = 245  # at/above: fully opaque (the raw body sits at 250-254)
SOLID = 128  # cleaned alpha that counts as body for recolouring / alignment
FRINGE_HI = 128  # cleaned alpha below this is "fringe" and gets despeckled
STRAY_R = 24  # px: fringe with no solid pixel this close is a stray speck
SPECKLE_R = 3  # px: neighbourhood for the fringe colour check
OUTLIER = 80  # max channel distance from the neighbourhood colour before recolouring
KEY_BG = (0x0B, 0x0E, 0x22)
MAX_SHIFT = 40  # px (source scale) searched when registering frames
DUST = 16  # alpha left by LANCZOS ringing after the downscale, zeroed
PAD = 0.04  # margin around the shared box, as a fraction of its side


# ---------------------------------------------------------------- alpha + colour


def _key_out(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Alpha from the distance to the flat key colour; colour un-mixed from it."""
    bg = np.array(KEY_BG, dtype=np.float32)
    d = np.abs(rgb - bg).max(axis=2)
    a = np.clip((d - 10) / 50, 0, 1)
    safe = np.maximum(a, 1e-3)[..., None]
    rgb = np.clip((rgb - bg * (1 - a[..., None])) / safe, 0, 255)
    return rgb, a * 255


def _box(arr: np.ndarray, r: int) -> np.ndarray:
    """Box sum over a (2r+1)^2 window (edges clamped), via summed-area tables."""
    pad = np.pad(arr, [(r + 1, r), (r + 1, r)] + [(0, 0)] * (arr.ndim - 2), mode="constant")
    s = pad.cumsum(0).cumsum(1)
    k = 2 * r + 1
    return s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]


def _recolour_fringe(rgb: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Clean the faint fringe (0 < alpha < FRINGE_HI) that survives the floor.

    Rim light and lantern glow there are real colour, so they are kept; what goes
    is what does not belong: fringe pixels with no solid pixel within STRAY_R are
    dropped (alpha 0), and a fringe pixel whose colour is an outlier from its
    alpha-weighted neighbourhood (garbage speckle is incoherent, glow is smooth)
    takes the neighbourhood colour."""
    out = rgb.copy()
    fringe = (a > 0) & (a < FRINGE_HI)
    solid = (a >= SOLID).astype(np.float32)
    a[fringe & (_box(solid, STRAY_R) == 0)] = 0
    fringe &= a > 0
    w = a / 255
    mean = _box(rgb * w[..., None], SPECKLE_R) / np.maximum(_box(w, SPECKLE_R), 1e-6)[..., None]
    bad = fringe & (np.abs(rgb - mean).max(axis=2) > OUTLIER)
    out[bad] = mean[bad]
    return out


# ---------------------------------------------------------------- segmentation + registration


def _splits(profile: np.ndarray, n: int) -> list[int]:
    """n+1 boundaries: 0, the emptiest line near each nominal border k*len/n, len."""
    size = len(profile)
    out = [0]
    for k in range(1, n):
        nominal = k * size / n
        lo, hi = int(nominal - size / n * 0.3), int(nominal + size / n * 0.3)
        window = profile[lo:hi]
        best = window.min()
        idx = np.flatnonzero(window == best)
        # centre of the run of emptiest lines closest to the nominal border
        runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
        run = min(runs, key=lambda r: abs(lo + (r[0] + r[-1]) / 2 - nominal))
        out.append(lo + int((run[0] + run[-1]) // 2))
    out.append(size)
    return out


def _cells(a: np.ndarray, cols: int, rows: int) -> list[tuple[int, int, int, int]]:
    """(x0, y0, x1, y1) per frame, row-major."""
    strong = a >= SOLID
    ys = _splits(strong.sum(1), rows)
    cells = []
    for r in range(rows):
        band = strong[ys[r]:ys[r + 1]]
        xs = _splits(band.sum(0), cols)
        cells += [(xs[c], ys[r], xs[c + 1], ys[r + 1]) for c in range(cols)]
    return cells


def _shift(ref: np.ndarray, mov: np.ndarray) -> int:
    """Horizontal shift of `mov` (same height, bottom-aligned) that best overlaps `ref`."""
    best, best_dx = None, 0
    w = max(ref.shape[1], mov.shape[1]) + 2 * MAX_SHIFT
    h = max(ref.shape[0], mov.shape[0])

    def place(m: np.ndarray, dx: int) -> np.ndarray:
        c = np.zeros((h, w), dtype=np.float32)
        c[h - m.shape[0]:, MAX_SHIFT + dx:MAX_SHIFT + dx + m.shape[1]] = m
        return c

    r = place(ref, 0)
    for dx in range(-MAX_SHIFT, MAX_SHIFT + 1):
        cost = np.abs(r - place(mov, dx)).sum()
        if best is None or cost < best:
            best, best_dx = cost, dx
    return best_dx


# ---------------------------------------------------------------- main entry


def normalize_sheet(
    src: Path,
    cols: int,
    rows: int,
    frame_px: int,
    *,
    key_out: bool | None = None,
    layout: str = "row",
) -> bytes:
    """Clean, register and shrink a cols x rows sprite sheet; returns palette PNG bytes.

    Output: one row of cols*rows frames (layout="row") or the source grid
    (layout="grid"), each frame_px square. key_out=None keys out a flat #0b0e22
    background only when the source has no transparency."""
    im = Image.open(src).convert("RGBA")
    px = np.asarray(im).astype(np.float32)
    rgb, a = px[..., :3], px[..., 3]
    if key_out or (key_out is None and a.min() >= 255):
        rgb, a = _key_out(rgb)

    a = np.where(a < ALPHA_FLOOR, 0, np.clip((a - ALPHA_FLOOR) / (ALPHA_FULL - ALPHA_FLOOR), 0, 1) * 255)
    rgb = _recolour_fringe(rgb, a)
    rgb[a == 0] = 0

    frames = []
    for x0, y0, x1, y1 in _cells(a, cols, rows):
        fa, frgb = a[y0:y1, x0:x1], rgb[y0:y1, x0:x1]
        ys, xs = np.nonzero(fa > 0)
        if not len(xs):
            raise ValueError(f"empty frame in cell {(x0, y0, x1, y1)}")
        # crop to visible content; baseline = lowest solid pixel (the feet)
        cy0, cy1, cx0, cx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        fa, frgb = fa[cy0:cy1, cx0:cx1], frgb[cy0:cy1, cx0:cx1]
        solid_rows = np.flatnonzero((fa >= SOLID).any(1))
        base = int(solid_rows.max()) + 1 if len(solid_rows) else fa.shape[0]
        frames.append((frgb, fa, base))

    # register: silhouettes above the baseline, bottom-aligned, shifted onto frame 0
    sil = [(fa[:base] >= SOLID).astype(np.float32) for _, fa, base in frames]
    dxs = [0] + [_shift(sil[0], s) for s in sil[1:]]

    # shared box around every frame, anchored at (frame-0 left edge, baseline)
    left = min(dx for dx in dxs)
    right = max(dx + f[1].shape[1] for dx, f in zip(dxs, frames))
    up = max(base for _, _, base in frames)
    down = max(fa.shape[0] - base for _, fa, base in frames)
    bw, bh = right - left, up + down
    side = int(round(max(bw, bh) * (1 + 2 * PAD)))
    ox = (side - bw) // 2 - left
    oy = side - int(round(side * PAD)) - down - up  # feet on a shared line near the bottom

    out_frames = []
    for (frgb, fa, base), dx in zip(frames, dxs):
        canvas = np.zeros((side, side, 4), dtype=np.float32)
        y = oy + up - base
        x = ox + dx
        canvas[y:y + fa.shape[0], x:x + fa.shape[1], :3] = frgb
        canvas[y:y + fa.shape[0], x:x + fa.shape[1], 3] = fa
        img = Image.fromarray(np.clip(canvas + 0.5, 0, 255).astype(np.uint8), "RGBA")
        img = img.resize((frame_px, frame_px), Image.Resampling.LANCZOS)  # premultiplied
        q = np.asarray(img).copy()
        q[q[..., 3] < DUST] = 0  # LANCZOS ringing beyond the edge
        out_frames.append(Image.fromarray(q, "RGBA"))

    n = cols * rows
    gc, gr = (n, 1) if layout == "row" else (cols, rows)
    sheet = Image.new("RGBA", (gc * frame_px, gr * frame_px), (0, 0, 0, 0))
    for i, f in enumerate(out_frames):
        sheet.paste(f, ((i % gc) * frame_px, (i // gc) * frame_px))
    pal = sheet.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    buf = io.BytesIO()
    pal.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


SHEETS = {
    # raw art -> (output, cols, rows, frame_px)
    "kitsune-guardian-raw.png": (ROOT / "assets" / "common" / "kitsune-sheet.png", 4, 2, 160),
    "kitsune-walker-raw.png": (ROOT / "scripts" / "build" / "art" / "walker-sheet.png", 4, 2, 128),
}


def main() -> None:
    for name, (out, cols, rows, frame) in SHEETS.items():
        data = normalize_sheet(ART_SRC / name, cols, rows, frame)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        print(f"{out.relative_to(ROOT)}: {len(data)} B")


if __name__ == "__main__":
    main()
