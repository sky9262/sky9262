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

from ..content import ACHIEVEMENTS, CTFTIME, HACKERRANK, HACKERRANK_TEXT, PICOCTF, Lang
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


def _hanging(i: int) -> str:
    """Cords, wooden board (grain, inset, sheen, corner fittings) and its little roof."""
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
    return f'<g filter="url(#hang)">{cords}{board}{roof}</g>'


def _tablet(aid: str, lang: Lang, i: int) -> str:
    _, (_, _, detail) = _find(aid)
    wx, wy = WIN_C
    accent = ACCENT[aid]
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
        _hanging(i)
        + window
        + f'<g filter="url(#carve)">{title_svg}{divider}{detail_svg}</g>'
    )


SWAY_DELAYS = (0, -1.1, -2.3, -3.4, -4.3, -0.6)


def _card(i: int, sway_delay: float, tablet: str, title: str, accent: str, fonts, *, css: str = "", defs: str = "") -> str:
    """The night scene, the swaying tablet and the frame, as an embedded-font SVG."""
    pivot = f"transform-box:view-box;transform-origin:{_g(CX)}px 14px"
    body = (
        '<g clip-path="url(#card)">'
        + _scene_back(i)
        + f'<g class="sway" style="{pivot};animation-delay:{sway_delay:g}s">'
        + tablet
        + "</g></g>"
        + f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="15.25" fill="none" '
        'stroke="url(#frame)" stroke-width="1.5"/>'
    )
    svg = document(W, H, body, title=title, css=MOTION_CSS + CSS + css, defs=_defs(accent) + defs)
    return embed_fonts(svg, fonts)


def render_achievement(aid: str, lang: Lang, fonts) -> str:
    i, (_, title, detail) = _find(aid)
    return _card(i, SWAY_DELAYS[i % len(SWAY_DELAYS)], _tablet(aid, lang, i), f"{title(lang)} · {detail(lang)}", ACCENT[aid], fonts)


# ---------------------------------------------------------------- HackerRank (owner edit 5)
#
# The same hanging tablet, with a header (a small HackerRank-green hex mark, the title
# and a sub-line) and a lacquered panel holding three hexagonal medals side by side,
# drawn after HackerRank's own badges in the shrine palette: a gold or silver rim,
# the language mark inside (C++ drawn as paths, the Simple Icons Python logo, a cut
# ruby), then the name, the earned stars and the solved count.

HR_GREEN = "#2ec866"
HR_HEAD_Y = 88
HR_HEAD_SIZE = 20
HR_SUB_SIZE = 15
HR_PANEL = (30, 98, 380, 172)  # x0, y0, x1, y1
HR_HEX_R = 21
HR_INSET = 8  # medal columns keep this clear of the panel's rim
HR_NAME_SIZE = 15
HR_CAPTION_SIZE = 14
HR_STAR = 10
TIER = {
    "gold": (P["moon-a"], P["lantern-gold"], GOLD_DARK, P["lantern-gold"]),
    "silver": ("#ffffff", "#c9d1dc", "#6f7888", "#dfe5ee"),
    "bronze": ("#ffe0c2", "#c98a4b", "#7a4a1e", "#e0a46a"),
}  # (light, mid, dark, star colour)


def _hr_defs() -> str:
    tiers = "".join(
        f'<linearGradient id="tier-{k}" x1="0" y1="0" x2="0.5" y2="1"><stop offset="0" stop-color="{a}"/>'
        f'<stop offset="0.45" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient>'
        for k, (a, b, c, _) in TIER.items()
    )
    return (
        tiers
        + '<linearGradient id="pyG" x1="0" y1="0" x2="1" y2="1"><stop offset="0.5" stop-color="#5a9fd4"/>'
        '<stop offset="0.5" stop-color="#ffd43b"/></linearGradient>'
        '<linearGradient id="rubyG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff7a86"/>'
        '<stop offset="0.45" stop-color="#e0283c"/><stop offset="1" stop-color="#8b1020"/></linearGradient>'
        f'<linearGradient id="panelG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a1d46"/>'
        f'<stop offset="1" stop-color="{P["night-0"]}"/></linearGradient>'
        '<linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.1"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
    )


def _hex(r: float) -> str:
    """Points of a pointy-top hexagon of radius r centred on the origin."""
    return " ".join(
        f"{_g(r * math.cos(math.radians(60 * k - 90)))},{_g(r * math.sin(math.radians(60 * k - 90)))}" for k in range(6)
    )


