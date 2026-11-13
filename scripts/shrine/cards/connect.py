"""Connect (ご縁): the shrine bell card.

A large honzuzu bell (本坪鈴) hangs from the shimenawa with its red-and-white bell
rope (鈴緒) and tasselled end. The whole bell swings on the shared 5 s sway; every
RING_S seconds it gives a small ring: the bell jiggles, two sound rings spread from
it, a sheen crosses the bronze and a glint flashes on its shoulder. Beside it (below
it on phones): the CONNECT heading, the bell line and a decorative row of the seven
link glyphs strung on a red thread of fate (赤い糸, the ご縁 itself). The sign-off is
the README footer, not part of this card.

The card has no click targets: the seven links are separate button images in the
README. Desktop: viewBox 1200x360 shown at 846 px; phone: 600x560 shown at 360 px.

Stdlib only.
"""
from __future__ import annotations

from typing import Literal

from ..content import CONNECT, LINKS, SECTION, Lang
from ..icons import LINK_BRAND, icon, on_dark
from ..metrics import text_width, wrap
from ..palette import PALETTE as P
from ..svg import MOTION_CSS, document, embed_fonts, esc, heading_defs, lantern, night_bg, petal_def, petals, rope, rope_y, section_heading

Layout = Literal["desktop", "phone"]

RX = 16
SERIF = 'font-family="Shrine Serif"'
SIZE = {"desktop": (1200, 360), "phone": (600, 560)}
ROPE_TOP = {"desktop": 62, "phone": 66}
HEAD_Y = {"desktop": 42, "phone": 46}

# bell centre, radius, bell-rope length (from the bell's lip to the tassel cap)
BELL = {"desktop": (250, 150, 54, 108), "phone": (300, 152, 50, 84)}

# copy: (centre x, heading y, heading size, bell-line y, bell-line size, row y);
# the block sits centred in the space under the rope (desktop) / under the bell (phone)
COPY = {
    "desktop": dict(cx=770, head_y=174, head=46, line_y=222, line=22, row_y=280),
    "phone": dict(cx=300, head_y=392, head=40, line_y=436, line=22, row_y=492),
}
LINE_W = {"desktop": 640, "phone": 548}
ROUNDEL_R = 21
ROW_STEP = {"desktop": 74, "phone": 76}

RING_S = 7  # one ring of the bell every 7 s

CSS = f"""
.ring{{animation:ring {RING_S}s ease-in-out infinite}}
@keyframes ring{{0%,68%,100%{{transform:rotate(0deg)}}72%{{transform:rotate(4deg)}}76%{{transform:rotate(-3.4deg)}}80%{{transform:rotate(2.4deg)}}84%{{transform:rotate(-1.4deg)}}88%{{transform:rotate(.6deg)}}92%{{transform:rotate(0deg)}}}}
.wave{{transform-box:fill-box;transform-origin:center;opacity:0;animation:wave {RING_S}s ease-out infinite}}
@keyframes wave{{0%,70%{{transform:scale(.9);opacity:0}}73%{{opacity:.75}}100%{{transform:scale(2.3);opacity:0}}}}
.bsheen{{animation:bsheen {RING_S}s ease-in-out infinite}}
@keyframes bsheen{{0%,66%{{transform:translateX(-120px)}}84%,100%{{transform:translateX(120px)}}}}
.glint{{transform-box:fill-box;transform-origin:center;animation:glint {RING_S}s ease-in-out infinite}}
@keyframes glint{{0%,70%,100%{{transform:scale(0) rotate(0deg);opacity:0}}78%{{transform:scale(1) rotate(45deg);opacity:1}}88%{{transform:scale(0) rotate(90deg);opacity:0}}}}
.thread{{stroke-dasharray:3 9;animation:tdash 2.4s linear infinite}}
@keyframes tdash{{to{{stroke-dashoffset:-24}}}}
.halo{{animation:breathe 5s ease-in-out infinite}}
"""


def _g(v: float) -> str:
    return f"{round(v, 2):g}"


def glyph_color(lid: str) -> str:
    if lid in LINK_BRAND:
        return on_dark(LINK_BRAND[lid][1])
    return P["lantern-gold"]


