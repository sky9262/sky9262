"""Flip plaques (絵馬): one wooden prayer plaque per project, 420x360, shown at 360 px.

Ported from the approved prototype ema-flip.svg. The plaque hangs from the
shimenawa by a red cord and sways; it flips itself on a 12 s timer (GitHub shows
SVGs as <img>, so there is no hover): the front (表) carries the name and an
animated motif, the back (裏) the details. Every animated face is delayed by
-1.5 s x index, so a row of plaques flips in a slow wave.

Stdlib only: the CI generator calls render_plaque() for live star counts.
"""
from __future__ import annotations

import random

from ..content import NDA, Lang, Plaque
from ..icons import icon
from ..metrics import text_width
from ..palette import PALETTE as P
from ..svg import MOTION_CSS, document, embed_fonts, esc, petal_def, petals, rope

W, H = 420, 360
CX = 210
LEFT, RIGHT = 28, 392  # inner text box of the plaque
INNER_W = RIGHT - LEFT  # 364
MIN_SIZE = 14  # 12 px at 360 rendered
SHOULDER, PEAK, BOTTOM = 88, 50, 352
PL, PR = 16, 404  # plaque edges

SERIF = 'font-family="Shrine Serif"'
MONO = 'font-family="Shrine Mono"'
MONO_W = 0.6
EDGE = "#6b4420"  # plaque outline, darker than the grain
STAMP = P["ink-red"]
TEAL = "#0f3a40"

STAMP_C = (360, 314)  # stamp centre, same on both faces
STAMP_R = 30
MOTIF_C = (210, 282)
WINDOW_R = 54

FLIP_CSS = """
.front{transform-origin:210px 200px;animation:front 12s ease-in-out infinite}
.back{transform-origin:210px 200px;animation:back 12s ease-in-out infinite}
@keyframes front{0%,40%{transform:scaleX(1)}45%,95%{transform:scaleX(0)}100%{transform:scaleX(1)}}
@keyframes back{0%,45%{transform:scaleX(0)}50%,90%{transform:scaleX(1)}95%,100%{transform:scaleX(0)}}
.sheen{animation:sheen 12s ease-in-out infinite}
@keyframes sheen{0%,6%{transform:translateX(-300px)}26%,100%{transform:translateX(300px)}}
.spin{animation:spin 14s linear infinite}
.spinr{animation:spin 26s linear infinite reverse}
.spinc{transform-box:fill-box;transform-origin:center;animation:spin 6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.core{transform-box:fill-box;transform-origin:center;animation:core 2.6s ease-in-out infinite}
@keyframes core{0%,100%{transform:scale(.85)}50%{transform:scale(1.15)}}
"""


def _g(v: float) -> str:
    return f"{round(v, 2):g}"


# ---------------------------------------------------------------- text fitting


def _fit(text: str, size: float, width: float, *, weight: int = 400, ls: float = 0, floor: float = MIN_SIZE) -> float:
    """Largest size <= `size` (not below `floor`) at which `text` fits `width`."""
    w = text_width(text, size, weight=weight, letter_spacing=ls)
    if w <= width:
        return size
    # letter-spacing does not scale with size, so solve for the glyph part only
    glyphs = text_width(text, 1000, weight=weight) / 1000
    return max(floor, round((width - ls * len(text)) / glyphs - 0.05, 1))


def back_text(p: Plaque, lang: Lang) -> tuple[float, list[str]]:
    """(font size, lines) of the back description: one size per plaque, never below 14."""
    lines = p.lines(lang).split("\n")
    base = 15 if lang == "jp" else 15.5
    size = min(_fit(line, base, INNER_W) for line in lines)
    return size, lines


def _split_title(text: str) -> list[str]:
    """Split a long Latin title at the space that best balances the two halves."""
    words = text.split(" ")
    best, best_d = [text], float("inf")
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        d = abs(text_width(a, 1, weight=700) - text_width(b, 1, weight=700))
        if d < best_d:
            best, best_d = [a, b], d
    return best


# ---------------------------------------------------------------- defs