def _mark_cpp() -> str:
    c = "#8fbfee"
    return (
        f'<path d="M0.4,-4.7 A6.6,6.6 0 1 0 0.4,4.7" transform="translate(-4.5,0)" fill="none" stroke="{c}" '
        'stroke-width="2.8" stroke-linecap="round"/>'
        f'<path d="M2.4,0 h5 M4.9,-2.5 v5 M8.6,0 h5 M11.1,-2.5 v5" transform="translate(-1.5,0)" stroke="{c}" '
        'stroke-width="1.9" stroke-linecap="round"/>'
    )


def _mark_python() -> str:
    d, _ = BRAND["Python"]
    s = 20 / 24
    return f'<g transform="translate(-10,-10) scale({_g(s)})"><path d="{d}" fill="url(#pyG)"/></g>'


def _mark_ruby() -> str:
    return (
        '<path d="M-6.5,-7 H6.5 L10.5,-2 L0,10 L-10.5,-2 Z" fill="url(#rubyG)" stroke="#5a0a14" stroke-width="0.6"/>'
        '<path d="M-10.5,-2 H10.5 M-6.5,-7 L-3,-2 L0,10 M6.5,-7 L3,-2 L0,10 M-3,-2 L0,-7 L3,-2" fill="none" '
        'stroke="#ffd0d6" stroke-opacity="0.6" stroke-width="0.7" stroke-linejoin="round"/>'
        '<path d="M-5.6,-5.8 L-3.4,-2.6" stroke="#fff" stroke-opacity="0.8" stroke-width="1.1" stroke-linecap="round"/>'
    )


HR_MARKS = {"C++": _mark_cpp, "Python": _mark_python, "Ruby": _mark_ruby}


HR_GAP = 6
HR_HEX_W = 2 * HR_HEX_R * math.cos(math.radians(30))


def _hr_text_w(lang: Lang) -> float:
    """Widest text block (name, stars, caption) of any medal: all medals share one layout."""
    return max(
        max(
            text_width(b, HR_NAME_SIZE, weight=700),
            st * (HR_STAR + 1) - 1,
            text_width(HACKERRANK_TEXT["solved"](lang).format(n=n), HR_CAPTION_SIZE),
        )
        for b, st, n, _ in HACKERRANK
    )


def _hr_medal(k: int, badge: str, stars: int, solved: int, tier: str, lang: Lang, cx: float, cy: float) -> str:
    light, _mid, dark, star_c = TIER[tier]
    caption = HACKERRANK_TEXT["solved"](lang).format(n=solved)
    content = HR_HEX_W + HR_GAP + _hr_text_w(lang)
    hex_w, gap = HR_HEX_W, HR_GAP
    hx = cx - content / 2 + hex_w / 2
    tx = hx + hex_w / 2 + gap
    star_y = cy - HR_STAR / 2 - 1
    star_svg = "".join(icon("star", tx + j * (HR_STAR + 1), star_y, HR_STAR, star_c) for j in range(stars))
    glint = (
        f'<path class="glint" d="M{_g(hx + 14)},{_g(cy - 25)} l1.6,-6 l1.6,6 l6,1.6 l-6,1.6 l-1.6,6 l-1.6,-6 l-6,-1.6 z" '
        f'fill="#fff" style="animation-delay:{-1.3 * k - 0.4:g}s"/>'
        if tier == "gold" else ""
    )
    return (
        f'<g class="medal" data-badge="{esc(badge)}" data-stars="{stars}" data-tier="{tier}">'
        f'<g transform="translate({_g(hx)},{_g(cy)})">'
        f'<polygon points="{_hex(HR_HEX_R + 3)}" fill="{light}" opacity="0.14"/>'
        f'<polygon points="{_hex(HR_HEX_R)}" fill="url(#tier-{tier})" stroke="{dark}" stroke-width="0.8"/>'
        f'<polygon points="{_hex(HR_HEX_R - 4)}" fill="url(#panelG)" stroke="{light}" stroke-opacity="0.55" stroke-width="0.8"/>'
        f'<g filter="url(#eglow)">{HR_MARKS[badge]()}</g></g>'
        f'<text x="{_g(tx)}" y="{_g(cy - 10)}" {SERIF} font-size="{HR_NAME_SIZE}" font-weight="700" fill="{P["moon-a"]}">{esc(badge)}</text>'
        f"{star_svg}"
        f'<text x="{_g(tx)}" y="{_g(cy + 20)}" {SERIF} font-size="{HR_CAPTION_SIZE}" fill="{P["text-soft-a"]}">{esc(caption)}</text>'
        f"{glint}"
        "</g><!--/medal-->"
    )


