"""Achievements (奉納額): one small hanging tablet per achievement, 410x200, shown at 360 px.

Each achievement is a wooden votive tablet with a little roof, hung from the
shimenawa on two red cords. It sways (the shared 5 s sway, each tablet on its own
phase), a sheen sweeps across the wood now and then, and gold corner fittings
(金具) frame the board. On the left a lacquered round window holds a drawn emblem
that suits the achievement: a trophy for a CTF win, a capture-the-flag pennant for
a CTF ranking, a certification rosette for AWS and Salesforce, a TryHackMe-style
hex badge, and a red 合格 hanko for the JLPT. A glint twinkles on the emblem.
On the right: the title (wrapped with metrics.wrap, never truncated) and the result.

Stdlib only.
"""
from __future__ import annotations

import math

from ..content import ACHIEVEMENTS, Lang
from ..icons import BRAND, GLYPH, icon
from ..metrics import text_width, wrap
from ..palette import PALETTE as P
from ..svg import MOTION_CSS, document, embed_fonts, esc, petal_def, petals, rope

W, H = 410, 200
CX = W / 2
MIN_SIZE = 14  # 12 px at 360 rendered
SERIF = 'font-family="Shrine Serif"'

# board and roof
BL, BR, BT, BB = 22, 388, 60, 182
ROOF_T, ROOF_B = 46, 62
CORD_X = (150, 260)
ROPE_DY = 2

# emblem window and text column
WIN_C = (84, 121)
WIN_R = 44
TEXT_X = 144
TEXT_W = 234  # TEXT_X .. 378
TEXT_TOP, TEXT_BOT = 70, 174
DETAIL_SIZE = 17

EMBLEM: dict[str, str] = {
    "squid_ctf": "trophy",
    "knight_ctf": "flag",
    "aws_dev": "seal",
    "agentforce": "seal",
    "tryhackme": "thm",
    "jlpt": "pass",
}

# accent per tablet: halo behind the window, divider diamond
ACCENT: dict[str, str] = {
    "squid_ctf": P["lantern-gold"],
    "knight_ctf": P["vermilion"],
    "aws_dev": "#ff9900",
    "agentforce": "#00a1e0",
    "tryhackme": "#88cc14",
    "jlpt": P["vermilion"],
}

EDGE = "#6b4420"
GOLD_DARK = "#b47a2a"

CSS = """
.sheen{animation:sheen 11s ease-in-out infinite}
@keyframes sheen{0%,55%{transform:translateX(-260px)}80%,100%{transform:translateX(560px)}}
.glint{transform-box:fill-box;transform-origin:center;animation:glint 5s ease-in-out infinite}
@keyframes glint{0%,62%,100%{transform:scale(0) rotate(0deg);opacity:0}72%{transform:scale(1) rotate(45deg);opacity:1}84%{transform:scale(0) rotate(90deg);opacity:0}}
.wave{transform-box:fill-box;transform-origin:0 50%;animation:wave 2.8s ease-in-out infinite}
@keyframes wave{0%,100%{transform:skewY(0deg) scaleX(1)}50%{transform:skewY(-5deg) scaleX(.93)}}
.halo{animation:breathe 5s ease-in-out infinite}
"""


def _g(v: float) -> str:
    return f"{round(v, 2):g}"


def _find(aid: str) -> tuple[int, tuple]:
    for i, a in enumerate(ACHIEVEMENTS):
        if a[0] == aid:
            return i, a
    raise KeyError(aid)


# ---------------------------------------------------------------- text


def _fits(lines: list[str], size: float) -> bool:
    """Every line fits the column and none starts or ends at a spaced dash."""
    return all(
        text_width(l, size, weight=700) <= TEXT_W and not l.startswith(("–", "—")) and not l.endswith(("–", "—"))
        for l in lines
    )


def title_lines(aid: str, lang: Lang) -> tuple[float, list[str]]:
    """(font size, lines) of the title: one line up to 22 units, two lines up to 20,
    three as a last resort; never below MIN_SIZE and never truncated."""
    _, (_, title, _) = _find(aid)
    text = title(lang)
    size = 22.0
    while size >= MIN_SIZE:
        max_lines = 1 if size > 20 else 2
        lines = wrap(text, size, TEXT_W, weight=700)
        if len(lines) <= max_lines and _fits(lines, size):
            return size, lines
        size -= 0.5
    for size in (16.0, 15.0, float(MIN_SIZE)):
        lines = wrap(text, size, TEXT_W, weight=700)
        if _fits(lines, size):
            return size, lines
    raise ValueError(f"{aid}/{lang}: title does not fit")


