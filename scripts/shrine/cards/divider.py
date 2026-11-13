"""Walker divider: a chibi kitsune carrying a lantern walks a night path between
README sections. 1200x140, no text (language-neutral, one file for both READMEs).

The walker is a stepped sprite (scripts/shrine/sprite.py) from the one-row sheet
scripts/build/art/walker-sheet.png; it faces right and crosses the strip every 14 s,
its lantern throwing a warm pool of light on the flagstones. Stdlib only.
"""
from __future__ import annotations

import random

from ..palette import PALETTE as P
from ..sprite import png_size, sprite_parts
from ..svg import MOTION_CSS, document, lantern

W, H, RX = 1200, 140, 16
GROUND = 126  # top of the flagstones; the walker's feet land just below it
WALKER_FPS = 11
LANTERNS = (170, 610, 1050)

CSS = """
.tw{animation:pulse 3.2s ease-in-out infinite}
.fx{animation:fx 7s ease-in-out infinite}
@keyframes fx{0%,100%{transform:translate(0,0);opacity:.2}30%{opacity:.9}50%{transform:translate(6px,-9px);opacity:.6}75%{transform:translate(-4px,-4px);opacity:.95}}
"""


def _g(v: float) -> str:
    return f"{round(v, 2):g}"


def _defs() -> str:
    return (
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="{RX}"/></clipPath>'
        f'<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0.45"/>'
        f'<stop offset="0.5" stop-color="{P["vermilion"]}" stop-opacity="0.18"/>'
        f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0.35"/></linearGradient>'
        '<linearGradient id="stone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b3550"/>'
        '<stop offset="1" stop-color="#1c1830"/></linearGradient>'
        f'<linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["night-2"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{P["vermilion"]}" stop-opacity="0.10"/></linearGradient>'
        f'<radialGradient id="pool" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{P["lantern-glow-a"]}" stop-opacity="0.55"/>'
        f'<stop offset="1" stop-color="{P["lantern-glow-b"]}" stop-opacity="0"/></radialGradient>'
    )


def _stars(rnd: random.Random) -> str:
    out = []
    for i in range(40):
        x, y = rnd.uniform(10, W - 10), rnd.uniform(8, GROUND - 40)
        r = rnd.choice((0.7, 0.9, 1.1, 1.3))
        if i % 3 == 0:
            out.append(f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{r:g}" fill="#fff" class="tw" style="animation-delay:-{_g(rnd.uniform(0, 3.2))}s"/>')
        else:
            out.append(f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{r:g}" fill="#fff" opacity="{_g(rnd.uniform(0.3, 0.7))}"/>')
    return "".join(out)


def _hills() -> str:
    import math

    pts = []
    for i in range(61):
        x = W * i / 60
        u = x / W
        y = GROUND - 26 - 14 * (0.6 * math.sin(u * 9.3 + 1.1) + 0.4 * math.sin(u * 23.7 + 0.4))
        pts.append(f"{_g(x)},{_g(y)}")
    return f'<path d="M0,{H} L{" L".join(pts)} L{W},{H} Z" fill="#141030" opacity="0.9"/>'


def _path() -> str:
    joints = "".join(f"M{x},{GROUND + 1} l3,{H - GROUND}" for x in range(23, W, 46))
    return (
        f'<rect y="{GROUND}" width="{W}" height="{H - GROUND}" fill="url(#stone)"/>'
        f'<path d="M0,{GROUND} H{W}" stroke="{P["moon-b"]}" stroke-opacity="0.22" stroke-width="1"/>'
        f'<path d="{joints}" fill="none" stroke="#0b0a18" stroke-opacity="0.55" stroke-width="1"/>'
    )


def _lanterns() -> str:
    k = 0.62
    return "".join(
        f'<g transform="translate({x},{_g(GROUND + 2 - 60 * k)}) scale({k})">{lantern(0, 0, 0.6 * i)}</g>'
        for i, x in enumerate(LANTERNS)
    )


def _fireflies(rnd: random.Random) -> str:
    return "".join(
        f'<circle cx="{_g(rnd.uniform(30, W - 30))}" cy="{_g(rnd.uniform(40, GROUND - 14))}" r="1.6" '
        f'fill="{P["lantern-gold"]}" class="fx" style="animation-delay:-{_g(rnd.uniform(0, 7))}s"/>'
        for _ in range(8)
    )


def render_divider(walker_png: bytes) -> str:
    """The walker strip; walker_png is a one-row sheet of square frames, facing right."""
    w, f = png_size(walker_png)
    cols = w // f
    # warm light from the lantern (right of the walker's chest) and its pool on the path
    underlay = (
        f'<circle cx="{_g(f * 0.82)}" cy="{_g(f * 0.7)}" r="{_g(f * 0.32)}" fill="url(#lanternGlow)" class="lglow" opacity="0.7"/>'
        f'<ellipse cx="{_g(f * 0.62)}" cy="{_g(f + 4)}" rx="{_g(f * 0.55)}" ry="7" fill="url(#pool)"/>'
    )
    s_defs, s_css, s_body = sprite_parts(
        walker_png, cols, 1, f, WALKER_FPS, walk_across=W, uid="wk", underlay=underlay
    )
    foot = GROUND + 4  # feet a little into the flagstones, read as standing on them
    pad = round(f * 0.04)  # the sheet keeps the feet this far above the frame bottom
    rnd = random.Random(7)
    scene = (
        _stars(rnd)
        + f'<rect y="{_g(H * 0.4)}" width="{W}" height="{_g(H * 0.6)}" fill="url(#mist)"/>'
        + _hills()
        + _path()
        + _lanterns()
        + _fireflies(rnd)
        + f'<g transform="translate(0,{foot + pad - f})">{s_body}</g>'
    )
    body = (
        f'<g clip-path="url(#card)"><rect width="{W}" height="{H}" fill="url(#sky)"/>{scene}</g>'
        f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="{RX - 0.75}" fill="none" '
        f'stroke="url(#frame)" stroke-width="1.5"/>'
    )
    return document(W, H, body, title="kitsune", css=MOTION_CSS + CSS + s_css, defs=_defs() + s_defs)