# ---------------------------------------------------------------- defs


def _defs(w: int, h: int) -> str:
    return (
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="{RX}"/></clipPath>'
        + petal_def()
        + heading_defs()
        + f'<radialGradient id="bronze" cx="0.36" cy="0.3" r="0.78"><stop offset="0" stop-color="{P["moon-a"]}"/>'
        f'<stop offset="0.28" stop-color="{P["lantern-gold"]}"/><stop offset="0.66" stop-color="#d0923a"/>'
        f'<stop offset="1" stop-color="#7a4a18"/></radialGradient>'
        f'<linearGradient id="goldV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["moon-a"]}"/>'
        f'<stop offset="0.45" stop-color="{P["lantern-gold"]}"/><stop offset="1" stop-color="#9a6424"/></linearGradient>'
        f'<radialGradient id="bellHalo" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{P["lantern-glow-a"]}" stop-opacity="0.42"/>'
        f'<stop offset="0.55" stop-color="{P["lantern-glow-b"]}" stop-opacity="0.12"/><stop offset="1" stop-color="{P["lantern-glow-b"]}" stop-opacity="0"/></radialGradient>'
        # 鈴緒: red-and-white twisted rope, shaded round
        f'<pattern id="twist" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(-32)">'
        f'<rect width="18" height="18" fill="{P["vermilion"]}"/><rect y="6" width="18" height="5" fill="#fff4ec"/>'
        f'<rect y="14" width="18" height="1.6" fill="#a3291a"/></pattern>'
        f'<linearGradient id="round" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity="0.5"/>'
        f'<stop offset="0.38" stop-color="#fff" stop-opacity="0.14"/><stop offset="0.6" stop-color="#000" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#000" stop-opacity="0.55"/></linearGradient>'
        f'<linearGradient id="sheenB" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="#fff" stop-opacity="0.55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<radialGradient id="lacquer" cx="0.5" cy="0.38" r="0.65"><stop offset="0" stop-color="#2a1d46"/>'
        f'<stop offset="1" stop-color="{P["night-0"]}"/></radialGradient>'
        f'<linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["night-2"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{P["night-2"]}" stop-opacity="0.85"/></linearGradient>'
        f'<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0.45"/>'
        f'<stop offset="0.5" stop-color="{P["vermilion"]}" stop-opacity="0.18"/>'
        f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0.35"/></linearGradient>'
        f'<linearGradient id="bigInk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["moon-a"]}"/>'
        f'<stop offset="0.6" stop-color="{P["lantern-gold"]}"/><stop offset="1" stop-color="{P["lantern-glow-a"]}"/></linearGradient>'
        '<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<filter id="hang" x="-30%" y="-10%" width="160%" height="130%">'
        '<feDropShadow dx="0" dy="8" stdDeviation="7" flood-color="#000" flood-opacity="0.55"/></filter>'
        '<filter id="lift" x="-10%" y="-40%" width="120%" height="180%">'
        f'<feDropShadow dx="0" dy="1.5" stdDeviation="1.5" flood-color="{P["night-0"]}" flood-opacity="0.9"/></filter>'
    )


# ---------------------------------------------------------------- the bell


