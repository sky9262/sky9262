"""TryHackMe badge shelf (owner edit 9): the owner's earned badges on hanging shelves.

A shimenawa with shide crosses the card under the heading and the stats line. One or
more wooden shelves hang from it on red cords (each lower shelf hangs from the one
above). The badges (TryHackMe's own images, downscaled into scripts/build/art/thm and
embedded as base64 PNG) stand on the shelves and float gently on staggered delays, a
glint twinkling on each; under every badge a small wooden name tag (札) hangs from the
shelf on a short cord, its name wrapped to at most two lines.

Rows are balanced and fill from the top (10 badges: 5 + 5 on desktop; 11: 6 + 5).
Desktop: viewBox 1200xH shown at 846 px (names 17.5 units). Phone: 600xH shown at
360 px, three per row (names 20 units).

Stdlib only.
"""
from __future__ import annotations

import base64
import math
from typing import Literal

from ..content import THM_BADGES, THM_SHELF, Lang
from ..icons import GLYPH
from ..metrics import text_width, wrap
from ..palette import PALETTE as P
from ..svg import MOTION_CSS, document, embed_fonts, esc, heading_defs, night_bg, petal_def, petals, rope, rope_y, section_heading

Layout = Literal["desktop", "phone"]

RX = 16
SERIF = 'font-family="Shrine Serif"'
W = {"desktop": 1200, "phone": 600}
PER_ROW = {"desktop": 6, "phone": 3}
SLOT_W = {"desktop": 180, "phone": 186}
BADGE_W = {"desktop": 104, "phone": 108}
BADGE_RATIO = 500 / 425  # TryHackMe badge images are 425x500
NAME_SIZE = {"desktop": 17.5, "phone": 20}  # >= 12 px rendered
NAME_LH = {"desktop": 21.5, "phone": 24.5}
HEAD = {"desktop": (46, 32, 84, 20), "phone": (50, 34, 92, 22)}  # title y, size, stats y, size
ROPE_TOP = {"desktop": 104, "phone": 112}
FIRST_ROW = {"desktop": 158, "phone": 164}
PLANK_H = 16
CORD = 10  # plank to tag
ROW_GAP = {"desktop": 30, "phone": 34}
BOTTOM_PAD = 26
TAG_PAD = 9
EDGE = "#6b4420"

CSS = """
.bob{animation:bob 4.6s ease-in-out infinite}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
.glint{transform-box:fill-box;transform-origin:center;animation:glint 6s ease-in-out infinite}
@keyframes glint{0%,64%,100%{transform:scale(0) rotate(0deg);opacity:0}74%{transform:scale(1) rotate(45deg);opacity:1}86%{transform:scale(0) rotate(90deg);opacity:0}}
.halo{animation:breathe 5s ease-in-out infinite}
"""


def _g(v: float) -> str:
    return f"{round(v, 2):g}"


def badge_h(layout: Layout) -> float:
    return BADGE_W[layout] * BADGE_RATIO


def tag_w(layout: Layout) -> float:
    return SLOT_W[layout] - 16


def tag_h(layout: Layout) -> float:
    return 2 * TAG_PAD + NAME_SIZE[layout] * 0.8 + NAME_LH[layout]


def name_lines(name: str, layout: Layout) -> list[str]:
    """The badge name wrapped to the tag (never truncated, at most two lines)."""
    room = tag_w(layout) - 2 * TAG_PAD
    lines = wrap(name, NAME_SIZE[layout], room)
    if len(lines) > 2 or any(text_width(l, NAME_SIZE[layout]) > room for l in lines):
        raise ValueError(f"badge name does not fit its tag: {name}")
    return lines


def _row_h(layout: Layout) -> float:
    return badge_h(layout) - 6 + PLANK_H + CORD + tag_h(layout)


def _counts(n: int, layout: Layout) -> list[int]:
    """Balanced rows, fuller rows first: 10 -> [5, 5], 11 -> [6, 5] on desktop."""
    rows = max(1, math.ceil(n / PER_ROW[layout]))
    base, extra = divmod(n, rows)
    return [base + 1] * extra + [base] * (rows - extra)


def plan(n: int, layout: Layout) -> tuple[int, list[tuple[float, float]]]:
    """(card height, [(slot centre x, row top y)] in badge order)."""
    w = W[layout]
    slots: list[tuple[float, float]] = []
    y = FIRST_ROW[layout]
    for count in _counts(n, layout):
        x0 = w / 2 - count * SLOT_W[layout] / 2
        slots += [(x0 + (k + 0.5) * SLOT_W[layout], y) for k in range(count)]
        y += _row_h(layout) + ROW_GAP[layout]
    h = int(round(y - ROW_GAP[layout] + BOTTOM_PAD))
    return h, slots


# ---------------------------------------------------------------- defs and pieces


