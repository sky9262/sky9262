"""What I can do (我が道): five omamori charms hanging from the shimenawa.

Each skill is an omamori (お守り), a brocade charm bag with gold embroidery and a
knotted vermilion cord, carrying the skill's glyph in a lacquered medallion, the
title and the wrapped description. The charms sway gently, each on its own
delay; an embroidered "thread" of light circles every charm, a halo breathes
behind it and a sheen sweeps across it now and then.

Desktop: viewBox 1200x560 shown at 846 px, 3 + 2 charms; the second row hangs on
long cords that pass between the charms of the first. Phone: 600xPHONE_H shown
at 360 px, one column threaded on a single cord like a tsurushi-kazari.
"""
from __future__ import annotations

from typing import Literal

from ..content import CANDO, SECTION, Lang
from ..icons import icon
from ..metrics import text_width, wrap
from ..palette import PALETTE as P
from ..svg import (
    MOTION_CSS,
    document,
    embed_fonts,
    esc,
    heading_defs,
    night_bg,
    petal_def,
    petals,
    rope,
    rope_y,
    section_heading,
)

Layout = Literal["desktop", "phone"]

RX = 16
SERIF = 'font-family="Shrine Serif"'

# Body text: >= 12 px rendered (desktop 846/1200, phone 360/600).
BODY_SIZE = {"desktop": 17.2, "phone": 20}
TITLE_SIZE = {"desktop": 23, "phone": 26}
LINE_H = {"desktop": 26, "phone": 30}
TILE_W = {"desktop": 368, "phone": 544}
PAD = {"desktop": 16, "phone": 24}
TEXT_W = {k: TILE_W[k] - 2 * PAD[k] for k in TILE_W}
MED_R = {"desktop": 21, "phone": 23}  # medallion radius; it sits on the charm's top edge
CHAMFER = 14

ROPE_TOP = {"desktop": 60, "phone": 66}  # translate of the rope group
HEAD_Y = {"desktop": 44, "phone": 48}
TASSELS = {
    "desktop": tuple((2 * i + 1) / 12 for i in range(6)),
    "phone": (0.14, 0.32, 0.68, 0.86),
}

# accent per skill: cord-side glow, stitch thread, medallion icon
ACCENT = {
    "agent": P["circuit-cyan"],
    "rag": P["lantern-gold"],
    "local": P["text-soft-b"],
    "gen3d": P["sakura-b"],
    "shield": P["vermilion"],
}

# The sheen is a skewed band, SHEEN_W wide, slanting by SHEEN_SKEW over the charm's
# height. It sweeps from fully left of the charm to fully right of it.
SHEEN_W = 90
SHEEN_SKEW = 56


def _sheen_reach(layout: Layout) -> float:
    """How far the band reaches past either side of the charm during its sweep."""
    return SHEEN_W + SHEEN_SKEW + 20


def _css(layout: Layout) -> str:
    start = -(SHEEN_W + 20)
    end = TILE_W[layout] + SHEEN_SKEW + 20
    return (
        ".thread{stroke-dasharray:3 5;animation:thread 9s linear infinite}"
        "@keyframes thread{to{stroke-dashoffset:-160}}"
        ".halo{animation:breathe 5s ease-in-out infinite}"
        # the wide phone charms swing through a smaller angle than the shared ±1.4deg
        ".swayw{animation-name:swayw}@keyframes swayw{0%,100%{transform:rotate(-.7deg)}50%{transform:rotate(.7deg)}}"
        ".sheen{animation:sheen 10s ease-in-out infinite}"
        f"@keyframes sheen{{0%,62%{{transform:translateX({start}px)}}86%,100%{{transform:translateX({end}px)}}}}"
    )


def _g(v: float) -> str:
    return f"{round(v, 2):g}"