def _defs() -> str:
    shape = f"M{PL},{SHOULDER} L{CX},{PEAK} L{PR},{SHOULDER} L{PR},{BOTTOM} L{PL},{BOTTOM} Z"
    inset = f"M{PL + 7},{SHOULDER + 4} L{CX},{PEAK + 8} L{PR - 7},{SHOULDER + 4} L{PR - 7},{BOTTOM - 7} L{PL + 7},{BOTTOM - 7} Z"
    grain = "".join(
        f'<path d="M{PL},{y} C{PL + 110},{y - 9 + d} {PR - 140},{y + 9 - d} {PR},{y - 3}"/>'
        for y, d in ((112, 0), (150, 4), (186, -2), (224, 5), (262, 1), (298, -4), (334, 3))
    )
    return (
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
        + petal_def()
        + f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["night-0"]}"/>'
        f'<stop offset="0.65" stop-color="{P["night-1"]}"/><stop offset="1" stop-color="{P["night-2"]}"/></linearGradient>'
        f'<radialGradient id="halo" cx="0.5" cy="0.55" r="0.55"><stop offset="0" stop-color="{P["lantern-glow-a"]}" stop-opacity="0.32"/>'
        f'<stop offset="1" stop-color="{P["lantern-glow-a"]}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="wood" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["wood-a"]}"/>'
        f'<stop offset="0.55" stop-color="#c3914f"/><stop offset="1" stop-color="{P["wood-b"]}"/></linearGradient>'
        f'<linearGradient id="woodBack" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e2c08e"/>'
        f'<stop offset="1" stop-color="#c49a62"/></linearGradient>'
        f'<linearGradient id="sheenG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff4dc" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="#fff4dc" stop-opacity="0.28"/><stop offset="1" stop-color="#fff4dc" stop-opacity="0"/></linearGradient>'
        f'<radialGradient id="lacquer" cx="0.5" cy="0.4" r="0.65"><stop offset="0" stop-color="#22163a"/>'
        f'<stop offset="1" stop-color="{P["night-0"]}"/></radialGradient>'
        f'<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0.45"/>'
        f'<stop offset="0.5" stop-color="{P["vermilion"]}" stop-opacity="0.18"/>'
        f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0.35"/></linearGradient>'
        f'<path id="shape" d="{shape}"/>'
        f'<path id="inset" d="{inset}" fill="none" stroke="{P["moon-b"]}" stroke-opacity="0.28" stroke-width="1.2"/>'
        f'<clipPath id="plaqueClip"><path d="{shape}"/></clipPath>'
        f'<g id="grain" clip-path="url(#plaqueClip)" stroke="{P["wood-grain"]}" stroke-opacity="0.22" fill="none" stroke-width="1.3">{grain}</g>'
        f'<clipPath id="win"><circle cx="0" cy="0" r="{WINDOW_R - 3}"/></clipPath>'
        '<filter id="hang" x="-10%" y="-10%" width="120%" height="130%">'
        f'<feDropShadow dx="0" dy="7" stdDeviation="7" flood-color="#000" flood-opacity="0.55"/></filter>'
        '<filter id="carve" x="-5%" y="-20%" width="110%" height="150%">'
        f'<feDropShadow dx="0" dy="1" stdDeviation="0.2" flood-color="{P["moon-b"]}" flood-opacity="0.5"/></filter>'
        '<filter id="cglow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<filter id="ink" x="-10%" y="-10%" width="120%" height="120%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="7" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="1.6" xChannelSelector="R" yChannelSelector="G"/></filter>'
    )


# ---------------------------------------------------------------- frame pieces


def _scene_back() -> str:
    """Card background, halo, stars, and petals drifting behind the plaque."""
    stars = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff"' + (' class="node"' if i % 3 == 0 else ' opacity="0.6"') + "/>"
        for i, (x, y, r) in enumerate(
            ((34, 64, 1.1), (388, 52, 1.2), (60, 150, 0.9), (402, 190, 1), (22, 300, 1), (396, 330, 0.9), (110, 40, 0.8), (318, 36, 0.9))
        )
    )
    return (
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>'
        f'<rect width="{W}" height="{H}" fill="url(#halo)" class="toriiGlow"/>'
        f"{stars}"
        + petals([(70, 1, 10, -2), (300, 0.8, 12, -7), (430, 1.1, 11, -4), (200, 0.7, 14, -10.5), (520, 0.9, 13, -1)])
        + f'<g transform="translate(0,4)">{rope(W)}</g>'
    )


def _cord() -> str:
    return (
        f'<path d="M{CX},24 L188,62 M{CX},24 L232,62" stroke="{P["vermilion"]}" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
        f'<circle cx="{CX}" cy="24" r="4.5" fill="{P["vermilion"]}"/>'
        f'<path d="M{CX},27 l-3,13 l3,-2 l3,2 z" fill="{P["vermilion"]}" opacity="0.9"/>'
    )


