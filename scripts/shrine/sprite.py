"""Stepped CSS sprites: one embedded PNG sheet, clipped to one frame (stdlib only).

The sheet is laid out row-major, `cols` x `rows` frames of `frame_px` square.
A 1-row sheet steps through with a single `steps(cols)` animation; a grid uses
`steps(cols)` on x (one row per cols/fps seconds) inside `steps(rows)` on y.
With `walk_across`, an outer group also walks from -frame_px to walk_across
over 14 s. Shown as <img>, so CSS keyframes only. Imported by the CI generator
(scripts/shrine/cards/live.py): no third-party packages here.
"""
from __future__ import annotations

import base64
import struct

from .svg import NS, esc

WALK_S = 14
PNG_SIG = b"\x89PNG\r\n\x1a\n"


def png_size(png: bytes) -> tuple[int, int]:
    """(width, height) from a PNG's IHDR; ValueError if it is not a PNG."""
    if len(png) < 24 or png[:8] != PNG_SIG or png[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    return struct.unpack(">II", png[16:24])


def _g(v: float) -> str:
    return f"{round(v, 3):g}"


def sprite_parts(
    png: bytes,
    cols: int,
    rows: int,
    frame_px: int,
    fps: float,
    *,
    walk_across: int | None = None,
    uid: str = "spr",
    underlay: str = "",
) -> tuple[str, str, str]:
    """(defs, css, body) for embedding in a larger card. The body draws one frame at
    (0, 0)-(frame_px, frame_px) in its own user space; place it with a transform on
    a parent <g>. `underlay` (same user space) is drawn behind the frame and walks
    with it. Ids and keyframe names are prefixed with `uid`."""
    f = frame_px
    w, h = cols * f, rows * f
    n = cols * rows
    href = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    defs = f'<clipPath id="{uid}-clip"><rect width="{f}" height="{f}"/></clipPath>'
    css = (
        f".{uid}-x{{animation:{uid}x {_g(cols / fps)}s steps({cols}) infinite}}"
        f"@keyframes {uid}x{{from{{transform:translateX(0)}}to{{transform:translateX(-{w}px)}}}}"
    )
    image = (
        f'<image href="{href}" xlink:href="{href}" width="{w}" height="{h}" '
        f'preserveAspectRatio="none" style="image-rendering:auto"/>'
    )
    if rows > 1:
        css += (
            f".{uid}-y{{animation:{uid}y {_g(n / fps)}s steps({rows}) infinite}}"
            f"@keyframes {uid}y{{from{{transform:translateY(0)}}to{{transform:translateY(-{h}px)}}}}"
        )
        image = f'<g class="{uid}-y">{image}</g>'
    body = f'{underlay}<g clip-path="url(#{uid}-clip)"><g class="{uid}-x">{image}</g></g>'
    if walk_across is not None:
        css += (
            f".{uid}-w{{animation:{uid}w {WALK_S}s linear infinite}}"
            f"@keyframes {uid}w{{from{{transform:translateX(-{f}px)}}to{{transform:translateX({walk_across}px)}}}}"
        )
        body = f'<g class="{uid}-w">{body}</g>'
    return defs, css, body


def sprite_svg(
    png: bytes,
    cols: int,
    rows: int,
    frame_px: int,
    fps: float,
    *,
    walk_across: int | None = None,
    title: str = "kitsune",
) -> str:
    """A standalone animated sprite: frame_px square, or walk_across x frame_px when walking."""
    defs, css, body = sprite_parts(png, cols, rows, frame_px, fps, walk_across=walk_across)
    w = walk_across if walk_across is not None else frame_px
    return (
        f'<svg xmlns="{NS}" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {w} {frame_px}" width="{w}" height="{frame_px}" role="img">'
        f"<title>{esc(title)}</title><defs>{defs}</defs><style>{css}</style>{body}</svg>"
    )