# ---------------------------------------------------------------- defs


def _defs(accent: str) -> str:
    grain = "".join(
        f'<path d="M{BL},{y} C{BL + 110},{y - 6 + d} {BR - 140},{y + 6 - d} {BR},{y - 2}"/>'
        for y, d in ((78, 0), (101, 3), (126, -2), (150, 4), (172, 1))
    )
    return (
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
        + petal_def()
        + f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["night-0"]}"/>'
        f'<stop offset="0.65" stop-color="{P["night-1"]}"/><stop offset="1" stop-color="{P["night-2"]}"/></linearGradient>'
        f'<radialGradient id="halo" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{accent}" stop-opacity="0.45"/>'
        f'<stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="wood" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["wood-a"]}"/>'
        f'<stop offset="0.55" stop-color="#c3914f"/><stop offset="1" stop-color="{P["wood-b"]}"/></linearGradient>'
        f'<linearGradient id="roof" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a2c12"/>'
        f'<stop offset="1" stop-color="{P["ink-a"]}"/></linearGradient>'
        f'<linearGradient id="gold" x1="0" y1="0" x2="0.4" y2="1"><stop offset="0" stop-color="{P["moon-a"]}"/>'
        f'<stop offset="0.35" stop-color="{P["lantern-gold"]}"/><stop offset="1" stop-color="{GOLD_DARK}"/></linearGradient>'
        f'<linearGradient id="sheenG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff4dc" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="#fff4dc" stop-opacity="0.3"/><stop offset="1" stop-color="#fff4dc" stop-opacity="0"/></linearGradient>'
        f'<radialGradient id="lacquer" cx="0.5" cy="0.38" r="0.65"><stop offset="0" stop-color="#2a1d46"/>'
        f'<stop offset="1" stop-color="{P["night-0"]}"/></radialGradient>'
        f'<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0.45"/>'
        f'<stop offset="0.5" stop-color="{P["vermilion"]}" stop-opacity="0.18"/>'
        f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0.35"/></linearGradient>'
        f'<linearGradient id="divider" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{P["ink-red"]}" stop-opacity="0.8"/>'
        f'<stop offset="1" stop-color="{P["ink-red"]}" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="boardClip"><rect x="{BL}" y="{BT}" width="{BR - BL}" height="{BB - BT}" rx="5"/></clipPath>'
        f'<clipPath id="win"><circle cx="0" cy="0" r="{WIN_R - 3}"/></clipPath>'
        f'<g id="grain" clip-path="url(#boardClip)" stroke="{P["wood-grain"]}" stroke-opacity="0.22" fill="none" stroke-width="1.3">{grain}</g>'
        '<filter id="hang" x="-10%" y="-10%" width="120%" height="135%">'
        '<feDropShadow dx="0" dy="6" stdDeviation="6" flood-color="#000" flood-opacity="0.55"/></filter>'
        '<filter id="carve" x="-5%" y="-20%" width="110%" height="150%">'
        f'<feDropShadow dx="0" dy="1" stdDeviation="0.2" flood-color="{P["moon-b"]}" flood-opacity="0.5"/></filter>'
        '<filter id="eglow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<filter id="ink" x="-10%" y="-10%" width="120%" height="120%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="7" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="1.6" xChannelSelector="R" yChannelSelector="G"/></filter>'
    )


# ---------------------------------------------------------------- emblems (local coords, centred on the window)


def _trophy() -> str:
    gold = "url(#gold)"
    return (
        _laurel()
        + f'<path d="M-15,-20 c-12,0 -14,14 -2,18 M15,-20 c12,0 14,14 2,18" fill="none" stroke="{P["lantern-gold"]}" stroke-width="3" stroke-linecap="round"/>'
        f'<path d="M-17,-25 h34 v6 c0,15 -7,23 -17,25 c-10,-2 -17,-10 -17,-25 z" fill="{gold}" stroke="{GOLD_DARK}" stroke-width="1"/>'
        f'<path d="M-11,-21 c0,10 3,17 7,20" fill="none" stroke="#fff4dc" stroke-opacity="0.7" stroke-width="2" stroke-linecap="round"/>'
        f'<rect x="-3.5" y="6" width="7" height="9" fill="{gold}"/>'
        f'<path d="M-12,15 h24 l3,8 h-30 z" fill="{gold}" stroke="{GOLD_DARK}" stroke-width="1"/>'
        f'<rect x="-17" y="23" width="34" height="6" rx="1.5" fill="{P["ink-b"]}" stroke="{GOLD_DARK}" stroke-width="0.8"/>'
        + icon("star", -6.5, -19, 13, P["ink-red"])
    )