def _hr_mark(x: float, y: float, r: float) -> str:
    """A small HackerRank-style mark: a green hexagon with an H."""
    return (
        f'<g transform="translate({_g(x)},{_g(y)})">'
        f'<polygon points="{_hex(r)}" fill="{HR_GREEN}" stroke="{P["ink-a"]}" stroke-opacity="0.5" stroke-width="0.8"/>'
        f'<path d="M-4,-5.5 V5.5 M4,-5.5 V5.5 M-4,0 H4" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/></g>'
    )


def _hr_tablet(lang: Lang, i: int) -> str:
    title = HACKERRANK_TEXT["title"](lang)
    sub = HACKERRANK_TEXT["sub"](lang)
    mark_r = 11
    tw = text_width(title, HR_HEAD_SIZE, weight=700)
    sw = text_width(sub, HR_SUB_SIZE, letter_spacing=0.5)
    total = 2 * mark_r + 8 + tw + 26 + sw
    if total > BR - BL - 40:
        raise ValueError(f"HackerRank header ({lang}) does not fit")
    x = CX - total / 2
    mark_y = HR_HEAD_Y - HR_HEAD_SIZE * 0.36
    head = (
        _hr_mark(x + mark_r, mark_y, mark_r)
        + f'<g filter="url(#carve)"><text x="{_g(x + 2 * mark_r + 8)}" y="{HR_HEAD_Y}" {SERIF} font-size="{HR_HEAD_SIZE}" '
        f'font-weight="700" fill="{P["ink-a"]}">{esc(title)}</text>'
        f'<path d="M{_g(x + 2 * mark_r + 8 + tw + 9)},{_g(mark_y)} l4,-4 l4,4 l-4,4 z" fill="{P["ink-red"]}"/>'
        f'<text x="{_g(x + 2 * mark_r + 8 + tw + 26)}" y="{HR_HEAD_Y}" {SERIF} font-size="{HR_SUB_SIZE}" font-weight="700" '
        f'fill="{P["ink-red"]}" letter-spacing="0.5">{esc(sub)}</text></g>'
    )
    x0, y0, x1, y1 = HR_PANEL
    col = (x1 - x0 - 2 * HR_INSET) / len(HACKERRANK)
    if HR_HEX_W + HR_GAP + _hr_text_w(lang) > col - 4:
        raise ValueError(f"HackerRank medals ({lang}) do not fit their columns")
    cy = (y0 + y1) / 2
    seps = "".join(
        f'<rect x="{_g(x0 + HR_INSET + col * k - 0.5)}" y="{y0 + 10}" width="1" height="{y1 - y0 - 20}" fill="{P["lantern-gold"]}" opacity="0.25"/>'
        for k in range(1, len(HACKERRANK))
    )
    panel = (
        f'<rect x="{x0 - 2}" y="{y0 - 2}" width="{x1 - x0 + 4}" height="{y1 - y0 + 4}" rx="10" fill="{P["ink-a"]}" opacity="0.35"/>'
        f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="8" fill="url(#panelG)" '
        f'stroke="{P["lantern-gold"]}" stroke-opacity="0.8" stroke-width="1.6"/>'
        f'<rect x="{x0 + 4}" y="{y0 + 4}" width="{x1 - x0 - 8}" height="{y1 - y0 - 8}" rx="5" fill="none" '
        f'stroke="{P["lantern-gold"]}" stroke-opacity="0.25" stroke-width="0.8"/>'
        f'<rect x="{x0 + 1}" y="{y0 + 1}" width="{x1 - x0 - 2}" height="{_g((y1 - y0) / 2)}" rx="7" fill="url(#gloss)"/>'
        + seps
    )
    medals = "".join(
        _hr_medal(k, b, st, n, t, lang, x0 + HR_INSET + col * (k + 0.5), cy) for k, (b, st, n, t) in enumerate(HACKERRANK)
    )
    return _hanging(i) + head + panel + medals


