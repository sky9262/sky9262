"""Hero card (夜の神社): the first thing a visitor sees.

The scene is the owner's animated banner, embedded as a GIF (scripts/build/art/,
built by scripts.build.banner) with live text on top. Without the GIF a code-drawn
scene ported from the approved mockup is used instead, so tests need no art.

Desktop: viewBox 1200x500, shown at 846 px. Phone: 600x760, shown at 360 px, the
scene in the top 600x430 and the name block below.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal

from ..content import HERO, Lang
from ..icons import icon
from ..palette import PALETTE as P
from ..svg import MOTION_CSS, document, embed_fonts, esc, lantern, night_bg, petal_def, petals, rope, torii

Layout = Literal["desktop", "phone"]

ART_DIR = Path(__file__).resolve().parents[2] / "build" / "art"
SIZE: dict[str, tuple[int, int]] = {"desktop": (1200, 500), "phone": (600, 760)}
SCENE_H = {"desktop": 500, "phone": 430}
RX = 16
MONO_ADVANCE = 0.6  # JetBrains Mono: every glyph is 600/1000 em wide

SERIF = 'font-family="Shrine Serif"'
MONO = 'font-family="Shrine Mono"'
INK = "#fff6ea"  # name fill top; warm white
STONE_DARK = "#0d0b22"
GROUND = "#0a0818"


def scene_gif(layout: Layout) -> bytes | None:
    """The committed scene GIF for a layout, or None when the art is absent."""
    path = ART_DIR / f"hero-scene-{layout}.gif"
    return path.read_bytes() if path.exists() else None


# ---------------------------------------------------------------- defs


def _defs(w: int, h: int, scene_h: int, layout: Layout) -> str:
    scrim = (
        # left-side scrim over the art for text legibility (desktop)
        f'<linearGradient id="scrim" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="620" y2="0">'
        f'<stop offset="0" stop-color="{P["night-0"]}" stop-opacity="0.75"/>'
        f'<stop offset="0.55" stop-color="{P["night-0"]}" stop-opacity="0.38"/>'
        f'<stop offset="1" stop-color="{P["night-0"]}" stop-opacity="0"/></linearGradient>'
    )
    fade = (
        # phone: the scene's bottom edge melts into the name block
        f'<linearGradient id="fade" gradientUnits="userSpaceOnUse" x1="0" y1="{scene_h - 90}" x2="0" y2="{scene_h}">'
        f'<stop offset="0" stop-color="{P["night-1"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{P["night-1"]}" stop-opacity="1"/></linearGradient>'
    )
    return (
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="{RX}"/></clipPath>'
        + petal_def()
        + (scrim if layout == "desktop" else fade)
        + f'<linearGradient id="nameInk" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{INK}"/><stop offset="0.6" stop-color="{P["moon-b"]}"/>'
        f'<stop offset="1" stop-color="{P["lantern-gold"]}"/></linearGradient>'
        f'<linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{P["vermilion"]}"/>'
        f'<stop offset="1" stop-color="{P["vermilion"]}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="ruleC" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{P["vermilion"]}" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="{P["vermilion"]}"/>'
        f'<stop offset="1" stop-color="{P["vermilion"]}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0.45"/>'
        f'<stop offset="0.5" stop-color="{P["vermilion"]}" stop-opacity="0.18"/>'
        f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0.35"/></linearGradient>'
        '<filter id="lift" x="-10%" y="-40%" width="120%" height="180%">'
        f'<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="{P["night-0"]}" flood-opacity="0.9"/></filter>'
        '<filter id="dof" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="0.9"/></filter>'
    )


# ---------------------------------------------------------------- scenes


def _image(gif: bytes, w: int, h: int) -> str:
    b64 = base64.b64encode(gif).decode("ascii")
    return (
        f'<image href="data:image/gif;base64,{b64}" x="0" y="0" width="{w}" height="{h}" '
        f'preserveAspectRatio="xMidYMid slice" clip-path="url(#card)"/>'
    )


def _circuits(paths: list[tuple[str, float]], nodes: list[tuple[float, float, float]]) -> str:
    c = P["circuit-cyan"]
    lines = "".join(
        f'<path d="{d}" stroke="{c}" stroke-opacity="0.25"/>'
        f'<path class="flow" d="{d}" stroke="{c}"'
        + (f' style="animation-delay:{delay:g}s"' if delay else "")
        + "/>"
        for d, delay in paths
    )
    dots = "".join(
        f'<circle cx="{x:g}" cy="{y:g}" r="4" class="node"'
        + (f' style="animation-delay:{delay:g}s"' if delay else "")
        + "/>"
        for x, y, delay in nodes
    )
    return (
        f'<g fill="none" stroke-width="2" stroke-linecap="round">{lines}</g>'
        f'<g fill="{c}">{dots}</g>'
    )


def _stars(spec: list[tuple[float, float, float, float | None]]) -> str:
    out = []
    for x, y, r, delay in spec:
        cls = ""
        if delay is not None:
            cls = ' class="node"' + (f' style="animation-delay:{delay:g}s"' if delay else "")
        out.append(f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}"{cls}/>')
    return '<g fill="#fff">' + "".join(out) + "</g>"


def _moon(cx: float, cy: float, r: float) -> str:
    return (
        f'<circle cx="{cx:g}" cy="{cy:g}" r="{r * 2.6:g}" fill="url(#moonGlow)"/>'
        f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{P["moon-a"]}" opacity="0.92"/>'
    )


def _shrine(x: float, y: float, s: float) -> str:
    """Torii (breathing glow) with a shimenawa hung under the nuki."""
    return (
        torii(x, y, s)
        + f'<g transform="translate({x - 78 * s:g},{y + 74 * s:g}) scale({s:g})">{rope(156)}</g>'
    )


# Petal spec from the approved mockup: (x, scale, duration s, delay s); negative
# delays put them mid-air on load.
MOCKUP_PETALS = [
    (80, 1.2, 11, -2), (210, 0.9, 14, -9), (330, 1.4, 10, -5), (460, 1, 13, -1),
    (580, 1.3, 12, -7), (690, 0.8, 15, -3), (800, 1.1, 11, -8), (920, 1.5, 9, -4),
    (1030, 1, 13, -10), (1140, 1.2, 12, -6), (1240, 0.9, 14, -12), (1320, 1.3, 10, -2.5),
    (980, 0.7, 16, -11), (400, 0.7, 16, -13),
]


def _fallback_desktop() -> str:
    """The mockup scene, re-set on a 1200x500 canvas (everything 100 units lower)."""
    return (
        _stars([
            (120, 40, 1.2, 0), (260, 90, 1, None), (410, 30, 1.4, -1), (560, 70, 1, None),
            (700, 24, 1.3, -0.5), (1110, 60, 1.1, None), (1040, 22, 1, None), (640, 130, 0.9, None),
            (330, 150, 0.9, 0), (180, 210, 1, None), (520, 240, 1.1, -1.6), (760, 180, 0.9, None),
            (90, 300, 1, None), (470, 330, 0.9, None), (860, 60, 1.2, -2),
        ])
        + _moon(1020, 150, 46)
        + f'<path d="M560,430 L680,340 L750,385 L860,300 L960,375 L1040,335 L1200,415 L1200,500 L560,500 Z" fill="{STONE_DARK}" opacity="0.9"/>'
        + f'<rect x="0" y="460" width="1200" height="40" fill="{GROUND}"/>'
        + _circuits(
            [
                ("M824,470 L760,470 L740,450 L620,450", 0),
                ("M976,470 L1060,470 L1080,445 L1180,445", -0.7),
                ("M900,228 L900,196 L960,196", -1.1),
            ],
            [(620, 450, 0), (1180, 445, -1.2), (960, 196, -0.6)],
        )
        + _shrine(900, 228, 1.0)
        + lantern(720, 400)
        + lantern(1100, 400, -1.4)
        + petals(MOCKUP_PETALS)
    )


def _fallback_phone() -> str:
    """Torii, moon and lanterns in the top 600x430."""
    s = 0.9
    tx, ty = 300, 150
    base_l, base_r, base_y = tx - 88 * s, tx + 88 * s, ty + 238 * s
    return (
        _stars([
            (60, 40, 1.2, 0), (150, 110, 1, None), (230, 30, 1.3, -1), (90, 200, 0.9, None),
            (540, 220, 1, None), (560, 40, 1.1, -0.5), (200, 250, 0.9, None), (330, 60, 1, None),
        ])
        + _moon(440, 100, 42)
        + f'<path d="M0,330 L90,280 L160,310 L260,250 L360,300 L440,265 L600,320 L600,430 L0,430 Z" fill="{STONE_DARK}" opacity="0.9"/>'
        + f'<rect x="0" y="392" width="600" height="38" fill="{GROUND}"/>'
        + _circuits(
            [
                (f"M{base_l:g},404 L170,404 L150,386 L40,386", 0),
                (f"M{base_r:g},404 L430,404 L450,386 L560,386", -0.7),
                (f"M{tx},{ty} L{tx},{ty - 34} L{tx + 56},{ty - 34}", -1.1),
            ],
            [(40, 386, 0), (560, 386, -1.2), (tx + 56, ty - 34, -0.6)],
        )
        + _shrine(tx, ty, s)
        + lantern(110, 336)
        + lantern(490, 336, -1.4)
        + petals([(x * 0.5, sc, d, dl) for x, sc, d, dl in MOCKUP_PETALS])
    )


def _near_petals(spec: list[tuple[float, float, float, float]]) -> str:
    """Large, slightly soft petals in front of the art, for depth."""
    out = []
    for x, scale, dur, delay in spec:
        out.append(
            f'<g transform="translate({x:g},0) scale({scale:g})" opacity="0.9" filter="url(#dof)">'
            f'<use href="#pt" xlink:href="#pt" class="pf" '
            f'style="animation-duration:{dur:g}s;animation-delay:{delay:g}s"/></g>'
        )
    return "<g>" + "".join(out) + "</g>"


# ---------------------------------------------------------------- text


def _terminal(lang: Lang, x: float, y: float, size: float) -> str:
    """Torii glyph + `kami@jinja:~$ summon --engineer` + a blinking block cursor."""
    prompt, cmd = HERO["terminal"](lang).split("$ ", 1)
    prompt += "$ "
    ico = size * 1.2
    tx = x + ico + size * 0.45
    width = MONO_ADVANCE * size * (len(prompt) + len(cmd))
    return (
        f'<g class="rise">'
        + icon("torii", x, y - ico * 0.86, ico, P["vermilion"])
        + f'<text x="{tx:g}" y="{y:g}" {MONO} font-size="{size:g}" fill="{P["circuit-cyan"]}">'
        f'{esc(prompt)}<tspan fill="#e6e6f0">{esc(cmd)}</tspan></text>'
        f'<rect class="cursor" x="{tx + width + size * 0.25:g}" y="{y - size * 0.82:g}" '
        f'width="{size * 0.55:g}" height="{size * 1.02:g}" fill="{P["circuit-cyan"]}"/>'
        f"</g>"
    )


def _tagline(lang: Lang) -> tuple[str, str]:
    """(text, extra attributes): EN is quoted italic; JP is upright (no italics in Japanese type)."""
    t = HERO["tagline"](lang)
    if lang == "en":
        return f"“{t}”", ' font-style="italic"'
    return t, ' letter-spacing="3"'


def _text_desktop(lang: Lang) -> str:
    x = 66
    tag, tag_attr = _tagline(lang)
    return (
        '<g filter="url(#lift)">'
        + _terminal(lang, x, 116, 20)
        + f'<text x="{x - 3}" y="214" class="rise d1" {SERIF} font-size="82" font-weight="700" '
        f'fill="url(#nameInk)" letter-spacing="1">{esc(HERO["name"](lang))}</text>'
        f'<text x="{x}" y="268" class="rise d2" {SERIF} font-size="32" font-weight="700" '
        f'fill="{P["vermilion"]}" letter-spacing="10">{esc(HERO["kana"](lang))}</text>'
        f'<rect x="{x}" y="296" width="260" height="2" fill="url(#rule)" class="rise d2"/>'
        f'<text x="{x}" y="342" class="rise d3" {SERIF} font-size="24" fill="{P["text-soft-a"]}" '
        f'letter-spacing="1.5">{esc(HERO["role"](lang))}</text>'
        f'<text x="{x}" y="388" class="rise d4" {SERIF} font-size="21" fill="{P["text-soft-a"]}" '
        f'opacity="0.82"{tag_attr}>{esc(tag)}</text>'
        "</g>"
    )


def _text_phone(lang: Lang, top: int) -> str:
    cx = 300
    tag, tag_attr = _tagline(lang)
    size = 20
    role_size = 22 if lang == "en" else 24  # the EN role is longer; 22 keeps it within x 30-570
    term_w = size * 1.2 + size * 0.45 + MONO_ADVANCE * size * len(HERO["terminal"](lang)) + size * 0.8
    return (
        '<g filter="url(#lift)">'
        + _terminal(lang, cx - term_w / 2, top + 40, size)
        + f'<g text-anchor="middle">'
        f'<text x="{cx}" y="{top + 122}" class="rise d1" {SERIF} font-size="70" font-weight="700" '
        f'fill="url(#nameInk)">{esc(HERO["name"](lang))}</text>'
        f'<text x="{cx + 5}" y="{top + 174}" class="rise d2" {SERIF} font-size="32" font-weight="700" '
        f'fill="{P["vermilion"]}" letter-spacing="10">{esc(HERO["kana"](lang))}</text>'
        f'<rect x="{cx - 130}" y="{top + 197}" width="260" height="2" fill="url(#ruleC)" class="rise d2"/>'
        f'<text x="{cx}" y="{top + 240}" class="rise d3" {SERIF} font-size="{role_size}" fill="{P["text-soft-a"]}" '
        f'letter-spacing="1.5">{esc(HERO["role"](lang))}</text>'
        f'<text x="{cx}" y="{top + 282}" class="rise d4" {SERIF} font-size="21" fill="{P["text-soft-a"]}" '
        f'opacity="0.82"{tag_attr}>{esc(tag)}</text>'
        "</g></g>"
    )


# ---------------------------------------------------------------- card


def _frame(w: int, h: int) -> str:
    return (
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{RX - 0.75}" '
        f'fill="none" stroke="url(#frame)" stroke-width="1.5"/>'
    )


def render_hero(lang: Lang, layout: Layout, fonts, scene_gif: bytes | None = None) -> str:
    w, h = SIZE[layout]
    sh = SCENE_H[layout]
    if layout == "desktop":
        if scene_gif is not None:
            scene = (
                _image(scene_gif, w, sh)
                + f'<rect width="{w}" height="{h}" fill="url(#scrim)"/>'
                + _near_petals([(150, 2.2, 14, -3), (420, 1.7, 12, -8), (560, 2.6, 16, -12), (300, 1.5, 11, -5.5)])
            )
        else:
            scene = night_bg(w, h, RX) + _fallback_desktop() + f'<rect width="{w}" height="{h}" fill="url(#scrim)"/>'
        body = f'<g clip-path="url(#card)">{scene}{_text_desktop(lang)}</g>{_frame(w, h)}'
    else:
        top_scene = _image(scene_gif, w, sh) if scene_gif is not None else _fallback_phone()
        body = (
            f'<g clip-path="url(#card)">{night_bg(w, h, RX)}{top_scene}'
            f'<rect y="{sh - 90}" width="{w}" height="90" fill="url(#fade)"/>'
            f"{_text_phone(lang, sh)}</g>{_frame(w, h)}"
        )
    title = f'{HERO["name"](lang)} {HERO["kana"](lang)} · {HERO["role"](lang)}'
    svg = document(w, h, body, title=title, css=MOTION_CSS, defs=_defs(w, h, sh, layout))
    return embed_fonts(svg, fonts)