def _board(fill: str) -> str:
    holes = "".join(
        f'<circle cx="{x}" cy="62" r="3.4" fill="{P["ink-a"]}" opacity="0.75"/>' for x in (188, 232)
    )
    return (
        # the board's thickness, seen below and to the right of the face
        f'<use href="#shape" xlink:href="#shape" transform="translate(2.5,3.5)" fill="{EDGE}"/>'
        f'<use href="#shape" xlink:href="#shape" fill="{fill}" stroke="{EDGE}" stroke-width="2"/>'
        '<use href="#grain" xlink:href="#grain"/>'
        '<use href="#inset" xlink:href="#inset"/>'
        '<g clip-path="url(#plaqueClip)"><g transform="rotate(14 75 205)">'
        '<rect class="sheen" x="40" y="20" width="70" height="370" fill="url(#sheenG)"/></g></g>'
        f"{holes}"
    )


def _cord_front() -> str:
    """The cord passes through the holes, so its lower ends sit over the board."""
    return f'<path d="M188,62 l-2,6 M232,62 l2,6" stroke="{P["vermilion"]}" stroke-width="2.6" stroke-linecap="round"/>'


# ---------------------------------------------------------------- stamps (hanko)


def _stamp(p: Plaque, stars: int | None, forks: int | None) -> tuple[str, float]:
    """(seal svg, its left edge): a hanko in the plaque's lower right corner."""
    x, y = STAMP_C
    half = STAMP_R
    if p.stamp == "prod":
        inner = (
            f'<circle r="{STAMP_R}" fill="none" stroke="{STAMP}" stroke-width="2.8"/>'
            f'<circle r="{STAMP_R - 4}" fill="none" stroke="{STAMP}" stroke-width="1"/>'
            f'<text y="0" text-anchor="middle" {SERIF} font-size="17" font-weight="700" fill="{STAMP}">本番</text>'
            f'<text y="16" text-anchor="middle" {MONO} font-size="14" font-weight="700" fill="{STAMP}">PROD</text>'
        )
    elif p.stamp == "hf":
        inner = (
            f'<circle r="{STAMP_R}" fill="{STAMP}"/>'
            f'<circle r="{STAMP_R - 4}" fill="none" stroke="{P["moon-a"]}" stroke-width="1" stroke-opacity="0.7"/>'
            f'<text y="7" text-anchor="middle" {SERIF} font-size="21" font-weight="700" fill="{P["moon-a"]}">HF</text>'
        )
    else:  # stars: filled square seal, ★ count over fork count
        moon = P["moon-a"]
        if stars is None and forks is None:
            inner = (
                f'<rect x="-27" y="-27" width="54" height="54" rx="6" fill="{STAMP}"/>'
                f'<rect x="-23" y="-23" width="46" height="46" rx="4" fill="none" stroke="{moon}" stroke-width="1" stroke-opacity="0.7"/>'
                + icon("star", -13, -18, 26, P["lantern-gold"])
                + icon("fork", -7, 8, 14, moon)
            )
        else:
            row1 = f"{stars}" if stars is not None else ""
            row2 = f"{forks} forks" if forks is not None else ""
            tw = max(MONO_W * 16 * len(row1) + 20, MONO_W * 14 * len(row2), 40)
            half = tw / 2 + 9
            x = min(x, RIGHT - half)  # a wide seal moves left to stay on the board
            star_w = 16 + (4 + MONO_W * 16 * len(row1) if row1 else 0)
            sx = -star_w / 2
            inner = (
                f'<rect x="{_g(-half)}" y="-28" width="{_g(2 * half)}" height="56" rx="6" fill="{STAMP}"/>'
                f'<rect x="{_g(-half + 4)}" y="-24" width="{_g(2 * half - 8)}" height="48" rx="4" fill="none" '
                f'stroke="{moon}" stroke-width="1" stroke-opacity="0.7"/>'
                + icon("star", sx, -17.5, 16, P["lantern-gold"])
                + (
                    f'<text x="{_g(sx + 20)}" y="-3.5" {MONO} font-size="16" font-weight="700" fill="{moon}">{esc(row1)}</text>'
                    if row1
                    else ""
                )
                + (
                    f'<text y="16" text-anchor="middle" {MONO} font-size="14" fill="{moon}">{esc(row2)}</text>'
                    if row2
                    else icon("fork", -7, 4, 14, moon)
                )
            )
    svg = f'<g transform="translate({_g(x)},{y}) rotate(-8)" filter="url(#ink)" opacity="0.92">{inner}</g>'
    return svg, x - half