def render_hackerrank(lang: Lang, fonts) -> str:
    """HackerRank skill badges (content.HACKERRANK) on a tablet of the achievements family, 410x200."""
    i = len(ACHIEVEMENTS)  # its own phase after the six tablets
    summary = " · ".join(f"{b} {st}/5, {HACKERRANK_TEXT['solved'](lang).format(n=n)}" for b, st, n, _ in HACKERRANK)
    title = f"{HACKERRANK_TEXT['title'](lang)} · {HACKERRANK_TEXT['sub'](lang)} · {summary}"
    return _card(i, -2.9, _hr_tablet(lang, i), title, HR_GREEN, fonts, defs=_hr_defs())


# ---------------------------------------------------------------- picoCTF (owner edit 6)
#
# Same layout as the achievement tablets: a lacquered window on the left with a
# capture-the-flag pennant over a small "pico" mark, and on the right the title, the
# sub-line, the score set large and "pts · <user>" in mono.

MONO = 'font-family="Shrine Mono"'
PICO_ACCENT = P["circuit-cyan"]


def _pico_emblem() -> str:
    c, gold = P["circuit-cyan"], P["lantern-gold"]
    return (
        f'<rect x="-15.5" y="-32" width="3" height="44" rx="1.5" fill="url(#gold)"/>'
        f'<circle cx="-14" cy="-33" r="3.2" fill="{gold}"/>'
        f'<g class="wave"><path d="M-12.5,-29 C-3,-34 6,-23 22,-28 L22,-5 C6,0 -3,-11 -12.5,-6 Z" fill="{c}"/>'
        f'<path d="M-12.5,-29 C-3,-34 6,-23 22,-28 L22,-24 C6,-19 -3,-30 -12.5,-25 Z" fill="#fff" opacity="0.3"/>'
        # a terminal prompt on the flag
        f'<path d="M-3,-22.5 l5,4.2 l-5,4.2" fill="none" stroke="{P["night-0"]}" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="M4.5,-13.5 h8" stroke="{P["night-0"]}" stroke-width="2.2" stroke-linecap="round"/></g>'
        f'<path d="M-24,12 h20" stroke="{gold}" stroke-opacity="0.6" stroke-width="1.2"/>'
        f'<text x="0" y="30" text-anchor="middle" {MONO} font-size="14" font-weight="700" fill="{c}" '
        'letter-spacing="1">pico</text>'
    )


def _pico_tablet(lang: Lang, i: int) -> str:
    wx, wy = WIN_C
    title, sub = PICOCTF["title"](lang), PICOCTF["sub"](lang)
    score, small = PICOCTF["score"], f"pts · {PICOCTF['user']}"
    score_size = 34
    for t, size, kw in ((title, 21, {"weight": 700}), (sub, 15, {}), (score, score_size, {"weight": 700})):
        if text_width(t, size, **kw) > TEXT_W:
            raise ValueError(f"picoCTF text does not fit: {t}")
    window = (
        f'<g transform="translate({wx},{wy})">'
        f'<circle r="{WIN_R + 3}" fill="{P["ink-a"]}" opacity="0.35"/>'
        f'<circle r="{WIN_R}" fill="url(#lacquer)" stroke="{P["lantern-gold"]}" stroke-opacity="0.8" stroke-width="1.8"/>'
        f'<circle r="{WIN_R - 4}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.25" stroke-width="0.8"/>'
        f'<circle r="{WIN_R - 6}" fill="url(#halo)" class="halo" style="animation-delay:{-0.9 * i:g}s"/>'
        f'<g clip-path="url(#win)"><g filter="url(#eglow)">{_pico_emblem()}</g></g>'
        f'<path class="glint" d="M30,-30 l2,-8 l2,8 l8,2 l-8,2 l-2,8 l-2,-8 l-8,-2 z" fill="#fff" '
        f'style="animation-delay:{-0.8 * i:g}s"/>'
        "</g>"
    )
    x = TEXT_X
    tw = text_width(title, 21, weight=700)
    sub_x = x + tw + 22
    if sub_x + text_width(sub, 15, weight=700, letter_spacing=0.5) > TEXT_X + TEXT_W:
        raise ValueError(f"picoCTF header ({lang}) does not fit")
    text = (
        f'<g filter="url(#carve)">'
        f'<text x="{x}" y="96" {SERIF} font-size="21" font-weight="700" fill="{P["ink-a"]}">{esc(title)}</text>'
        f'<path d="M{_g(x + tw + 7)},89 l4,-4 l4,4 l-4,4 z" fill="{P["ink-red"]}"/>'
        f'<text x="{_g(sub_x)}" y="96" {SERIF} font-size="15" font-weight="700" fill="{P["ink-red"]}" letter-spacing="0.5">{esc(sub)}</text>'
        f'<rect x="{x}" y="106.4" width="150" height="1.2" fill="url(#divider)"/>'
        f'<text x="{x - 1}" y="143" {SERIF} font-size="{score_size}" font-weight="700" fill="{P["ink-red"]}" letter-spacing="0.5">{esc(score)}</text>'
        f'<text x="{x + 1}" y="165" {MONO} font-size="14" fill="{P["ink-b"]}">{esc(small)}</text>'
        "</g>"
    )
    return _hanging(i) + window + text