def _bell(layout: Layout, w: int) -> tuple[str, str]:
    """(swinging bell group, sound rings behind it)."""
    bx, by, r, rope_len = BELL[layout]
    top = ROPE_TOP[layout] + rope_y(w, bx)
    hang_y = by - r - 12  # top of the hanger ring
    lip = by + r - 4
    rope_w = 15
    rope_end = lip + rope_len
    gold_dark = "#8a5a1e"
    v = P["vermilion"]
    hanger = (
        f'<path d="M{_g(bx)},{_g(top)} V{_g(hang_y)}" stroke="{P["sumi-a"]}" stroke-width="4" stroke-linecap="round"/>'
        f'<path d="M{_g(bx)},{_g(top)} V{_g(hang_y)}" stroke="{P["lantern-gold"]}" stroke-opacity="0.35" stroke-width="1"/>'
        f'<circle cx="{_g(bx)}" cy="{_g(hang_y + 4)}" r="6.5" fill="none" stroke="url(#goldV)" stroke-width="3.2"/>'
        f'<path d="M{_g(bx - 11)},{_g(by - r + 5)} q11,-12 22,0 z" fill="url(#goldV)" stroke="{gold_dark}" stroke-width="0.8"/>'
    )
    # 鈴緒 with a gold collar where it leaves the bell and a tassel (房) at the end
    fringe = "".join(
        f'<path d="M{_g(bx - 9 + k * 1.8)},{_g(rope_end + 10)} q{_g((k - 5) * 0.5)},10 {_g((k - 5) * 0.9)},{_g(22 + (k % 3) * 2)}"/>'
        for k in range(11)
    )
    bell_rope = (
        f'<rect x="{_g(bx - rope_w / 2)}" y="{_g(lip - 6)}" width="{rope_w}" height="{_g(rope_len + 8)}" rx="6" fill="url(#twist)"/>'
        f'<rect x="{_g(bx - rope_w / 2)}" y="{_g(lip - 6)}" width="{rope_w}" height="{_g(rope_len + 8)}" rx="6" fill="url(#round)"/>'
        f'<rect x="{_g(bx - 10)}" y="{_g(lip - 2)}" width="20" height="7" rx="2.5" fill="url(#goldV)" stroke="{gold_dark}" stroke-width="0.6"/>'
        f'<rect x="{_g(bx - 11)}" y="{_g(rope_end)}" width="22" height="11" rx="3" fill="url(#goldV)" stroke="{gold_dark}" stroke-width="0.6"/>'
        f'<path d="M{_g(bx - 11)},{_g(rope_end + 5.5)} h22" stroke="{gold_dark}" stroke-width="0.8"/>'
        f'<g stroke="{v}" stroke-width="2" fill="none" stroke-linecap="round">{fringe}</g>'
        f'<g stroke="#ff8a6a" stroke-width="0.8" fill="none" stroke-opacity="0.7">{fringe}</g>'
    )
    slit_w = r * 0.62
    sy = by + r * 0.42
    body = (
        f'<circle cx="{_g(bx)}" cy="{_g(by)}" r="{r}" fill="url(#bronze)" stroke="{gold_dark}" stroke-width="1.2"/>'
        # engraved rings and the equator ridge
        f'<path d="M{_g(bx - r + 2)},{_g(by - 2)} Q{_g(bx)},{_g(by + r * 0.22)} {_g(bx + r - 2)},{_g(by - 2)}" fill="none" stroke="{gold_dark}" stroke-width="3"/>'
        f'<path d="M{_g(bx - r + 3)},{_g(by - 5)} Q{_g(bx)},{_g(by + r * 0.16)} {_g(bx + r - 3)},{_g(by - 5)}" fill="none" stroke="{P["moon-a"]}" stroke-opacity="0.6" stroke-width="1.2"/>'
        f'<path d="M{_g(bx - r * 0.78)},{_g(by - r * 0.42)} Q{_g(bx)},{_g(by - r * 0.26)} {_g(bx + r * 0.78)},{_g(by - r * 0.42)}" fill="none" stroke="{gold_dark}" stroke-opacity="0.55" stroke-width="1.2"/>'
        # the mouth: a slit ending in two round holes
        f'<path d="M{_g(bx - slit_w)},{_g(sy)} H{_g(bx + slit_w)}" stroke="{P["ink-a"]}" stroke-width="4" stroke-linecap="round"/>'
        f'<circle cx="{_g(bx - slit_w)}" cy="{_g(sy)}" r="5" fill="{P["ink-a"]}"/>'
        f'<circle cx="{_g(bx + slit_w)}" cy="{_g(sy)}" r="5" fill="{P["ink-a"]}"/>'
        f'<path d="M{_g(bx - slit_w)},{_g(sy + 5)} H{_g(bx + slit_w)}" stroke="{P["moon-a"]}" stroke-opacity="0.35" stroke-width="1"/>'
        # specular highlight and the sweeping sheen
        f'<ellipse cx="{_g(bx - r * 0.38)}" cy="{_g(by - r * 0.45)}" rx="{_g(r * 0.3)}" ry="{_g(r * 0.17)}" fill="#fff" opacity="0.55" '
        f'transform="rotate(-32 {_g(bx - r * 0.38)} {_g(by - r * 0.45)})"/>'
        f'<clipPath id="bellClip"><circle cx="{_g(bx)}" cy="{_g(by)}" r="{r}"/></clipPath>'
        f'<g clip-path="url(#bellClip)"><g transform="rotate(20 {_g(bx)} {_g(by)})">'
        f'<rect class="bsheen" x="{_g(bx - 18)}" y="{_g(by - r - 20)}" width="36" height="{_g(2 * r + 40)}" fill="url(#sheenB)"/></g></g>'
        f'<path class="glint" d="M{_g(bx - r * 0.52)},{_g(by - r * 0.8)} l2.6,-10 l2.6,10 l10,2.6 l-10,2.6 l-2.6,10 l-2.6,-10 l-10,-2.6 z" fill="#fff"/>'
    )
    pivot_top = f"transform-box:view-box;transform-origin:{_g(bx)}px {_g(top)}px"
    pivot_ring = f"transform-box:view-box;transform-origin:{_g(bx)}px {_g(hang_y + 4)}px"
    swing = (
        f'<g class="sway" style="{pivot_top};animation-delay:-1.2s">'
        f'<g class="ring" style="{pivot_ring}"><g filter="url(#hang)">{hanger}{bell_rope}{body}</g></g></g>'
    )
    waves = (
        f'<circle cx="{_g(bx)}" cy="{_g(by)}" r="{_g(r * 2.3)}" fill="url(#bellHalo)" class="halo"/>'
        + "".join(
            f'<circle cx="{_g(bx)}" cy="{_g(by)}" r="{_g(r + 6)}" fill="none" stroke="{P["lantern-gold"]}" stroke-width="{sw}" '
            f'class="wave" style="animation-delay:{d}s"/>'
            for d, sw in ((0, 2), (0.35, 1.4), (0.7, 0.9))
        )
    )
    return swing, waves