def _laurel() -> str:
    leaves = []
    for side in (-1, 1):
        for k in range(5):
            a = 200 - k * 26 if side < 0 else -20 + k * 26
            r = 33
            x = r * math.cos(math.radians(a))
            y = r * math.sin(math.radians(a)) + 4
            rot = a + (90 if side < 0 else -90)
            leaves.append(
                f'<ellipse cx="{_g(x)}" cy="{_g(y)}" rx="2.6" ry="6.5" transform="rotate({_g(rot + side * 25)} {_g(x)} {_g(y)})"/>'
            )
    return f'<g fill="{P["lantern-gold"]}" opacity="0.55">{"".join(leaves)}</g>'


def _flag() -> str:
    v = P["vermilion"]
    return (
        f'<path d="M-24,32 h40" stroke="{P["text-soft-b"]}" stroke-opacity="0.5" stroke-width="1.2"/>'
        f'<path d="M-16,32 l4,-8 h12 l4,8 z" fill="{P["ink-b"]}" stroke="{GOLD_DARK}" stroke-width="0.8"/>'
        f'<rect x="-11.5" y="-34" width="3" height="58" rx="1.5" fill="url(#gold)"/>'
        f'<circle cx="-10" cy="-35" r="3.4" fill="{P["lantern-gold"]}"/>'
        f'<g class="wave"><path d="M-8.5,-30 C2,-35 10,-24 28,-29 L28,-3 C10,2 2,-9 -8.5,-4 Z" fill="{v}"/>'
        f'<path d="M-8.5,-30 C2,-35 10,-24 28,-29 L28,-25 C10,-20 2,-31 -8.5,-26 Z" fill="#fff4dc" opacity="0.25"/>'
        + icon("star", 3, -24, 14, P["moon-a"])
        + "</g>"
    )


def _rosette(inner: str, ribbon: str) -> str:
    n, r1, r2 = 20, 30, 26
    pts = []
    for i in range(2 * n):
        r = r1 if i % 2 == 0 else r2
        a = math.pi * i / n - math.pi / 2
        pts.append(f"{_g(r * math.cos(a))},{_g(r * math.sin(a) - 6)}")
    return (
        f'<path d="M-14,10 l-8,30 l9,-5 l5,9 l6,-28 z M14,10 l8,30 l-9,-5 l-5,9 l-6,-28 z" fill="{ribbon}" stroke="{P["night-0"]}" stroke-opacity="0.5" stroke-width="0.8"/>'
        f'<polygon points="{" ".join(pts)}" fill="url(#gold)" stroke="{GOLD_DARK}" stroke-width="0.8"/>'
        f'<circle cy="-6" r="21" fill="{P["night-0"]}" stroke="{GOLD_DARK}" stroke-width="1.2"/>'
        f'<circle cy="-6" r="18" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.55" stroke-width="0.8" stroke-dasharray="1.5 2.5"/>'
        + inner
    )


def _seal_aws() -> str:
    d, _ = BRAND["AWS"]
    s = 28 / 24
    logo = f'<g transform="translate(-14,-20) scale({_g(s)})"><path d="{d}" fill="#ff9900"/></g>'
    return _rosette(logo, P["vermilion"])