def render_picoctf(lang: Lang, fonts) -> str:
    """picoCTF practice score (content.PICOCTF) on a tablet of the achievements family, 410x200."""
    i = len(ACHIEVEMENTS) + 1
    title = f"{PICOCTF['title'](lang)} · {PICOCTF['sub'](lang)} · {PICOCTF['score']} pts · {PICOCTF['user']}"
    return _card(i, -3.8, _pico_tablet(lang, i), title, PICO_ACCENT, fonts)


# ---------------------------------------------------------------- CTFtime team (owner edit 7)
#
# Header: a small red pennant, the role and the team name. A lacquered panel holds the
# headline places (best global place and best India place, each with its year) and a
# three-step climb: one torii per year with the place above and the year below. The
# climb switches between the world ranks (state A) and the India ranks (state B) on an
# 8 s CSS loop (hold 3.4 s, crossfade 0.6 s): the gates grow and shrink from their feet,
# the labels and the caption crossfade, and the best gate of the state glows. Inline
# styles hold state A, so a late-loading image never shows a blank frame.

CTF_PANEL = (30, 96, 380, 176)
CTF_SPLIT = 206  # headline | climb
CTF_HEAD = 21
CTF_GROUND = 150
CTF_YEAR_Y = 167
TORII_VIS = (22 - 5.2) / 24  # visible height of GLYPH['torii'] per unit of icon size
CTF_STEP_X = (240, 292, 344)
CTF_CYCLE = 8  # s: A hold 0-42.5%, fade to 50%, B hold to 92.5%, fade back to 100%
CTF_H_MIN, CTF_H_MAX = 14, 26  # visible torii height for the worst and the best place


def _ctf_keys(a: str, b: str) -> str:
    return f"0%,42.5%{{{a}}}50%,92.5%{{{b}}}100%{{{a}}}"


def _ctf_scale(h: float) -> str:
    """Gate scale for visible height h: mostly scaleY, with a gentler scaleX so a small gate is not squashed."""
    sy = h / CTF_H_MAX
    return f"scale({sy ** 0.5:.3f},{sy:.3f})"


def _ctf_css() -> str:
    hw, hi = _ctf_heights("world"), _ctf_heights("india")
    bw, bi = _ctf_best("world"), _ctf_best("india")
    gates = "".join(
        f"@keyframes gate{k}{{{_ctf_keys('transform:' + _ctf_scale(a), 'transform:' + _ctf_scale(b))}}}"
        f"@keyframes glow{k}{{{_ctf_keys(f'opacity:{int(k == bw)}', f'opacity:{int(k == bi)}')}}}"
        for k, (a, b) in enumerate(zip(hw, hi))
    )
    return (
        ".lit{animation:lit .7s ease-out both}"
        "@keyframes lit{from{opacity:.15}to{opacity:1}}"
        f".ctfA{{animation:ctfA {CTF_CYCLE}s ease-in-out infinite}}"
        f".ctfB{{animation:ctfB {CTF_CYCLE}s ease-in-out infinite}}"
        f"@keyframes ctfA{{{_ctf_keys('opacity:1', 'opacity:0')}}}"
        f"@keyframes ctfB{{{_ctf_keys('opacity:0', 'opacity:1')}}}"
        ".gate{transform-box:fill-box;transform-origin:50% 100%}"
        + gates
    )


def _ctf_ranks(state: str) -> list[int]:
    return [w if state == "world" else n for _, w, _, n in CTFTIME["years"]]


def _ctf_best(state: str) -> int:
    ranks = _ctf_ranks(state)
    return ranks.index(min(ranks))