# ---------------------------------------------------------------- motifs


def _window(body: str) -> str:
    """A round lacquered window (丸窓) that frames each motif."""
    x, y = MOTIF_C
    return (
        f'<g transform="translate({x},{y})">'
        f'<circle r="{WINDOW_R + 3}" fill="{P["ink-a"]}" opacity="0.35"/>'
        f'<circle r="{WINDOW_R}" fill="url(#lacquer)" stroke="{P["lantern-gold"]}" stroke-opacity="0.75" stroke-width="1.6"/>'
        f'<circle r="{WINDOW_R - 4}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.25" stroke-width="0.8"/>'
        f'<g clip-path="url(#win)">{body}</g></g>'
    )


def _sigil(delay: str) -> tuple[str, str]:
    c = P["circuit-cyan"]
    ticks = "".join(
        f'<rect x="-0.8" y="-46" width="1.6" height="{5 if i % 3 == 0 else 3}" fill="{P["lantern-gold"]}" '
        f'opacity="0.7" transform="rotate({i * 15})"/>'
        for i in range(24)
    )
    nodes = "".join(
        f'<circle cx="{x}" cy="{y}" r="3.4" fill="{c}" class="node" style="animation-delay:{d}s"/>'
        for x, y, d in ((0, -34, 0), (34, 0, -0.6), (0, 34, -1.2), (-34, 0, -1.8))
    )
    body = (
        f'<g class="spinr">{ticks}</g>'
        f'<g filter="url(#cglow)"><g class="spin">'
        f'<circle r="34" fill="none" stroke="{c}" stroke-width="1.6" stroke-dasharray="10 6"/>{nodes}</g>'
        f'<path class="flow" d="M0,-31 L0,-13 M31,0 L13,0 M0,31 L0,13 M-31,0 L-13,0" stroke="{c}" stroke-width="1.6"/>'
        f'<circle r="10" fill="{P["vermilion"]}" class="core"/>'
        f'<circle r="4" fill="{P["lantern-gold"]}"/></g>'
    )
    return body, ""


def _dashboard(delay: str) -> tuple[str, str]:
    c, gold = P["circuit-cyan"], P["lantern-gold"]
    bars = []
    for i, (h, d) in enumerate(((16, 0), (26, -0.4), (20, -0.8), (34, -1.2), (28, -1.6))):
        x = -36 + i * 10
        bars.append(
            f'<rect class="bar" x="{x}" y="{30 - h}" width="7" height="{h}" rx="1.5" '
            f'fill="{c if i != 3 else gold}" style="animation-delay:{d}s"/>'
        )
    dots = "".join(
        f'<circle cx="{x}" cy="-19" r="2.4" fill="{P["night-1"]}" class="typing" style="animation-delay:{d}s"/>'
        for x, d in ((9, 0), (17, -0.2), (25, -0.4))
    )
    body = (
        f'<path d="M-40,31 L14,31" stroke="{P["text-soft-b"]}" stroke-width="1"/>'
        f'<g filter="url(#cglow)">{"".join(bars)}</g>'
        f'<polyline class="trend" points="-33,16 -23,6 -13,11 -3,-4 7,1" fill="none" stroke="{P["sakura-b"]}" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<g class="bob"><path d="M0,-31 h34 a6,6 0 0 1 6,6 v12 a6,6 0 0 1 -6,6 h-20 l-8,8 v-8 h-6 '
        f'a6,6 0 0 1 -6,-6 v-12 a6,6 0 0 1 6,-6 z" fill="{P["moon-a"]}"/>{dots}</g>'
        f'<circle cx="34" cy="20" r="9" fill="none" stroke="{c}" stroke-width="1.4" stroke-dasharray="3 3" class="spinc"/>'
        f'<circle cx="34" cy="20" r="3" fill="{P["vermilion"]}" class="core"/>'
    )
    css = (
        ".bar{transform-box:fill-box;transform-origin:50% 100%;animation:bar 1.8s ease-in-out infinite}"
        "@keyframes bar{0%,100%{transform:scaleY(.45)}50%{transform:scaleY(1)}}"
        ".typing{animation:typing 1.2s ease-in-out infinite}"
        "@keyframes typing{0%,100%{opacity:.25}40%{opacity:1}}"
        ".trend{stroke-dasharray:60;animation:trend 3.6s ease-in-out infinite}"
        "@keyframes trend{0%{stroke-dashoffset:60}45%,80%{stroke-dashoffset:0}100%{stroke-dashoffset:-60}}"
        ".bob{animation:bob 3s ease-in-out infinite}"
        "@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-2.5px)}}"
    )
    return body, css