def _mix(a: str, b: str, t: float) -> str:
    """Blend hex colour a toward b by t (0 = a, 1 = b)."""
    ca = [int(a[i : i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


# ---------------------------------------------------------------- text


def body_lines(lang: Lang, layout: Layout) -> list[list[str]]:
    """The wrapped description of every skill, in CANDO order."""
    return [wrap(line(lang), BODY_SIZE[layout], TEXT_W[layout]) for _, _, line in CANDO]


def title_fit(title: str, layout: Layout) -> tuple[float, float]:
    """(font size, letter-spacing) for a title: tracking tightens first (to -0.08 em,
    usual for Japanese display type), and only then does the size shrink."""
    size = TITLE_SIZE[layout]
    room = TEXT_W[layout] - 12  # titles keep clear of the embroidery
    ls = 0.5
    if text_width(title, size, weight=700, letter_spacing=ls) <= room:
        return size, ls
    n = len(title)
    ls = (room - text_width(title, size, weight=700)) / n
    if ls >= -0.08 * size:
        return size, round(ls - 0.005, 2)
    # shrink at the tightest tracking: w(s) = glyphs*s - 0.08*s*n
    glyphs = text_width(title, 1, weight=700)
    size = max(BODY_SIZE[layout], round(room / (glyphs - 0.08 * n) - 0.05, 1))
    return size, round(-0.08 * size, 2)


def tile_height(layout: Layout) -> float:
    """One height for every charm: the longest description in either language."""
    n = max(len(ls) for lang in ("jp", "en") for ls in body_lines(lang, layout))
    return _body_top(layout) + (n - 1) * LINE_H[layout] + BODY_SIZE[layout] * 0.35 + PAD[layout] - 2


def _title_y(layout: Layout) -> float:
    return MED_R[layout] + 12 + TITLE_SIZE[layout] * 0.95


def _body_top(layout: Layout) -> float:
    """Baseline of the first body line when the block is full."""
    return _title_y(layout) + 14 + 12 + BODY_SIZE[layout]


# ---------------------------------------------------------------- defs


def _shape(w: float, h: float, inset: float = 0) -> str:
    c, r, i = CHAMFER, 10, inset
    return (
        f"M{_g(c + i * 0.4)},{_g(i)} L{_g(w - c - i * 0.4)},{_g(i)} L{_g(w - i)},{_g(c + i * 0.4)} "
        f"L{_g(w - i)},{_g(h - r - i)} Q{_g(w - i)},{_g(h - i)} {_g(w - r - i)},{_g(h - i)} "
        f"L{_g(r + i)},{_g(h - i)} Q{_g(i)},{_g(h - i)} {_g(i)},{_g(h - r - i)} L{_g(i)},{_g(c + i * 0.4)} Z"
    )


def _defs(w: int, h: int, tw: float, th: float) -> str:
    brocade = "".join(
        f'<linearGradient id="br-{k}" x1="0" y1="0" x2="0.35" y2="1">'
        f'<stop offset="0" stop-color="{_mix(P["night-1"], a, 0.30)}"/>'
        f'<stop offset="0.55" stop-color="{_mix(P["night-1"], a, 0.12)}"/>'
        f'<stop offset="1" stop-color="{_mix(P["night-0"], a, 0.06)}"/></linearGradient>'
        f'<radialGradient id="glow-{k}" cx="0.5" cy="0.5" r="0.5">'
        f'<stop offset="0" stop-color="{a}" stop-opacity="0.34"/><stop offset="1" stop-color="{a}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="mglow-{k}" cx="0.5" cy="0.5" r="0.5">'
        f'<stop offset="0.4" stop-color="{a}" stop-opacity="0.75"/><stop offset="1" stop-color="{a}" stop-opacity="0"/></radialGradient>'
        for k, a in ACCENT.items()
    )
    # seigaiha (青海波) wave pattern for the brocade
    sei = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{r}"/>' for cx, cy in ((0, 12), (24, 12), (12, 0), (12, 24), (0, 24), (24, 24)) for r in (11, 7.5, 4)
    )
    return (
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="{RX}"/></clipPath>'
        + petal_def()
        + heading_defs()
        + brocade
        + f'<pattern id="seigaiha" width="24" height="12" patternUnits="userSpaceOnUse">'
        f'<g fill="{P["night-0"]}" fill-opacity="0.12" stroke="{P["lantern-gold"]}" stroke-opacity="0.075" stroke-width="0.8">{sei}</g></pattern>'
        f'<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0.45"/>'
        f'<stop offset="0.5" stop-color="{P["vermilion"]}" stop-opacity="0.18"/>'
        f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0.35"/></linearGradient>'
        f'<linearGradient id="sheenG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{P["moon-a"]}" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="{P["moon-a"]}" stop-opacity="0.13"/><stop offset="1" stop-color="{P["moon-a"]}" stop-opacity="0"/></linearGradient>'
        f'<radialGradient id="lacquer" cx="0.5" cy="0.38" r="0.65"><stop offset="0" stop-color="#2a1d46"/>'
        f'<stop offset="1" stop-color="{P["night-0"]}"/></radialGradient>'
        f'<linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["night-2"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{P["night-2"]}" stop-opacity="0.85"/></linearGradient>'
        f'<linearGradient id="divider" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="{P["lantern-gold"]}" stop-opacity="0.7"/><stop offset="1" stop-color="{P["lantern-gold"]}" stop-opacity="0"/></linearGradient>'
        f'<path id="charm" d="{_shape(tw, th)}"/>'
        f'<clipPath id="charmClip"><path d="{_shape(tw, th)}"/></clipPath>'
        '<filter id="hang" x="-10%" y="-10%" width="120%" height="135%">'
        '<feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#000" flood-opacity="0.6"/></filter>'
        '<filter id="lift" x="-10%" y="-40%" width="120%" height="180%">'
        f'<feDropShadow dx="0" dy="1.5" stdDeviation="1.5" flood-color="{P["night-0"]}" flood-opacity="0.9"/></filter>'
    )


# ---------------------------------------------------------------- pieces


def _stars(w: int, h: int, n: int, seed: int) -> str:
    out = []
    x, y = seed * 37 % w, seed * 53 % h
    for i in range(n):
        x = (x + 263 + i * 71) % w
        y = (y + 157 + i * 29) % (h * 0.9)
        r = 0.8 + (i % 3) * 0.25
        cls = ' class="node"' + (f' style="animation-delay:-{i % 5 * 0.5:g}s"' if i % 5 else "") if i % 3 == 0 else ' opacity="0.55"'
        out.append(f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{r:g}"{cls}/>')
    return '<g fill="#fff">' + "".join(out) + "</g>"


def _knot(x: float, y: float) -> str:
    """A small hanamusubi (花結び) knot: two loops and two short tails."""
    v = P["vermilion"]
    return (
        f'<g transform="translate({_g(x)},{_g(y)})" fill="none" stroke="{v}" stroke-width="2.4" stroke-linecap="round">'
        '<path d="M0,0 C-10,-9 -15,1 -6,4 Z M0,0 C10,-9 15,1 6,4 Z"/>'
        '<path d="M0,0 l-4,9 M0,0 l4,9"/>'
        f'<circle r="2.8" fill="{v}" stroke="none"/></g>'
    )


def _charm(i: int, item: tuple, lang: Lang, layout: Layout, x: float, y: float, th: float, lines: list[str]) -> str:
    """One charm, its top-left at (x, y); the medallion is centred on its top edge."""
    key, title_t, _ = item
    tw, pad, mr = TILE_W[layout], PAD[layout], MED_R[layout]
    a = ACCENT[key]
    cx = tw / 2
    size, lh = BODY_SIZE[layout], LINE_H[layout]
    title = title_t(lang)
    ts, tls = title_fit(title, layout)
    ty = _title_y(layout)
    # centre the body block in the space below the divider
    full = (max_lines(layout) - 1) * lh
    top = _body_top(layout) + (full - (len(lines) - 1) * lh) / 2
    body = "".join(
        f'<text x="{pad}" y="{_g(top + j * lh)}" {SERIF} font-size="{_g(size)}" fill="{P["text-soft-a"]}">{esc(t)}</text>'
        for j, t in enumerate(lines)
    )
    dy = ty + 15
    div_w = min(tw - 2 * pad, 170)
    stitch = _shape(tw, th, 7)
    reach = _sheen_reach(layout)
    ico = mr * 1.12
    return (
        f'<g transform="translate({_g(x)},{_g(y)})">'
        # the charm and its embroidery
        f'<use href="#charm" xlink:href="#charm" fill="url(#br-{key})" filter="url(#hang)"/>'
        f'<use href="#charm" xlink:href="#charm" fill="url(#seigaiha)"/>'
        f'<path d="{_shape(tw, th, 3.5)}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.55" stroke-width="1.3"/>'
        f'<path class="thread" d="{stitch}" fill="none" stroke="{a}" stroke-opacity="0.75" stroke-width="1.4" '
        f'style="animation-delay:-{i * 1.7:g}s"/>'
        f'<g clip-path="url(#charmClip)">'
        f'<path class="sheen" d="M0,0 h{SHEEN_W} l-{SHEEN_SKEW},{_g(th)} h-{SHEEN_W} z" fill="url(#sheenG)" '
        f'style="animation-delay:{i * 1.3:g}s"/></g>'
        # medallion with the glyph
        f'<circle cx="{_g(cx)}" r="{_g(mr * 2.3)}" fill="url(#mglow-{key})" class="lglow" style="animation-delay:-{i * 0.6:g}s"/>'
        f'<circle cx="{_g(cx)}" r="{_g(mr)}" fill="url(#lacquer)" stroke="{P["lantern-gold"]}" stroke-width="1.6"/>'
        f'<circle cx="{_g(cx)}" r="{_g(mr - 3.5)}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.3" stroke-width="0.8"/>'
        + icon(key, cx - ico / 2, -ico / 2, ico, a)
        # title, divider, description
        + f'<g filter="url(#lift)"><text x="{_g(cx)}" y="{_g(ty)}" text-anchor="middle" {SERIF} font-size="{_g(ts)}" '
        f'font-weight="700" fill="{P["lantern-gold"]}" letter-spacing="{_g(tls)}">{esc(title)}</text>'
        f'<rect x="{_g(cx - div_w / 2)}" y="{_g(dy)}" width="{_g(div_w)}" height="1.2" fill="url(#divider)"/>'
        f'<path d="M{_g(cx)},{_g(dy - 3.4)} l4,4 l-4,4 l-4,-4 z" fill="{a}"/>'
        f"{body}</g>"
        # invisible span over the sheen's whole sweep: the swaying group's fill-box,
        # and so its pivot, stays fixed while the band moves
        f'<rect x="{_g(-reach)}" y="0" width="{_g(tw + 2 * reach)}" height="1" fill="none"/>'
        "</g>"
    )


def max_lines(layout: Layout) -> int:
    return max(len(ls) for lang in ("jp", "en") for ls in body_lines(lang, layout))


# ---------------------------------------------------------------- layouts

PHONE_GAP = 34


def _positions(layout: Layout, th: float) -> list[tuple[float, float]]:
    tw = TILE_W[layout]
    if layout == "desktop":
        gap = 26
        x0 = (1200 - 3 * tw - 2 * gap) / 2
        y1 = 118
        y2 = y1 + th + MED_R[layout] + 14
        row1 = [(x0 + k * (tw + gap), y1) for k in range(3)]
        mids = [x0 + tw + gap / 2, x0 + 2 * tw + 1.5 * gap]
        return row1 + [(m - tw / 2, y2) for m in mids]
    x = (600 - tw) / 2
    y1 = 124
    return [(x, y1 + k * (th + PHONE_GAP)) for k in range(5)]


def size_of(layout: Layout) -> tuple[int, int]:
    if layout == "desktop":
        return 1200, 560
    th = tile_height(layout)
    _, last_y = _positions(layout, th)[-1]
    return 600, int(round(last_y + th + 22))


# Stagger for the shared 5 s sway: every charm at a different phase.
SWAY_DELAYS = (0, -1.1, -2.3, -3.4, -4.3)


def _scene(layout: Layout, w: int, h: int, lang: Lang) -> str:
    th = tile_height(layout)
    pos = _positions(layout, th)
    rope_dy = ROPE_TOP[layout]
    tw, mr = TILE_W[layout], MED_R[layout]
    lines = body_lines(lang, layout)
    halos, cords, charms = [], [], []
    v = P["vermilion"]
    for i, (item, (x, y)) in enumerate(zip(CANDO, pos)):
        cx = x + tw / 2
        if layout == "desktop":
            top = rope_dy + rope_y(w, cx)
        else:
            top = rope_dy + rope_y(w, cx) if i == 0 else pos[i - 1][1] + th - 4
        cord = (
            f'<path d="M{_g(cx)},{_g(top)} L{_g(cx)},{_g(y - mr - 8)}" stroke="{v}" stroke-width="2.4" stroke-linecap="round"/>'
            + _knot(cx, y - mr - 6)
        )
        halos.append(
            f'<ellipse cx="{_g(cx)}" cy="{_g(y + th / 2)}" rx="{_g(tw * 0.62)}" ry="{_g(th * 0.72)}" '
            f'fill="url(#glow-{item[0]})" class="halo" style="animation-delay:-{i * 1.3:g}s"/>'
        )
        body = _charm(i, item, lang, layout, x, y, th, lines[i])
        cls = "sway" if layout == "desktop" else "sway swayw"
        sway = f'<g class="{cls}" style="animation-delay:{SWAY_DELAYS[i]:g}s">'
        if layout == "desktop":
            charms.append(f"{sway}{cord}{body}</g>")
        else:
            # phone: the cord threads behind every charm; each charm swings on its knot
            cords.append(
                f'<path d="M{_g(cx)},{_g(top)} L{_g(cx)},{_g(y - mr - 8)}" stroke="{v}" stroke-width="2.4" stroke-linecap="round"/>'
            )
            charms.append(f"{sway}{_knot(cx, y - mr - 6)}{body}</g>")
    if layout == "desktop":
        # draw row 2 first so its long cords pass behind row 1
        charms = charms[3:] + charms[:3]
    head = section_heading(
        SECTION["cando"](lang), w / 2, HEAD_Y[layout], 30 if layout == "desktop" else 34, 20 if layout == "desktop" else 22
    )
    pet = (
        [(90, 1.1, 12, -2), (330, 0.8, 15, -9), (520, 1.2, 11, -5), (760, 0.9, 14, -1), (980, 1.3, 13, -7), (1150, 0.8, 16, -11)]
        if layout == "desktop"
        else [(60, 1.1, 13, -2), (210, 0.8, 16, -9), (380, 1.2, 12, -5), (560, 0.9, 15, -1), (640, 1, 14, -7)]
    )
    if layout == "phone":  # petals fall the full height of the tall card
        pet = [(x, s, d * h / 440, dl * h / 440) for x, s, d, dl in pet]
    return (
        night_bg(w, h, RX)
        + _stars(w, h, 26 if layout == "desktop" else 30, 7)
        + f'<rect y="{_g(h * 0.55)}" width="{w}" height="{_g(h * 0.45)}" fill="url(#mist)"/>'
        + "".join(halos)
        + head
        + f'<g transform="translate(0,{rope_dy})">{rope(w, TASSELS[layout])}</g>'
        + "".join(cords)
        + petals(pet)
        + "".join(charms)
    )


def _frame(w: int, h: int) -> str:
    return (
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{RX - 0.75}" '
        f'fill="none" stroke="url(#frame)" stroke-width="1.5"/>'
    )


def render_cando(lang: Lang, layout: Layout, fonts) -> str:
    w, h = size_of(layout)
    th = tile_height(layout)
    body = f'<g clip-path="url(#card)">{_scene(layout, w, h, lang)}</g>{_frame(w, h)}'
    title = SECTION["cando"](lang) + " · " + " / ".join(t(lang) for _, t, _ in CANDO)
    svg = document(w, h, body, title=title, css=MOTION_CSS + _css(layout), defs=_defs(w, h, TILE_W[layout], th))
    return embed_fonts(svg, fonts)