def _ctf_heights(state: str) -> list[float]:
    """Visible torii height per year: the best place gets CTF_H_MAX, the worst CTF_H_MIN,
    linear in the place in between (the smallest gate stays readable)."""
    ranks = _ctf_ranks(state)
    best, worst = min(ranks), max(ranks)
    span = CTF_H_MAX - CTF_H_MIN
    return [round(CTF_H_MIN + span * (1 - (r - best) / (worst - best + 1e-9)), 1) for r in ranks]


def _pennant(x: float, y: float) -> str:
    return (
        f'<g transform="translate({_g(x)},{_g(y)})">'
        f'<rect x="-1" y="-10" width="2" height="20" rx="1" fill="{P["ink-a"]}"/>'
        f'<path d="M1,-10 L15,-5.5 L1,-1 Z" fill="{P["vermilion"]}" stroke="{P["ink-a"]}" stroke-opacity="0.5" stroke-width="0.6"/></g>'
    )


def _ctf_tablet(lang: Lang, i: int) -> str:
    role, team = CTFTIME["role"](lang), CTFTIME["team"]
    years = CTFTIME["years"]
    best_world = min(years, key=lambda r: r[1])
    best_india = min(years, key=lambda r: r[3])
    # header, centred: pennant, role, diamond, team
    rw = text_width(role, 15, weight=700, letter_spacing=0.5)
    tw = text_width(team, 20, weight=700)
    total = 22 + rw + 22 + tw
    x = CX - total / 2
    head = (
        _pennant(x + 2, 76)
        + f'<g filter="url(#carve)"><text x="{_g(x + 22)}" y="82" {SERIF} font-size="15" font-weight="700" fill="{P["ink-red"]}" '
        f'letter-spacing="0.5">{esc(role)}</text>'
        f'<path d="M{_g(x + 22 + rw + 7)},76 l4,-4 l4,4 l-4,4 z" fill="{P["ink-red"]}"/>'
        f'<text x="{_g(x + 22 + rw + 22)}" y="82" {SERIF} font-size="20" font-weight="700" fill="{P["ink-a"]}">{esc(team)}</text></g>'
    )
    x0, y0, x1, y1 = CTF_PANEL
    panel = (
        f'<rect x="{x0 - 2}" y="{y0 - 2}" width="{x1 - x0 + 4}" height="{y1 - y0 + 4}" rx="10" fill="{P["ink-a"]}" opacity="0.35"/>'
        f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="8" fill="url(#panelG)" '
        f'stroke="{P["lantern-gold"]}" stroke-opacity="0.8" stroke-width="1.6"/>'
        f'<rect x="{x0 + 4}" y="{y0 + 4}" width="{x1 - x0 - 8}" height="{y1 - y0 - 8}" rx="5" fill="none" '
        f'stroke="{P["lantern-gold"]}" stroke-opacity="0.25" stroke-width="0.8"/>'
        f'<rect x="{x0 + 1}" y="{y0 + 1}" width="{x1 - x0 - 2}" height="{_g((y1 - y0) / 2)}" rx="7" fill="url(#gloss)"/>'
        f'<rect x="{CTF_SPLIT - 0.5}" y="{y0 + 10}" width="1" height="{y1 - y0 - 20}" fill="{P["lantern-gold"]}" opacity="0.25"/>'
    )
    # headline: two places, each with its year
    lines = []
    for k, (label, (year, *_), colour) in enumerate((
        (CTFTIME["world"](lang).format(n=best_world[1]), best_world, P["lantern-gold"]),
        (CTFTIME["india"](lang).format(n=best_india[3]), best_india, P["moon-a"]),
    )):
        y = 127 + k * 31
        lw = text_width(label, CTF_HEAD, weight=700)
        if x0 + 14 + lw + 8 + text_width(str(year), 14) > CTF_SPLIT - 6:
            raise ValueError(f"CTFtime headline ({lang}) does not fit: {label}")
        lines.append(
            f'<text x="{x0 + 14}" y="{y}" {SERIF} font-size="{CTF_HEAD}" font-weight="700" fill="{colour}">{esc(label)}</text>'
            f'<text x="{_g(x0 + 14 + lw + 8)}" y="{y}" {SERIF} font-size="14" fill="{P["text-soft-b"]}">{year}</text>'
        )
    # the climb: world ranks (A) <-> India ranks (B)
    hw, hi = _ctf_heights("world"), _ctf_heights("india")
    bw, bi = _ctf_best("world"), _ctf_best("india")
    size = CTF_H_MAX / TORII_VIS
    soft, gold = P["text-soft-a"], P["lantern-gold"]
    steps = []
    for k, ((year, world, _pts, india), sx) in enumerate(zip(years, CTF_STEP_X)):
        anim = f"{CTF_CYCLE}s ease-in-out infinite"
        glow_a = int(k == bw)
        steps.append(
            f'<g class="step" data-year="{year}" data-world="{world}" data-india="{india}" data-hw="{hw[k]:g}" data-hi="{hi[k]:g}">'
            f'<g class="lit" style="animation-delay:{0.35 * k + 0.2:g}s">'
            f'<ellipse cx="{sx}" cy="{_g(CTF_GROUND - CTF_H_MAX / 2)}" rx="20" ry="21" fill="url(#lanternGlow)" class="lglow" '
            f'style="opacity:{glow_a * 0.5:g};animation:glow{k} {anim}"/>'
            f'<g class="gate" style="transform:{_ctf_scale(hw[k])};animation:gate{k} {anim}">'
            + icon("torii", sx - size / 2, CTF_GROUND - size * 22 / 24, size, "#b8402c")
            + f'<g style="opacity:{glow_a};animation:glow{k} {anim}">'
            + icon("torii", sx - size / 2, CTF_GROUND - size * 22 / 24, size, P["vermilion"])
            + "</g></g>"
            f'<text class="ctfA" x="{sx}" y="{_g(CTF_GROUND - hw[k] - 4)}" text-anchor="middle" {SERIF} font-size="14" '
            f'font-weight="700" fill="{gold if k == bw else soft}" style="opacity:1">#{world}</text>'
            f'<text class="ctfB" x="{sx}" y="{_g(CTF_GROUND - hi[k] - 4)}" text-anchor="middle" {SERIF} font-size="14" '
            f'font-weight="700" fill="{gold if k == bi else soft}" style="opacity:0">#{india}</text></g>'
            f'<text x="{sx}" y="{CTF_YEAR_Y}" text-anchor="middle" {SERIF} font-size="14" fill="{P["text-soft-b"]}">{year}</text>'
            "</g>"
        )
    # the state caption: a tab-like pill on the panel's top rim, centred over all three gates
    cap_x = sum(CTF_STEP_X) / len(CTF_STEP_X)
    words = [CTFTIME["state"][st](lang) for st in ("world", "india")]
    pill_w = max(text_width(w, 14, weight=700, letter_spacing=1) for w in words) + 22
    pill_h, pill_y = 17, y0 - 8
    caption = (
        '<g class="ctfCap">'
        f'<rect x="{_g(cap_x - pill_w / 2)}" y="{pill_y}" width="{_g(pill_w)}" height="{pill_h}" rx="9" '
        f'fill="{P["ink-red"]}" stroke="{P["lantern-gold"]}" stroke-width="1.2"/>'
        + "".join(
            f'<text class="{cls}" x="{_g(cap_x)}" y="{pill_y + 12.8}" text-anchor="middle" {SERIF} font-size="14" '
            f'font-weight="700" fill="{P["moon-a"]}" letter-spacing="1" style="opacity:{op}">{esc(w)}</text>'
            for cls, w, op in (("ctfA", words[0], 1), ("ctfB", words[1], 0))
        )
        + "</g><!--/ctfCap-->"
    )
    climb = (
        f'<path d="M{CTF_SPLIT + 14},{CTF_GROUND} H{x1 - 12}" stroke="{P["text-soft-b"]}" stroke-opacity="0.5" stroke-width="1"/>'
        + "".join(steps)
        + caption
    )
    return _hanging(i) + head + panel + "".join(lines) + climb


def render_ctftime(lang: Lang, fonts) -> str:
    """CTFtime team places (content.CTFTIME) on a tablet of the achievements family, 410x200."""
    i = len(ACHIEVEMENTS) + 2
    years = CTFTIME["years"]
    summary = ", ".join(f"{y}: #{p} / #{n}" for y, p, _, n in years)
    title = f"{CTFTIME['role'](lang)} · {CTFTIME['team']} · CTFtime {summary}"
    return _card(i, -1.7, _ctf_tablet(lang, i), title, P["vermilion"], fonts, css=_ctf_css(), defs=_hr_defs())