def _facilitator(delay: str) -> tuple[str, str]:
    moon, gold = P["moon-b"], P["lantern-gold"]
    personas = (P["vermilion"], P["circuit-cyan"], gold, P["sakura-b"])
    nodes = "".join(
        f'<g transform="rotate({i * 90}) translate(0,-38)"><g transform="rotate({-i * 90})">'
        f'<circle r="6.5" fill="{col}" opacity="0.25"/><circle r="4" fill="{col}" class="node" style="animation-delay:{-i * 0.6:g}s"/>'
        f"</g></g>"
        for i, col in enumerate(personas)
    )
    ripples = "".join(
        f'<circle r="16" fill="none" stroke="{P["circuit-cyan"]}" stroke-width="1.2" class="ripple" style="animation-delay:{d}s"/>'
        for d in (0, -1, -2)
    )
    body = (
        f'<circle r="38" fill="none" stroke="{P["text-soft-b"]}" stroke-opacity="0.45" stroke-dasharray="2 5"/>'
        f"{ripples}"
        f'<g class="spin" filter="url(#cglow)">{nodes}</g>'
        # microphone
        f'<rect x="-7.5" y="-21" width="15" height="25" rx="7.5" fill="{moon}"/>'
        f'<path d="M-7.5,-12 h15 M-7.5,-7 h15 M-7.5,-2 h15" stroke="{P["text-soft-b"]}" stroke-width="1"/>'
        f'<path d="M-12,-4 a12,12 0 0 0 24,0" fill="none" stroke="{gold}" stroke-width="2" stroke-linecap="round"/>'
        f'<path d="M0,8 v10 M-7,18 h14" stroke="{gold}" stroke-width="2" stroke-linecap="round"/>'
    )
    css = (
        ".ripple{transform-box:fill-box;transform-origin:center;animation:ripple 3s ease-out infinite}"
        "@keyframes ripple{0%{transform:scale(.8);opacity:.8}100%{transform:scale(2.1);opacity:0}}"
    )
    return body, css


def _torii_points() -> list[tuple[float, float]]:
    """Points along a torii outline (local motif coordinates), for the drone formation."""
    pts: list[tuple[float, float]] = []
    for i in range(13):  # kasagi: top beam, curving up at the ends
        x = -36 + i * 6
        pts.append((x, -24 - 4 * (x / 36) ** 2))
    for i in range(9):  # nuki: second beam
        pts.append((-28 + i * 7, -10))
    pts.append((0, -17))  # gakuzuka
    for side in (-1, 1):  # pillars, slightly splayed
        for i in range(7):
            t = i / 6
            pts.append((side * (19 + 4 * t), -18 + 8 + t * 38))
    return pts


def _drone(delay: str) -> tuple[str, str]:
    rnd = random.Random(1500)
    pts = _torii_points()
    dots, kf = [], []
    for i, (tx, ty) in enumerate(pts):
        # two scattered positions inside the window, drifting, then converge
        while True:
            sx, sy = rnd.uniform(-44, 44), rnd.uniform(-44, 40)
            if sx * sx + sy * sy < 44 * 44:
                break
        dx1, dy1 = sx - tx, sy - ty
        dx2, dy2 = dx1 + rnd.uniform(-6, 6), dy1 + rnd.uniform(-6, 6)
        a = rnd.uniform(3, 8)
        b = rnd.uniform(17, 25)
        kf.append(
            f"@keyframes dr{i}{{0%{{transform:translate({_g(dx1)}px,{_g(dy1)}px)}}"
            f"{_g(a)}%{{transform:translate({_g(dx2)}px,{_g(dy2)}px)}}"
            f"{_g(b)}%,42%{{transform:translate(0,0)}}"
            f"60%,100%{{transform:translate({_g(dx1)}px,{_g(dy1)}px)}}}}"
        )
        dots.append(
            f'<circle cx="{_g(tx)}" cy="{_g(ty)}" r="1.9" class="dr" style="animation-name:dr{i},drc;animation-delay:{delay}"/>'
        )
    outline = (
        "M-38,-25 Q0,-20 38,-25 M-30,-10 H30 M0,-22 V-10 "
        "M-19,-22 L-23,30 M19,-22 L23,30"
    )
    body = (
        f'<path d="M-44,32 H44" stroke="{P["text-soft-b"]}" stroke-opacity="0.35" stroke-dasharray="1 4"/>'
        f'<path class="ghost" d="{outline}" fill="none" stroke="{P["vermilion"]}" stroke-width="5" '
        f'stroke-linecap="round" filter="url(#cglow)" style="animation-delay:{delay}"/>'
        f'<g filter="url(#cglow)">{"".join(dots)}</g>'
    )
    css = (
        ".dr{animation-duration:12s;animation-timing-function:ease-in-out;animation-iteration-count:infinite}"
        # the drones warm from cyan to lantern gold as the torii forms
        f"@keyframes drc{{0%,14%{{fill:{P['circuit-cyan']}}}26%,42%{{fill:{P['lantern-gold']}}}60%,100%{{fill:{P['circuit-cyan']}}}}}"
        ".ghost{opacity:0;animation:ghost 12s ease-in-out infinite}"
        "@keyframes ghost{0%,20%{opacity:0}28%,40%{opacity:.45}52%,100%{opacity:0}}"
        + "".join(kf)
    )
    return body, css