def _defs(w: int, h: int) -> str:
    return (
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="{RX}"/></clipPath>'
        + petal_def()
        + heading_defs()
        + f'<linearGradient id="plankTop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e2c08e"/>'
        f'<stop offset="1" stop-color="{P["wood-a"]}"/></linearGradient>'
        f'<linearGradient id="plankFront" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c3914f"/>'
        f'<stop offset="1" stop-color="{P["wood-b"]}"/></linearGradient>'
        f'<linearGradient id="wood" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["wood-a"]}"/>'
        f'<stop offset="0.55" stop-color="#c3914f"/><stop offset="1" stop-color="{P["wood-b"]}"/></linearGradient>'
        f'<radialGradient id="badgeHalo" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{P["lantern-glow-a"]}" stop-opacity="0.32"/>'
        f'<stop offset="1" stop-color="{P["lantern-glow-a"]}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="shadow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#000" stop-opacity="0.5"/>'
        f'<stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["night-2"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{P["night-2"]}" stop-opacity="0.85"/></linearGradient>'
        f'<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0.45"/>'
        f'<stop offset="0.5" stop-color="{P["vermilion"]}" stop-opacity="0.18"/>'
        f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0.35"/></linearGradient>'
        '<filter id="hang" x="-10%" y="-20%" width="120%" height="160%">'
        '<feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#000" flood-opacity="0.55"/></filter>'
    )