def _seal_salesforce() -> str:
    blue = "#00a1e0"
    cloud = (
        f'<path d="M-11,1 a6,6 0 0 1 -1,-11.5 a7.5,7.5 0 0 1 12,-5 a6.5,6.5 0 0 1 10.5,2.2 a6,6 0 0 1 1.5,11.8 z" fill="{blue}"/>'
        f'<path d="M-5,-7 l3.6,3.6 l7,-7" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    return _rosette(cloud, "#0b5cab")


def _thm() -> str:
    def hexp(r: float, dy: float = 0) -> str:
        return " ".join(
            f"{_g(r * math.cos(math.radians(60 * k - 90)))},{_g(r * math.sin(math.radians(60 * k - 90)) + dy)}"
            for k in range(6)
        )

    green = "#88cc14"
    return (
        f'<polygon points="{hexp(39)}" fill="{green}" opacity="0.18"/>'
        f'<polygon points="{hexp(35)}" fill="#212c42" stroke="{green}" stroke-width="2.2"/>'
        f'<polygon points="{hexp(30.5)}" fill="none" stroke="{green}" stroke-opacity="0.45" stroke-width="0.8"/>'
        f'<g transform="translate(-17,-18) scale({_g(34 / 24)})"><path d="{GLYPH["tryhackme"]}" fill="#ffffff"/></g>'
    )


def _pass() -> str:
    red, moon = P["ink-red"], P["moon-a"]
    return (
        f'<g transform="rotate(-8)" filter="url(#ink)">'
        f'<circle r="33" fill="{red}"/>'
        f'<circle r="29" fill="none" stroke="{moon}" stroke-opacity="0.8" stroke-width="1.2"/>'
        f'<circle r="26" fill="none" stroke="{moon}" stroke-opacity="0.45" stroke-width="0.6"/>'
        f'<text y="8" text-anchor="middle" {SERIF} font-size="23" font-weight="700" fill="{moon}" letter-spacing="1">合格</text>'
        "</g>"
    )


EMBLEMS = {
    "squid_ctf": _trophy,
    "knight_ctf": _flag,
    "aws_dev": _seal_aws,
    "agentforce": _seal_salesforce,
    "tryhackme": _thm,
    "jlpt": _pass,
}


# ---------------------------------------------------------------- pieces


def _scene_back(i: int) -> str:
    stars = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff"' + (' class="node"' if k % 3 == 0 else ' opacity="0.55"') + "/>"
        for k, (x, y, r) in enumerate(
            ((24, 44, 1), (392, 40, 1.1), (12, 120, 0.8), (400, 150, 0.9), (60, 192, 0.8), (340, 194, 0.9), (110, 36, 0.7), (300, 34, 0.8))
        )
    )
    pet = [(60 + 37 * i, 0.7, 9, -2 - i), (300 - 23 * i, 0.6, 11, -6 - i), (470, 0.8, 10, -4)]
    return (
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>'
        f"{stars}"
        + petals(pet)
        + f'<g transform="translate(0,{ROPE_DY})">{rope(W, (0.12, 0.88))}</g>'
    )


def _corners() -> str:
    """Gold corner fittings (金具) with a rivet."""
    out = []
    for x, y, sx, sy in ((BL, BT, 1, 1), (BR, BT, -1, 1), (BL, BB, 1, -1), (BR, BB, -1, -1)):
        out.append(
            f'<g transform="translate({x},{y}) scale({sx},{sy})">'
            f'<path d="M0,0 h20 l-4,4 h-12 v12 l-4,4 z" fill="url(#gold)" stroke="{GOLD_DARK}" stroke-width="0.6"/>'
            f'<circle cx="7" cy="7" r="1.9" fill="{P["moon-a"]}" stroke="{GOLD_DARK}" stroke-width="0.6"/></g>'
        )
    return "".join(out)