def _eye(delay: str) -> tuple[str, str]:
    c = P["circuit-cyan"]
    body = (
        f'<circle r="44" fill="none" stroke="{c}" stroke-opacity="0.5" stroke-width="1.2" stroke-dasharray="14 8" class="spin"/>'
        f'<g class="blink" filter="url(#cglow)">'
        f'<path d="M-38,0 Q0,-30 38,0 Q0,30 -38,0 Z" fill="{P["moon-a"]}" stroke="{c}" stroke-width="2"/>'
        f'<g class="look"><circle r="13" fill="{c}"/><circle r="13" fill="none" stroke="#0b6b70" stroke-width="2"/>'
        f'<circle r="6" fill="{P["night-0"]}"/><circle cx="-4" cy="-4" r="2.6" fill="#fff"/></g></g>'
        # the phish hook, dangling on its line
        f'<g class="dangle"><path d="M28,-60 V-18" stroke="{P["moon-b"]}" stroke-opacity="0.7" stroke-width="1"/>'
        f'<path d="M28,-18 V8 a9,9 0 0 1 -18,0 l-4,-6 m4,6 l5,-5" fill="none" stroke="{P["vermilion"]}" '
        f'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="28" cy="-19" r="2.4" fill="{P["lantern-gold"]}"/></g>'
    )
    css = (
        ".blink{animation:blink2 4.5s ease-in-out infinite}"
        "@keyframes blink2{0%,46%,54%,100%{transform:scaleY(1)}50%{transform:scaleY(.06)}}"
        ".look{animation:look 6s ease-in-out infinite}"
        "@keyframes look{0%,20%{transform:translate(0,0)}30%,48%{transform:translate(-9px,1px)}"
        "58%,78%{transform:translate(8px,-2px)}88%,100%{transform:translate(0,0)}}"
        ".dangle{animation:dangle 3.2s ease-in-out infinite}"
        "@keyframes dangle{0%,100%{transform:translateY(0)}50%{transform:translateY(5px)}}"
    )
    return body, css


def _wave(delay: str) -> tuple[str, str]:
    n = 17
    bars = []
    for i in range(n):
        x = -40 + i * 5
        env = 1 - abs(i - (n - 1) / 2) / ((n - 1) / 2)
        h = 8 + 52 * env * (0.6 + 0.4 * ((i * 7) % 5) / 4)
        bars.append(
            f'<rect class="wv" x="{_g(x - 1.6)}" y="{_g(-h / 2)}" width="3.2" height="{_g(h)}" rx="1.6" '
            f'style="animation-delay:{_g(-i * 0.11)}s"/>'
        )
    body = (
        f'<linearGradient id="wvG" gradientUnits="userSpaceOnUse" x1="-40" y1="0" x2="40" y2="0">'
        f'<stop offset="0" stop-color="{P["circuit-cyan"]}"/><stop offset="0.5" stop-color="{P["moon-a"]}"/>'
        f'<stop offset="1" stop-color="{P["sakura-b"]}"/></linearGradient>'
        f'<path d="M-46,0 H46" stroke="{P["text-soft-b"]}" stroke-opacity="0.4" stroke-width="0.8"/>'
        f'<g fill="url(#wvG)" filter="url(#cglow)">{"".join(bars)}</g>'
    )
    css = (
        ".wv{transform-box:fill-box;transform-origin:center;animation:wv 1.9s ease-in-out infinite}"
        "@keyframes wv{0%,100%{transform:scaleY(.3)}50%{transform:scaleY(1)}}"
    )
    return body, css


