"""Kitsune sprites: stepped CSS sprite SVGs (stdlib) and the dev-only sheet normaliser.

The sprite_svg / divider tests build their sheets with zlib + struct so they run
without Pillow; only the normalize_sheet tests need it (and skip without it).
"""
import ast
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from helpers import assert_no_external, assert_under, assert_valid_svg

ROOT = Path(__file__).resolve().parent.parent


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def png_rgba(w: int, h: int, pixel) -> bytes:
    """A w x h RGBA PNG; pixel(x, y) -> (r, g, b, a)."""
    raw = b"".join(b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(w)) for y in range(h))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def synthetic_sheet(cols: int = 4, rows: int = 2, frame: int = 16) -> bytes:
    """cols x rows frames, each a differently coloured square on transparency."""

    def px(x, y):
        i = (y // frame) * cols + x // frame
        fx, fy = x % frame, y % frame
        inside = 3 <= fx < frame - 3 and 3 <= fy < frame - 1
        return (40 * i % 256, 200, 255 - 30 * i, 255) if inside else (0, 0, 0, 0)

    return png_rgba(cols * frame, rows * frame, px)


SHEET = synthetic_sheet()


# ---------------------------------------------------------------- sprite_svg (stdlib)


def test_sprite_svg_valid():
    from scripts.shrine.sprite import sprite_svg

    svg = sprite_svg(SHEET, 4, 2, 16, 8)
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert svg.count("<image") == 1
    assert 'href="data:image/png;base64,' in svg
    assert "<clipPath" in svg and 'clip-path="url(#' in svg
    assert 'viewBox="0 0 16 16"' in svg


def test_sprite_svg_has_steps():
    from scripts.shrine.sprite import sprite_svg

    grid = sprite_svg(SHEET, 4, 2, 16, 8)
    assert "steps(" in grid
    # 4x2 grid: x steps through the 4 columns every 0.5 s, y through the 2 rows every 1 s
    assert re.search(r"0\.5s steps\(4\) infinite", grid)
    assert re.search(r"1s steps\(2\) infinite", grid)
    assert "translateX(-64px)" in grid and "translateY(-32px)" in grid

    row = sprite_svg(synthetic_sheet(8, 1), 8, 1, 16, 10)
    assert re.search(r"0\.8s steps\(8\) infinite", row)
    assert "translateY" not in row


def test_sprite_svg_under_budget():
    from scripts.shrine.sprite import sprite_svg

    svg = sprite_svg(SHEET, 4, 2, 16, 8)
    assert_under(svg, 500)
    assert len(svg.encode()) < len(SHEET) * 4 / 3 + 2048  # the sheet plus a small wrapper


def test_sprite_svg_walk_across():
    from scripts.shrine.sprite import sprite_svg

    svg = sprite_svg(synthetic_sheet(8, 1), 8, 1, 16, 12, walk_across=300)
    assert_valid_svg(svg)
    assert re.search(r"14s linear infinite", svg)
    assert "translateX(-16px)" in svg and "translateX(300px)" in svg
    assert 'viewBox="0 0 300 16"' in svg
    assert "14s" not in sprite_svg(SHEET, 4, 2, 16, 8)


def test_sprite_parts_prefixed():
    """Two sprites in one card must not share ids or keyframe names."""
    from scripts.shrine.sprite import sprite_parts

    a = "".join(sprite_parts(SHEET, 4, 2, 16, 8, uid="ka"))
    b = "".join(sprite_parts(SHEET, 4, 2, 16, 8, uid="kb"))
    ids_a = set(re.findall(r'id="([^"]+)"', a)) | set(re.findall(r"@keyframes (\w+)", a))
    ids_b = set(re.findall(r'id="([^"]+)"', b)) | set(re.findall(r"@keyframes (\w+)", b))
    assert ids_a and not ids_a & ids_b


def test_png_size():
    from scripts.shrine.sprite import png_size

    assert png_size(SHEET) == (64, 32)
    with pytest.raises(ValueError):
        png_size(b"\x89PNG fake")


def test_sprite_stdlib_only():
    """sprite.py ships with the CI generator: stdlib imports only, Pillow never loaded."""
    src = (ROOT / "scripts" / "shrine" / "sprite.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            names = [node.module]
        else:
            continue
        for n in names:
            assert n.split(".")[0] in sys.stdlib_module_names or n == "__future__", n
    code = (
        "import sys\n"
        "sys.modules['PIL'] = None; sys.modules['numpy'] = None\n"
        "import scripts.shrine.sprite, scripts.shrine.cards.divider\n"
        "assert not any(m.split('.')[0] in ('PIL', 'numpy') and sys.modules[m] for m in sys.modules)\n"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------- walker divider


def test_divider():
    from scripts.shrine.cards.divider import render_divider

    svg = render_divider(synthetic_sheet(8, 1, 32))
    assert_valid_svg(svg)
    assert_no_external(svg)
    assert_under(svg, 500)
    assert 'viewBox="0 0 1200 140"' in svg
    assert "steps(8)" in svg and "14s linear infinite" in svg
    assert "<text" not in svg  # language-neutral


def test_committed_sprite_assets():
    from scripts.shrine.sprite import png_size

    sheet = ROOT / "assets" / "common" / "kitsune-sheet.png"
    assert sheet.stat().st_size <= 120 * 1024
    assert png_size(sheet.read_bytes()) == (8 * 160, 160)
    walker = ROOT / "scripts" / "build" / "art" / "walker-sheet.png"
    assert png_size(walker.read_bytes()) == (8 * 128, 128)
    div = ROOT / "assets" / "common" / "walker-divider.svg"
    text = div.read_text(encoding="utf-8")
    assert_valid_svg(text)
    assert_no_external(text)
    assert div.stat().st_size <= 500 * 1024


# ---------------------------------------------------------------- normalize_sheet (dev, Pillow)


def _raw_sheet(path: Path, cols: int = 4, rows: int = 2) -> None:
    """A non-integer grid (cells 30.5 px wide) of a 'fox' blob that drifts per frame,
    with low-alpha garbage-coloured speckle all over, like the ChatGPT art."""
    import random

    rnd = random.Random(1)
    w, h = 122, 64
    blobs = []
    for i in range(cols * rows):
        c, r = i % cols, i // cols
        cx = c * w / cols + w / cols / 2 + rnd.choice((-3, -2, 2, 3))
        foot = r * h / rows + h / rows - 4 + rnd.choice((-2, 0, 1))
        blobs.append((cx, foot))

    def px(x, y):
        for cx, foot in blobs:
            if abs(x + 0.5 - cx) <= 6 and foot - 16 <= y + 0.5 <= foot:
                return (230, 220, 210, 252)
        if rnd.random() < 0.3:
            return (rnd.choice((255, 0)), rnd.choice((255, 0)), rnd.choice((255, 0)), rnd.randint(1, 30))
        return (0, 0, 0, 0)

    path.write_bytes(png_rgba(w, h, px))


def test_normalize_sheet(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    import io

    from scripts.build.sprites import normalize_sheet

    src = tmp_path / "raw.png"
    _raw_sheet(src)
    out = normalize_sheet(src, 4, 2, 24)
    im = Image.open(io.BytesIO(out))
    assert im.size == (8 * 24, 24)
    assert im.mode == "P"  # palette PNG
    rgba = im.convert("RGBA")
    boxes = []
    for i in range(8):
        f = rgba.crop((i * 24, 0, i * 24 + 24, 24))
        a = f.getchannel("A")
        boxes.append(a.point(lambda v: 255 if v > 128 else 0).getbbox())
        # speckle gone: nothing visible outside the blob's (padded) box
        x0, y0, x1, y1 = a.point(lambda v: 255 if v > 0 else 0).getbbox()
        bx0, by0, bx1, by1 = boxes[-1]
        assert x0 >= bx0 - 2 and x1 <= bx1 + 2 and y0 >= by0 - 2 and y1 <= by1 + 2
        # no garbage colours survive: every visible pixel is near the blob colour
        raw = f.tobytes()
        for r, g, b, al in zip(raw[0::4], raw[1::4], raw[2::4], raw[3::4]):
            if al:
                assert r > 150 and g > 150 and b > 150, (r, g, b, al)
    # re-centred: shared horizontal centre and shared baseline (feet), no jitter
    assert max(b[0] for b in boxes) - min(b[0] for b in boxes) <= 1
    assert len({b[3] for b in boxes}) == 1
    assert max(b[3] for b in boxes) >= 24 - 3  # feet sit near the bottom of the frame


def test_normalize_sheet_key_out(tmp_path):
    """Fallback: a flat #0b0e22 background (no alpha) is keyed out to transparency."""
    Image = pytest.importorskip("PIL.Image")
    import io

    from scripts.build.sprites import normalize_sheet

    def px(x, y):
        fx, fy = x % 20, y % 20
        return (240, 240, 240, 255) if 6 <= fx < 14 and 4 <= fy < 18 else (0x0B, 0x0E, 0x22, 255)

    src = tmp_path / "flat.png"
    src.write_bytes(png_rgba(80, 40, px))
    im = Image.open(io.BytesIO(normalize_sheet(src, 4, 2, 16, key_out=True))).convert("RGBA")
    assert im.size == (128, 16)
    assert im.getpixel((0, 0))[3] == 0
    assert im.getpixel((8, 10))[3] > 200