def _tablet(aid: str, lang: Lang, i: int) -> str:
    _, (_, _, detail) = _find(aid)
    wx, wy = WIN_C
    accent = ACCENT[aid]
    v = P["vermilion"]
    top = ROPE_DY + 6 + 40 * (CORD_X[0] / W) * (1 - CORD_X[0] / W)
    cords = (
        f'<path d="M{CORD_X[0]},{_g(top)} L{CORD_X[0] - 6},{ROOF_T + 2} M{CORD_X[1]},{_g(top)} L{CORD_X[1] + 6},{ROOF_T + 2}" '
        f'stroke="{v}" stroke-width="2.4" fill="none" stroke-linecap="round"/>'
        + "".join(f'<circle cx="{x}" cy="{_g(top)}" r="3.4" fill="{v}"/>' for x in CORD_X)
    )
    # little roof (屋根) with upturned ends, like a kasagi
    roof = (
        f'<path d="M{BL - 12},{ROOF_T - 3} Q{CX},{ROOF_T + 4} {BR + 12},{ROOF_T - 3} L{BR + 6},{ROOF_B} L{BL - 6},{ROOF_B} Z" '
        f'fill="url(#roof)" stroke="{P["ink-a"]}" stroke-width="1"/>'
        f'<path d="M{BL - 8},{ROOF_T + 1} Q{CX},{ROOF_T + 7} {BR + 8},{ROOF_T + 1}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.35" stroke-width="1"/>'
        + "".join(f'<circle cx="{x - (6 if x < CX else -6)}" cy="{ROOF_T + 2}" r="2.6" fill="{P["ink-a"]}" stroke="{v}" stroke-width="1.2"/>' for x in CORD_X)
    )
    board = (
        f'<rect x="{BL + 2.5}" y="{BT + 3.5}" width="{BR - BL}" height="{BB - BT}" rx="5" fill="{EDGE}"/>'
        f'<rect x="{BL}" y="{BT}" width="{BR - BL}" height="{BB - BT}" rx="5" fill="url(#wood)" stroke="{EDGE}" stroke-width="2"/>'
        '<use href="#grain" xlink:href="#grain"/>'
        f'<rect x="{BL + 6}" y="{BT + 6}" width="{BR - BL - 12}" height="{BB - BT - 12}" rx="3" fill="none" '
        f'stroke="{P["moon-b"]}" stroke-opacity="0.3" stroke-width="1.1"/>'
        f'<g clip-path="url(#boardClip)"><g transform="rotate(16 {CX} {(BT + BB) / 2})">'
        f'<rect class="sheen" x="0" y="-40" width="70" height="240" fill="url(#sheenG)" style="animation-delay:{-1.7 * i:g}s"/></g></g>'
        + _corners()
    )
    window = (
        f'<g transform="translate({wx},{wy})">'
        f'<circle r="{WIN_R + 3}" fill="{P["ink-a"]}" opacity="0.35"/>'
        f'<circle r="{WIN_R}" fill="url(#lacquer)" stroke="{P["lantern-gold"]}" stroke-opacity="0.8" stroke-width="1.8"/>'
        f'<circle r="{WIN_R - 4}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.25" stroke-width="0.8"/>'
        f'<circle r="{WIN_R - 6}" fill="url(#halo)" class="halo" style="animation-delay:{-0.9 * i:g}s"/>'
        f'<g clip-path="url(#win)"><g filter="url(#eglow)">{EMBLEMS[aid]()}</g></g>'
        f'<path class="glint" d="M30,-30 l2,-8 l2,8 l8,2 l-8,2 l-2,8 l-2,-8 l-8,-2 z" fill="#fff" '
        f'style="animation-delay:{-0.8 * i:g}s"/>'
        "</g>"
    )
    # text column: title lines, divider, result
    size, lines = title_lines(aid, lang)
    lh = size * 1.24
    block = size * 0.78 + lh * (len(lines) - 1) + 14 + 12 + DETAIL_SIZE * 0.78
    y0 = (TEXT_TOP + TEXT_BOT) / 2 - block / 2 + size * 0.78
    title_svg = "".join(
        f'<text x="{TEXT_X}" y="{_g(y0 + k * lh)}" {SERIF} font-size="{_g(size)}" font-weight="700" fill="{P["ink-a"]}">{esc(t)}</text>'
        for k, t in enumerate(lines)
    )
    dy = y0 + lh * (len(lines) - 1) + 12
    det_y = dy + 12 + DETAIL_SIZE * 0.78
    divider = (
        f'<path d="M{TEXT_X + 4},{_g(dy)} l4,-4 l4,4 l-4,4 z" fill="{accent if aid != "squid_ctf" else P["ink-red"]}" stroke="{P["ink-a"]}" stroke-opacity="0.4" stroke-width="0.6"/>'
        f'<rect x="{TEXT_X + 14}" y="{_g(dy - 0.6)}" width="120" height="1.2" fill="url(#divider)"/>'
    )
    detail_svg = (
        f'<text x="{TEXT_X}" y="{_g(det_y)}" {SERIF} font-size="{DETAIL_SIZE}" font-weight="700" fill="{P["ink-red"]}" '
        f'letter-spacing="0.5">{esc(detail(lang))}</text>'
    )
    return (
        f'<g filter="url(#hang)">{cords}{board}{roof}</g>'
        + window
        + f'<g filter="url(#carve)">{title_svg}{divider}{detail_svg}</g>'
    )


SWAY_DELAYS = (0, -1.1, -2.3, -3.4, -4.3, -0.6)


def render_achievement(aid: str, lang: Lang, fonts) -> str:
    i, (_, title, detail) = _find(aid)
    pivot = f"transform-box:view-box;transform-origin:{_g(CX)}px 14px"
    body = (
        '<g clip-path="url(#card)">'
        + _scene_back(i)
        + f'<g class="sway" style="{pivot};animation-delay:{SWAY_DELAYS[i % len(SWAY_DELAYS)]:g}s">'
        + _tablet(aid, lang, i)
        + "</g></g>"
        + f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="15.25" fill="none" '
        'stroke="url(#frame)" stroke-width="1.5"/>'
    )
    svg = document(W, H, body, title=f"{title(lang)} · {detail(lang)}", css=MOTION_CSS + CSS, defs=_defs(ACCENT[aid]))
    return embed_fonts(svg, fonts)