MOTIFS = {
    "sigil": _sigil,
    "dashboard": _dashboard,
    "facilitator": _facilitator,
    "drone": _drone,
    "eye": _eye,
    "wave": _wave,
}


# ---------------------------------------------------------------- faces


def _pill(p: Plaque) -> str:
    client = p.kind == "client"
    label = "CLIENT WORK" if client else "OPEN SOURCE"
    fg = P["lantern-gold"] if client else P["circuit-cyan"]
    bg = "#3a1d0e" if client else TEAL
    ls = 1
    tw = text_width(label, 14, mono=True, letter_spacing=ls)
    w = 12 + 15 + 7 + tw + 10
    x, y = LEFT, 98
    return (
        f'<rect x="{x}" y="{y}" width="{_g(w)}" height="26" rx="13" fill="{bg}" fill-opacity="0.9"/>'
        + icon("lock" if client else "globe", x + 11, y + 5.5, 15, fg)
        + f'<text x="{_g(x + 33)}" y="{y + 18}" {MONO} font-size="14" font-weight="700" fill="{fg}" '
        f'letter-spacing="{ls}">{label}</text>'
    )


def _front(p: Plaque, lang: Lang, delay: str, stamp: str, motif: str) -> str:
    title, sub = p.title(lang), p.subtitle(lang)
    max_w = INNER_W - 12
    size = _fit(title, 30, max_w, weight=700, floor=10)
    lines = [title]
    if size < 24 and " " in title:
        lines = _split_title(title)
        size = min(28, min(_fit(t, 28, max_w, weight=700, floor=MIN_SIZE) for t in lines))
    size = max(size, MIN_SIZE)
    sub_ls = 3 if lang == "en" else 1  # the subtitle is JP on EN plaques
    sub_size = _fit(sub, 16, max_w, ls=sub_ls)
    lh = size * 1.12
    block = lh * (len(lines) - 1) + size * 0.8 + 14 + sub_size
    top = 132 + (224 - 132 - block) / 2  # centre the title block between pill and window
    base = top + size * 0.8
    title_svg = "".join(
        f'<text x="{CX}" y="{_g(base + i * lh)}" text-anchor="middle" {SERIF} font-size="{_g(size)}" '
        f'font-weight="700" fill="{P["ink-a"]}">{esc(t)}</text>'
        for i, t in enumerate(lines)
    )
    sub_y = base + lh * (len(lines) - 1) + 14 + sub_size
    years = (
        f'<text x="{RIGHT}" y="116" text-anchor="end" {MONO} font-size="14" fill="{P["ink-b"]}">{esc(p.years)}</text>'
        if p.years
        else ""
    )
    return (
        f'<g class="front" style="animation-delay:{delay}">'
        + _board("url(#wood)")
        + icon("torii", CX - 9, 70, 18, P["ink-red"])
        + _pill(p)
        + years
        + f'<g filter="url(#carve)">{title_svg}'
        f'<text x="{CX}" y="{_g(sub_y)}" text-anchor="middle" {SERIF} font-size="{_g(sub_size)}" '
        f'fill="{P["ink-red"]}" letter-spacing="{sub_ls}">{esc(sub)}</text></g>'
        + _window(motif)
        + stamp
        + _cord_front()
        + "</g>"
    )


def _tags(tags: list[str], top: float, stamp_left: float) -> tuple[str, float]:
    """Tag chips in rows; rows that reach the stamp's height stop short of it."""
    out, x, y = [], LEFT, top
    h, gap = 24, 6
    stamp_top = STAMP_C[1] - STAMP_R - 6
    limit = lambda yy: (stamp_left - 10) if yy + h > stamp_top else RIGHT  # noqa: E731
    for t in tags:
        w = text_width(t, 14, mono=True) + 18
        if x > LEFT and x + w > limit(y):
            x, y = LEFT, y + h + gap
        if x + w > limit(y):
            raise ValueError(f"tag does not fit: {t}")
        out.append(
            f'<rect x="{_g(x)}" y="{_g(y)}" width="{_g(w)}" height="{h}" rx="5" fill="{P["ink-a"]}" fill-opacity="0.9"/>'
            f'<text x="{_g(x + w / 2)}" y="{_g(y + 16.6)}" text-anchor="middle" {MONO} font-size="14" '
            f'fill="{P["moon-a"]}">{esc(t)}</text>'
        )
        x += w + gap
    return "".join(out), y + h