# ---------------------------------------------------------------- copy and the link row


def bell_lines(lang: Lang, layout: Layout) -> list[str]:
    c = COPY[layout]
    return wrap(CONNECT["bell"](lang), c["line"], LINE_W[layout])


def _row(layout: Layout) -> str:
    c = COPY[layout]
    step = ROW_STEP[layout]
    n = len(LINKS)
    x0 = c["cx"] - step * (n - 1) / 2
    y = c["row_y"]
    xs = [x0 + k * step for k in range(n)]
    # the red thread dips between roundels
    d = f"M{_g(xs[0] - 40)},{_g(y - 6)} " + " ".join(
        f"Q{_g((a + b) / 2)},{_g(y + 16)} {_g(b)},{_g(y)}" for a, b in zip([xs[0] - 40] + xs, xs + [xs[-1] + 40])
    )
    v = P["vermilion"]
    thread = (
        f'<path d="{d}" fill="none" stroke="{v}" stroke-width="2" stroke-linecap="round"/>'
        f'<path d="{d}" fill="none" stroke="{P["sakura-a"]}" stroke-width="1.2" stroke-opacity="0.8" class="thread" filter="url(#soft)"/>'
    )
    ro = []
    for k, (lid, _, _) in enumerate(LINKS):
        x = xs[k]
        s = 22
        ro.append(
            f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{ROUNDEL_R + 12}" fill="url(#lanternGlow)" opacity="0.5" class="lglow" '
            f'style="animation-delay:{-0.35 * k:g}s"/>'
            f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{ROUNDEL_R}" fill="url(#lacquer)" stroke="{P["lantern-gold"]}" stroke-width="1.5"/>'
            f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{ROUNDEL_R - 3.5}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.3" stroke-width="0.7"/>'
            + icon(lid, x - s / 2, y - s / 2, s, glyph_color(lid))
        )
    return thread + "".join(ro)


def _copy(lang: Lang, layout: Layout) -> str:
    c = COPY[layout]
    cx = c["cx"]
    head = CONNECT["heading"](lang)
    ls = 4 if lang == "jp" else 1.5
    lines = bell_lines(lang, layout)
    lh = c["line"] * 1.45
    line_svg = "".join(
        f'<text x="{_g(cx)}" y="{_g(c["line_y"] + k * lh)}" text-anchor="middle" {SERIF} font-size="{c["line"]}" '
        f'fill="{P["text-soft-a"]}">{esc(t)}</text>'
        for k, t in enumerate(lines)
    )
    hw = text_width(head, c["head"], weight=700, letter_spacing=ls)
    orn_y = c["head_y"] - c["head"] * 0.33
    orn = "".join(
        f'<path d="M{_g(x)},{_g(orn_y)} l{_g(5 * s)},-5 l{_g(5 * s)},5 l{_g(-5 * s)},5 z" fill="{P["vermilion"]}"/>'
        f'<rect x="{_g(x + (10 if s > 0 else -70))}" y="{_g(orn_y - 0.6)}" width="60" height="1.2" fill="url(#{"ruleR" if s > 0 else "ruleL"})"/>'
        for x, s in ((cx + hw / 2 + 14, 1), (cx - hw / 2 - 14, -1))
    )
    return (
        '<g filter="url(#lift)">'
        f'<g class="rise"><text x="{_g(cx + ls / 2)}" y="{c["head_y"]}" text-anchor="middle" {SERIF} font-size="{c["head"]}" '
        f'font-weight="700" fill="url(#bigInk)" letter-spacing="{ls}">{esc(head)}</text>{orn}</g>'
        f'<g class="rise d1">{line_svg}</g>'
        "</g>"
        + f'<g class="rise d1">{_row(layout)}</g>'
    )


# ---------------------------------------------------------------- card


def _stars(w: int, h: int, n: int) -> str:
    out = []
    x, y = 120, 40
    for i in range(n):
        x = (x + 263 + i * 71) % w
        y = (y + 157 + i * 29) % (h * 0.92)
        r = 0.8 + (i % 3) * 0.25
        cls = (' class="node"' + (f' style="animation-delay:-{i % 5 * 0.5:g}s"' if i % 5 else "")) if i % 3 == 0 else ' opacity="0.55"'
        out.append(f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{r:g}"{cls}/>')
    return '<g fill="#fff">' + "".join(out) + "</g>"


def render_connect(lang: Lang, layout: Layout, fonts) -> str:
    w, h = SIZE[layout]
    swing, waves = _bell(layout, w)
    desk = layout == "desktop"
    head = section_heading(SECTION["connect"](lang), w / 2, HEAD_Y[layout], 30 if desk else 34, 20 if desk else 22)
    pet = (
        [(120, 1, 11, -2), (420, 0.8, 14, -8), (640, 1.1, 12, -5), (900, 0.9, 13, -1), (1120, 1.2, 15, -10), (1280, 0.8, 12, -6)]
        if desk
        else [(80, 1, 12, -3), (260, 0.8, 15, -9), (430, 1.1, 13, -5), (620, 0.9, 14, -1)]
    )
    if not desk:
        pet = [(x, s, d * h / 440, dl * h / 440) for x, s, d, dl in pet]
    scene = (
        night_bg(w, h, RX)
        + _stars(w, h, 24 if desk else 22)
        + f'<rect y="{_g(h * 0.5)}" width="{w}" height="{_g(h * 0.5)}" fill="url(#mist)"/>'
        + head
        + waves
        + (lantern(84, 290) + lantern(1116, 290, 1.4) if desk else "")
        + f'<g transform="translate(0,{ROPE_TOP[layout]})">{rope(w, (0.08, 0.36, 0.64, 0.92) if desk else (0.14, 0.86))}</g>'
        + petals(pet)
        + swing
        + _copy(lang, layout)
    )
    body = (
        f'<g clip-path="url(#card)">{scene}</g>'
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{RX - 0.75}" fill="none" stroke="url(#frame)" stroke-width="1.5"/>'
    )
    title = f'{SECTION["connect"](lang)} · {CONNECT["heading"](lang)} · {CONNECT["bell"](lang)}'
    svg = document(w, h, body, title=title, css=MOTION_CSS + CSS, defs=_defs(w, h))
    return embed_fonts(svg, fonts)