def _stars(w: int, h: int, n: int) -> str:
    out = []
    x, y = 90, 30
    for i in range(n):
        x = (x + 263 + i * 71) % w
        y = (y + 157 + i * 29) % (h * 0.92)
        r = 0.8 + (i % 3) * 0.25
        cls = (' class="node"' + (f' style="animation-delay:-{i % 5 * 0.5:g}s"' if i % 5 else "")) if i % 3 == 0 else ' opacity="0.55"'
        out.append(f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{r:g}"{cls}/>')
    return '<g fill="#fff">' + "".join(out) + "</g>"


def _plank(x0: float, x1: float, y: float) -> str:
    """A shelf board: a light top face and a darker front face, its top edge at y."""
    return (
        f'<g filter="url(#hang)">'
        f'<path d="M{_g(x0 + 6)},{_g(y)} H{_g(x1 - 6)} L{_g(x1)},{_g(y + 6)} H{_g(x0)} Z" fill="url(#plankTop)"/>'
        f'<rect x="{_g(x0)}" y="{_g(y + 6)}" width="{_g(x1 - x0)}" height="{PLANK_H - 6}" fill="url(#plankFront)" stroke="{EDGE}" stroke-width="1"/>'
        f'<path d="M{_g(x0 + 8)},{_g(y + 11)} H{_g(x1 - 8)}" stroke="{P["wood-grain"]}" stroke-opacity="0.35" stroke-width="1"/>'
        "</g>"
    )


def _tag(cx: float, top: float, lines: list[str], layout: Layout) -> str:
    tw, th = tag_w(layout), tag_h(layout)
    size, lh = NAME_SIZE[layout], NAME_LH[layout]
    block = size * 0.8 + lh * (len(lines) - 1)
    y0 = top + (th - block) / 2 + size * 0.8
    text = "".join(
        f'<text x="{_g(cx)}" y="{_g(y0 + k * lh)}" text-anchor="middle" {SERIF} font-size="{size:g}" '
        f'font-weight="700" fill="{P["ink-a"]}">{esc(l)}</text>'
        for k, l in enumerate(lines)
    )
    return (
        f'<path d="M{_g(cx)},{_g(top - CORD)} V{_g(top + 4)}" stroke="{P["vermilion"]}" stroke-width="2" stroke-linecap="round"/>'
        f'<g filter="url(#hang)"><rect x="{_g(cx - tw / 2)}" y="{_g(top)}" width="{_g(tw)}" height="{_g(th)}" rx="5" '
        f'fill="url(#wood)" stroke="{EDGE}" stroke-width="1.2"/></g>'
        f'<rect x="{_g(cx - tw / 2 + 3.5)}" y="{_g(top + 3.5)}" width="{_g(tw - 7)}" height="{_g(th - 7)}" rx="3" fill="none" '
        f'stroke="{P["moon-b"]}" stroke-opacity="0.3" stroke-width="0.9"/>'
        f'<circle cx="{_g(cx)}" cy="{_g(top + 4)}" r="2.2" fill="{P["ink-a"]}"/>'
        + text
    )


def _badge(k: int, cx: float, top: float, png: bytes, layout: Layout) -> str:
    bw, bh = BADGE_W[layout], badge_h(layout)
    b64 = base64.b64encode(png).decode("ascii")
    base = top + bh - 6  # the badge's foot rests on the plank
    return (
        f'<ellipse cx="{_g(cx)}" cy="{_g(top + bh / 2)}" rx="{_g(bw * 0.72)}" ry="{_g(bh * 0.6)}" fill="url(#badgeHalo)" '
        f'class="halo" style="animation-delay:{-0.7 * k:g}s"/>'
        f'<ellipse cx="{_g(cx)}" cy="{_g(base + 1)}" rx="{_g(bw * 0.42)}" ry="4" fill="url(#shadow)"/>'
        f'<g class="bob" style="animation-delay:{-0.46 * k:g}s">'
        f'<image href="data:image/png;base64,{b64}" x="{_g(cx - bw / 2)}" y="{_g(top - 4)}" width="{bw}" height="{_g(bh)}"/>'
        f'<path class="glint" d="M{_g(cx + bw * 0.3)},{_g(top + 6)} l2.2,-8 l2.2,8 l8,2.2 l-8,2.2 l-2.2,8 l-2.2,-8 l-8,-2.2 z" '
        f'fill="#fff" style="animation-delay:{-0.6 * k - 0.3:g}s"/>'
        "</g>"
    )


def _header(lang: Lang, layout: Layout, w: int) -> str:
    ty, ts, sy, ss = HEAD[layout]
    title = section_heading(THM_SHELF["title"](lang), w / 2, ty, ts, ts * 0.6, rule=130 if layout == "desktop" else 60)
    stats = THM_SHELF["stats"](lang)
    sw = text_width(stats, ss, letter_spacing=0.5)
    ico = ss * 1.1
    x = w / 2 - (ico + 8 + sw) / 2
    s = ico / 24
    return (
        title
        + f'<g class="rise d1"><g transform="translate({_g(x)},{_g(sy - ss * 0.36 - ico / 2)}) scale({_g(s)})">'
        f'<path d="{GLYPH["tryhackme"]}" fill="{P["moon-b"]}"/></g>'
        f'<text x="{_g(x + ico + 8)}" y="{sy}" {SERIF} font-size="{ss}" fill="{P["text-soft-a"]}" letter-spacing="0.5">{esc(stats)}</text></g>'
    )


# ---------------------------------------------------------------- card


def render_thm_shelf(
    lang: Lang,
    layout: Layout,
    fonts,
    images: dict[str, bytes],
    *,
    badges: list[tuple[str, str]] = THM_BADGES,
) -> str:
    """The badge shelf; `images` maps each badge slug to its PNG bytes (KeyError if one is missing)."""
    w = W[layout]
    pngs = [images[slug] for slug, _ in badges]
    h, slots = plan(len(badges), layout)
    bh = badge_h(layout)
    rope_dy = ROPE_TOP[layout]
    rows = sorted({y for _, y in slots})
    widest = max(_counts(len(badges), layout)) * SLOT_W[layout]
    shelves, tags, items = [], [], []
    prev: tuple[float, float, float] | None = None  # previous plank (x0, x1, bottom)
    v = P["vermilion"]
    for r, y in enumerate(rows):
        # every plank is as wide as the fullest row and reaches past the outer tags,
        # so the cords run straight down, clear of every tag
        x0 = w / 2 - widest / 2 - 14
        x1 = w / 2 + widest / 2 + 14
        plank_y = y + bh - 6
        # cords: from the rope (first shelf) or from the shelf above
        cords = []
        for cx in (x0 + 7, x1 - 7):
            top = rope_dy + rope_y(w, cx) if prev is None else prev[2]
            cords.append(f'<path d="M{_g(cx)},{_g(top)} V{_g(plank_y + 2)}" stroke="{v}" stroke-width="2.4" stroke-linecap="round"/>'
                         f'<circle cx="{_g(cx)}" cy="{_g(top + 1)}" r="3" fill="{v}"/>')
        shelves.append("".join(cords) + _plank(x0, x1, plank_y))
        prev = (x0, x1, plank_y + PLANK_H)
    for k, ((slug, name), png, (cx, y)) in enumerate(zip(badges, pngs, slots)):
        items.append(_badge(k, cx, y, png, layout))
        tags.append(_tag(cx, y + bh - 6 + PLANK_H + CORD, name_lines(name, layout), layout))
    pet = (
        [(120, 1, 12, -2), (420, 0.8, 15, -8), (700, 1.1, 13, -5), (960, 0.9, 14, -1), (1180, 1.2, 16, -10)]
        if layout == "desktop"
        else [(80, 1, 13, -3), (300, 0.8, 16, -9), (560, 1.1, 14, -5)]
    )
    pet = [(x, s, d * h / 440, dl * h / 440) for x, s, d, dl in pet]
    tassels = (0.06, 0.94) if layout == "desktop" else (0.05, 0.95)
    scene = (
        night_bg(w, h, RX)
        + _stars(w, h, 30 if layout == "desktop" else 34)
        + f'<rect y="{_g(h * 0.55)}" width="{w}" height="{_g(h * 0.45)}" fill="url(#mist)"/>'
        + _header(lang, layout, w)
        + f'<g transform="translate(0,{rope_dy})">{rope(w, tassels)}</g>'
        + petals(pet)
        + "".join(shelves)
        + "".join(tags)
        + "".join(items)
    )
    body = (
        f'<g clip-path="url(#card)">{scene}</g>'
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{RX - 0.75}" fill="none" stroke="url(#frame)" stroke-width="1.5"/>'
    )
    title = f'{THM_SHELF["title"](lang)} · {THM_SHELF["stats"](lang)} · ' + ", ".join(n for _, n in badges)
    svg = document(w, h, body, title=title, css=MOTION_CSS + CSS, defs=_defs(w, h))
    return embed_fonts(svg, fonts)