def _back(p: Plaque, lang: Lang, delay: str, stamp: str, stamp_left: float) -> str:
    ink, red = P["ink-a"], P["ink-red"]
    title = p.title(lang)
    tsize = _fit(title, 17, INNER_W - 24, weight=700)
    size, lines = back_text(p, lang)
    lh = round(size * 1.62, 1)
    client = p.kind == "client"
    # vertical rhythm: strip, lines, (NDA), tags; centred in the space under the strip
    tag_rows = 2 if len(p.tags) > 2 else 1
    block = size * 0.85 + lh * (len(lines) - 1) + (30 if client else 0) + 16 + tag_rows * 30 - 6
    top = 128 + max(8, min(32, (BOTTOM - 14 - 128 - block) / 2))
    y = top + size * 0.85
    body = "".join(
        f'<text x="{LEFT}" y="{_g(y + i * lh)}" {SERIF} font-size="{_g(size)}" fill="{ink}">{esc(line)}</text>'
        for i, line in enumerate(lines)
    )
    y += lh * (len(lines) - 1)
    nda = ""
    if client:
        y += 30
        nda = (
            f'<path d="M{LEFT},{_g(y - 21)} H{RIGHT}" stroke="{red}" stroke-opacity="0.35" stroke-dasharray="2 4"/>'
            + icon("lock", LEFT, y - 12.5, 14, red)
            + f'<text x="{LEFT + 19}" y="{_g(y)}" {SERIF} font-size="14" fill="{red}">{esc(NDA(lang))}</text>'
        )
    tags, tags_bottom = _tags(p.tags, y + 16, stamp_left)
    if tags_bottom > BOTTOM - 10:
        raise ValueError(f"{p.id}/{lang}: back content overflows the plaque")
    header = (
        f'<text x="{CX}" y="82" text-anchor="middle" {SERIF} font-size="15" font-weight="700" fill="{red}">裏'
        f'<tspan {MONO} font-size="14" font-weight="400" letter-spacing="1.5" fill="{P["ink-b"]}"> · WHAT IT DOES</tspan></text>'
    )
    strip = (
        f'<rect x="{LEFT}" y="96" width="{INNER_W}" height="30" rx="4" fill="{ink}" fill-opacity="0.9"/>'
        f'<path d="M{LEFT + 6},100 H{RIGHT - 6}" stroke="{P["lantern-gold"]}" stroke-opacity="0.35"/>'
        f'<text x="{CX}" y="{_g(111 + tsize * 0.36)}" text-anchor="middle" {SERIF} font-size="{_g(tsize)}" '
        f'font-weight="700" fill="{P["lantern-gold"]}">{esc(title)}</text>'
    )
    return (
        f'<g class="back" style="animation-delay:{delay}">'
        + _board("url(#woodBack)")
        + header
        + strip
        + f'<g filter="url(#carve)">{body}{nda}</g>'
        + tags
        + stamp
        + _cord_front()
        + "</g>"
    )


# ---------------------------------------------------------------- card


def render_plaque(
    p: Plaque,
    lang: Lang,
    index: int,
    fonts,
    stars: int | None = None,
    forks: int | None = None,
) -> str:
    delay = f"-{1.5 * index:g}s"
    motif_body, motif_css = MOTIFS.get(p.motif, _sigil)(delay)
    stamp, stamp_left = _stamp(p, stars, forks)
    body = (
        '<g clip-path="url(#card)">'
        + _scene_back()
        + '<g class="sway"><g filter="url(#hang)">'
        + _cord()
        + _front(p, lang, delay, stamp, motif_body)
        + _back(p, lang, delay, stamp, stamp_left)
        + "</g></g></g>"
        + f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="15.25" fill="none" '
        'stroke="url(#frame)" stroke-width="1.5"/>'
    )
    title = f"{p.title(lang)} · {p.subtitle(lang)}"
    svg = document(W, H, body, title=title, css=MOTION_CSS + FLIP_CSS + motif_css, defs=_defs())
    return embed_fonts(svg, fonts)
