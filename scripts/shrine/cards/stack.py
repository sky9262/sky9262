"""Tech stack (道具): a shrine-festival wall of paper lanterns.

Every tool is a hanging lantern (提灯) on a festival string: dark at first, then
lit one after another (`animation: lightup .6s ease-out {0.15*k}s both`, where
k = group index + the tool's index in its group, so the light runs diagonally
from the top-left and every lantern is lit within about 2.2 s). `both` keeps the
final, lit state, so an <img> that loads late still shows every lantern lit.
Brand tools carry their logo in a lacquered roundel; TEXT_ONLY tools are
name-only lanterns. Each group is introduced by a small wooden signboard (立て札)
in the card's language; tool names stay as they are.

Desktop: viewBox 1200xH shown at 846 px; signboards on the left, lantern strings
to the right. Phone: 600xH shown at 360 px; each signboard heads its group and
the lanterns wrap into centred strings below it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..content import SECTION, STACK, Lang
from ..icons import BRAND, icon
from ..metrics import text_width, wrap
from ..palette import PALETTE as P
from ..svg import MOTION_CSS, document, embed_fonts, esc, heading_defs, night_bg, petal_def, petals, section_heading

Layout = Literal["desktop", "phone"]

RX = 16
SERIF = 'font-family="Shrine Serif"'
W = {"desktop": 1200, "phone": 600}
MARGIN = {"desktop": 30, "phone": 20}

NAME_SIZE = {"desktop": 18, "phone": 20}  # >= 12 px rendered
LABEL_SIZE = {"desktop": 19, "phone": 22}
BODY_H = {"desktop": 44, "phone": 48}  # lantern paper, one line of text
NAME_LH = {"desktop": 22, "phone": 25}  # extra height per wrapped name line
CAP_H = 5
HANG = 9  # string to top cap
ROUNDEL_R = {"desktop": 15, "phone": 16}
GAP_X = {"desktop": 14, "phone": 10}
GAP_Y = {"desktop": 20, "phone": 18}  # room for the tassels  # between lantern strings
GROUP_GAP = {"desktop": 22, "phone": 36}
TOP = {"desktop": 96, "phone": 98}  # first group's top
HEAD_Y = {"desktop": 52, "phone": 56}
SIGN_H = {"desktop": 44, "phone": 48}
SIGN_PAD = 16

LIGHTUP_STEP = 0.15
LIGHTUP_CSS = (
    "@keyframes lightup{from{opacity:0}to{opacity:1}}"
    ".hl{animation:lightup .6s ease-out both}"
    ".rib{stroke:#7a3a10;stroke-opacity:.13;stroke-width:1}"
)


def _g(v: float) -> str:
    return f"{round(v, 2):g}"


@dataclass(frozen=True)
class Tile:
    name: str
    x: float
    y: float  # top of the hanger (the festival string)
    w: float
    h: float  # hanger + caps + paper
    k: int  # lightup order: group index + index in group
    logo: bool
    lines: tuple[str, ...]


@dataclass(frozen=True)
class Sign:
    label: str
    x: float
    y: float
    w: float
    post: float  # post length below the board (desktop)


# ---------------------------------------------------------------- planning


def _sign_w(lang: Lang, layout: Layout) -> float:
    size = LABEL_SIZE[layout]
    widest = max(text_width(label(lang), size, weight=700, letter_spacing=1) for label, _ in STACK)
    return round(max(150.0, widest + 2 * SIGN_PAD), 1)


def _pads(logo: bool, layout: Layout) -> tuple[float, float]:
    """(space before the name, space after it) inside the paper."""
    if logo:
        return 10 + 2 * ROUNDEL_R[layout] + 9, 16
    return 18, 18


def _lantern_size(name: str, layout: Layout, max_w: float) -> tuple[float, float, tuple[str, ...]]:
    """(width, total height, name lines) of one lantern."""
    size = NAME_SIZE[layout]
    lead, tail = _pads(name in BRAND, layout)
    lines = (name,)
    if lead + text_width(name, size) + tail > max_w:
        lines = tuple(wrap(name, size, max_w - lead - tail))
    tw = max(text_width(l, size) for l in lines)
    h = HANG + CAP_H + BODY_H[layout] + NAME_LH[layout] * (len(lines) - 1) + CAP_H
    return round(lead + tw + tail, 1), h, lines


def _balance(widths: list[float], area: float, gap: float) -> list[list[int]]:
    """Split lantern indices into the fewest strings that fit, as evenly as possible."""
    n = len(widths)

    def span(i: int, j: int) -> float:
        return sum(widths[i:j]) + gap * (j - i - 1)

    # fewest lines (greedy), then minimise the widest line over partitions with that count
    lines, cur = 1, 0.0
    for w in widths:
        need = w if cur == 0 else cur + gap + w
        if need > area and cur > 0:
            lines, cur = lines + 1, w
        else:
            cur = need
    best: dict[tuple[int, int], tuple[float, list[int]]] = {}

    def solve(i: int, left: int) -> tuple[float, list[int]]:
        if (i, left) in best:
            return best[(i, left)]
        if left == 1:
            res = (span(i, n), [n]) if span(i, n) <= area or n - i == 1 else (float("inf"), [n])
        else:
            res = (float("inf"), [n])
            for j in range(i + 1, n - left + 2):
                s = span(i, j)
                if s > area and j > i + 1:
                    break
                sub, cuts = solve(j, left - 1)
                cand = max(s, sub)
                if cand < res[0]:
                    res = (cand, [j] + cuts)
        best[(i, left)] = res
        return res

    _, cuts = solve(0, lines)
    out, start = [], 0
    for c in cuts:
        out.append(list(range(start, c)))
        start = c
    return out


def plan(lang: Lang, layout: Layout) -> tuple[int, list[Tile]]:
    """(card height, lanterns in STACK order)."""
    h, tiles, _ = _plan(lang, layout)
    return h, tiles


def _area(lang: Lang, layout: Layout) -> tuple[float, float]:
    """(left edge, width) of the space the lantern strings span."""
    w, m = W[layout], MARGIN[layout]
    if layout == "desktop":
        x0 = m + _sign_w(lang, layout) + 26
        return x0, w - m - x0
    return m, w - 2 * m


def _plan(lang: Lang, layout: Layout) -> tuple[int, list[Tile], list[Sign]]:
    w, m = W[layout], MARGIN[layout]
    sw = _sign_w(lang, layout)
    x0, area = _area(lang, layout)
    gx, gy = GAP_X[layout], GAP_Y[layout]
    tiles: list[Tile] = []
    signs: list[Sign] = []
    y = TOP[layout]
    for gi, (label, tools) in enumerate(STACK):
        sizes = [_lantern_size(t, layout, area) for t in tools]
        rows = _balance([s[0] for s in sizes], area, gx)
        if layout == "desktop":
            sign_y = y + HANG + 2
            ly = y
        else:
            signs_x = (w - sw) / 2
            sign_y = y
            ly = y + SIGN_H[layout] + 22
        for row in rows:
            row_w = sum(sizes[i][0] for i in row) + gx * (len(row) - 1)
            x = x0 + (area - row_w) / 2
            row_h = max(sizes[i][1] for i in row)
            for i in row:
                tw, th, lines = sizes[i]
                tiles.append(Tile(tools[i], round(x, 1), ly, tw, th, gi + i, tools[i] in BRAND, lines))
                x += tw + gx
            ly += row_h + gy
        block_bottom = ly - gy
        if layout == "desktop":
            post = max(0.0, block_bottom - (sign_y + SIGN_H[layout]) - 6)
            signs.append(Sign(label(lang), m, sign_y, sw, post))
        else:
            signs.append(Sign(label(lang), signs_x, sign_y, sw, 0))
        y = block_bottom + GROUP_GAP[layout] + (14 if layout == "desktop" else 0)
    height = int(round(y - GROUP_GAP[layout] + 30))
    return height, tiles, signs


# ---------------------------------------------------------------- defs


def _defs(w: int, h: int) -> str:
    return (
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="{RX}"/></clipPath>'
        + petal_def()
        + heading_defs()
        + f'<radialGradient id="paper" cx="0.5" cy="0.45" r="0.75"><stop offset="0" stop-color="{P["moon-a"]}"/>'
        f'<stop offset="0.55" stop-color="{P["lantern-gold"]}"/><stop offset="1" stop-color="{P["lantern-glow-a"]}"/></radialGradient>'
        f'<linearGradient id="paperDark" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a2140"/>'
        f'<stop offset="1" stop-color="#1a142c"/></linearGradient>'
        f'<radialGradient id="halo" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{P["lantern-glow-a"]}" stop-opacity="0.42"/>'
        f'<stop offset="0.6" stop-color="{P["lantern-glow-b"]}" stop-opacity="0.1"/>'
        f'<stop offset="1" stop-color="{P["lantern-glow-b"]}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="lacquer" cx="0.5" cy="0.38" r="0.65"><stop offset="0" stop-color="#2a1d46"/>'
        f'<stop offset="1" stop-color="{P["night-0"]}"/></radialGradient>'
        f'<linearGradient id="wood" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["wood-a"]}"/>'
        f'<stop offset="0.55" stop-color="#c3914f"/><stop offset="1" stop-color="{P["wood-b"]}"/></linearGradient>'
        f'<linearGradient id="post" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{P["wood-grain"]}"/>'
        f'<stop offset="0.5" stop-color="{P["wood-b"]}"/><stop offset="1" stop-color="#5e3a18"/></linearGradient>'
        f'<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0.45"/>'
        f'<stop offset="0.5" stop-color="{P["vermilion"]}" stop-opacity="0.18"/>'
        f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0.35"/></linearGradient>'
        f'<linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["night-2"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{P["night-2"]}" stop-opacity="0.85"/></linearGradient>'
        '<filter id="shadow" x="-10%" y="-20%" width="120%" height="150%">'
        '<feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000" flood-opacity="0.55"/></filter>'
    )


# ---------------------------------------------------------------- pieces


def _stars(w: int, h: int, n: int) -> str:
    out = []
    x, y = 41.0, 23.0
    for i in range(n):
        x = (x + 263 + i * 71) % w
        y = (y + 157 + i * 29) % (h * 0.95)
        r = 0.8 + (i % 3) * 0.25
        cls = (
            ' class="node"' + (f' style="animation-delay:-{i % 5 * 0.5:g}s"' if i % 5 else "")
            if i % 3 == 0
            else ' opacity="0.5"'
        )
        out.append(f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{r:g}"{cls}/>')
    return '<g fill="#fff">' + "".join(out) + "</g>"


def _sign(s: Sign, layout: Layout) -> str:
    """立て札: a wooden board under a little dark roof, on a post (desktop)."""
    h = SIGN_H[layout]
    size = LABEL_SIZE[layout]
    x, y, w = s.x, s.y, s.w
    roof = (
        f'<path d="M{_g(x - 7)},{_g(y + 1)} L{_g(x + 10)},{_g(y - 9)} L{_g(x + w - 10)},{_g(y - 9)} L{_g(x + w + 7)},{_g(y + 1)} Z" '
        f'fill="{P["sumi-a"]}"/>'
        f'<rect x="{_g(x - 7)}" y="{_g(y + 1)}" width="{_g(w + 14)}" height="2.5" fill="{P["vermilion"]}"/>'
    )
    post = ""
    if s.post > 0:
        post = f'<rect x="{_g(x + w / 2 - 5)}" y="{_g(y + h)}" width="10" height="{_g(s.post)}" fill="url(#post)"/>'
    grain = "".join(
        f'<path d="M{_g(x + 4)},{_g(y + gy)} C{_g(x + w * 0.35)},{_g(y + gy - 3)} {_g(x + w * 0.65)},{_g(y + gy + 3)} {_g(x + w - 4)},{_g(y + gy - 1)}"/>'
        for gy in (12, 24, 36)
    )
    return (
        f'<g filter="url(#shadow)">{post}'
        f'<rect x="{_g(x)}" y="{_g(y + 3.5)}" width="{_g(w)}" height="{_g(h - 3.5)}" rx="2" fill="url(#wood)" stroke="#6b4420" stroke-width="1.5"/>'
        f"{roof}</g>"
        f'<g stroke="{P["wood-grain"]}" stroke-opacity="0.25" fill="none" stroke-width="1.1">{grain}</g>'
        f'<circle cx="{_g(x + 8)}" cy="{_g(y + h / 2 + 2)}" r="1.8" fill="{P["ink-a"]}" opacity="0.6"/>'
        f'<circle cx="{_g(x + w - 8)}" cy="{_g(y + h / 2 + 2)}" r="1.8" fill="{P["ink-a"]}" opacity="0.6"/>'
        f'<text x="{_g(x + w / 2)}" y="{_g(y + 3.5 + (h - 3.5) / 2 + size * 0.36)}" text-anchor="middle" {SERIF} '
        f'font-size="{size}" font-weight="700" fill="{P["ink-a"]}" letter-spacing="1">{esc(s.label)}</text>'
    )


def _string(x1: float, x2: float, y: float) -> str:
    mid = (x1 + x2) / 2
    return (
        f'<path d="M{_g(x1)},{_g(y)} Q{_g(mid)},{_g(y + 7)} {_g(x2)},{_g(y)}" fill="none" '
        f'stroke="#4a3f5e" stroke-width="1.6"/>'
    )


def _delay(t: Tile) -> float:
    return round(LIGHTUP_STEP * t.k, 2)


def _halo(t: Tile) -> str:
    """The warm glow around a lit lantern; painted under every lantern so it never veils a neighbour."""
    body_h = t.h - HANG - 2 * CAP_H
    cy = t.y + HANG + CAP_H + body_h / 2
    return (
        f'<g class="hl" style="animation-delay:{_delay(t):g}s">'
        f'<ellipse cx="{_g(t.x + t.w / 2)}" cy="{_g(cy)}" rx="{_g(t.w / 2 + 22)}" ry="{_g(body_h * 0.85 + 6)}" '
        f'fill="url(#halo)" class="lglow" style="animation-delay:-{(t.k * 0.37) % 3:.2f}s"/></g>'
    )


def _paper(x: float, y: float, w: float, h: float) -> str:
    """A chochin silhouette: round ends and a gentle bulge top and bottom."""
    r = min(16.0, h / 2)
    b = 3.0
    cx = x + w / 2
    return (
        f"M{_g(x + r)},{_g(y)} Q{_g(cx)},{_g(y - b)} {_g(x + w - r)},{_g(y)} "
        f"C{_g(x + w + r * 0.35)},{_g(y)} {_g(x + w + r * 0.35)},{_g(y + h)} {_g(x + w - r)},{_g(y + h)} "
        f"Q{_g(cx)},{_g(y + h + b)} {_g(x + r)},{_g(y + h)} "
        f"C{_g(x - r * 0.35)},{_g(y + h)} {_g(x - r * 0.35)},{_g(y)} {_g(x + r)},{_g(y)} Z"
    )


def _lantern(t: Tile, layout: Layout) -> str:
    size = NAME_SIZE[layout]
    rr = ROUNDEL_R[layout]
    body_top = t.y + HANG + CAP_H
    body_h = t.h - HANG - 2 * CAP_H
    bx, bw = t.x, t.w
    cx = bx + bw / 2
    paper = _paper(bx, body_top, bw, body_h)
    cap_w = bw - 22
    ribs = "".join(
        f'<path class="rib" d="M{_g(bx + 5)},{_g(body_top + d)} Q{_g(cx)},{_g(body_top + d + (-2 if d < body_h / 2 else 2))} {_g(bx + bw - 5)},{_g(body_top + d)}"/>'
        for d in (6, 11, body_h - 11, body_h - 6)
    )
    lead, _ = _pads(t.logo, layout)
    if t.logo:
        rcx = bx + 10 + rr
        rcy = body_top + body_h / 2
        ico = rr * 1.25
        logo = (
            f'<circle cx="{_g(rcx)}" cy="{_g(rcy)}" r="{rr}" fill="url(#lacquer)" stroke="{P["ink-b"]}" stroke-width="1.5"/>'
            + icon(t.name, rcx - ico / 2, rcy - ico / 2, ico)
        )
        tx, anchor = bx + lead, ""
    else:
        logo = ""
        tx, anchor = cx, ' text-anchor="middle"'
    n = len(t.lines)
    first = body_top + body_h / 2 + size * 0.35 - (n - 1) * NAME_LH[layout] / 2
    name = "".join(
        f'<text x="{_g(tx)}" y="{_g(first + j * NAME_LH[layout])}"{anchor} {SERIF} font-size="{size}" '
        f'fill="{P["ink-a"]}">{esc(line)}</text>'
        for j, line in enumerate(t.lines)
    )
    bottom = body_top + body_h
    caps = (
        f'<rect x="{_g(cx - cap_w / 2)}" y="{_g(t.y + HANG)}" width="{_g(cap_w)}" height="{CAP_H + 1}" rx="2" fill="{P["sumi-a"]}"/>'
        f'<rect x="{_g(cx - cap_w / 2)}" y="{_g(t.y + HANG + CAP_H - 0.6)}" width="{_g(cap_w)}" height="0.8" fill="{P["lantern-gold"]}" opacity="0.5"/>'
        f'<rect x="{_g(cx - cap_w / 2)}" y="{_g(bottom - 1)}" width="{_g(cap_w)}" height="{CAP_H + 1}" rx="2" fill="{P["sumi-a"]}"/>'
        # a short vermilion tassel (房)
        f'<path d="M{_g(cx)},{_g(bottom + CAP_H)} v4 m-2.5,0 h5 l1,9 h-7 z" fill="{P["vermilion"]}" opacity="0.9"/>'
    )
    hanger = (
        f'<path d="M{_g(cx)},{_g(t.y + 2)} V{_g(t.y + HANG)}" stroke="#4a3f5e" stroke-width="1.4"/>'
        f'<circle cx="{_g(cx)}" cy="{_g(t.y + 2.5)}" r="2" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.6" stroke-width="1"/>'
    )
    unlit = f'<path d="{paper}" fill="url(#paperDark)" stroke="{P["lantern-gold"]}" stroke-opacity="0.22"/>'
    lit = (
        f'<g style="animation:lightup .6s ease-out {_delay(t):g}s both">'
        f'<path d="{paper}" fill="url(#paper)"/>'
        f"<g>{ribs}</g>{logo}{name}</g>"
    )
    return f"{hanger}{unlit}{lit}{caps}"


# ---------------------------------------------------------------- card


def _frame(w: int, h: int) -> str:
    return (
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{RX - 0.75}" '
        f'fill="none" stroke="url(#frame)" stroke-width="1.5"/>'
    )


def render_stack(lang: Lang, layout: Layout, fonts) -> str:
    w = W[layout]
    h, tiles, signs = _plan(lang, layout)
    # festival strings: one per row of lanterns
    rows: dict[float, list[Tile]] = {}
    for t in tiles:
        rows.setdefault(t.y, []).append(t)
    x0, area = _area(lang, layout)
    strings = "".join(_string(x0 - 6, x0 + area + 6, y) for y in rows)
    lanterns = "".join(_halo(t) for t in tiles) + "".join(_lantern(t, layout) for t in tiles)
    head = section_heading(
        SECTION["stack"](lang), w / 2, HEAD_Y[layout], 30 if layout == "desktop" else 34, 20 if layout == "desktop" else 22
    )
    pet = (
        [(120, 1.1, 13, -2), (380, 0.8, 16, -9), (610, 1.2, 12, -5), (840, 0.9, 15, -1), (1060, 1.3, 14, -7), (1240, 0.8, 16, -11)]
        if layout == "desktop"
        else [(70, 1.1, 13, -2), (230, 0.8, 16, -9), (400, 1.2, 12, -5), (580, 0.9, 15, -1), (660, 1, 14, -7)]
    )
    pet = [(x, s, d * h / 440, dl * h / 440) for x, s, d, dl in pet]  # fall the full card height
    scene = (
        night_bg(w, h, RX)
        + _stars(w, h, 24 if layout == "desktop" else 30)
        + f'<rect y="{_g(h * 0.6)}" width="{w}" height="{_g(h * 0.4)}" fill="url(#mist)"/>'
        + petals(pet)
        + head
        + "".join(_sign(s, layout) for s in signs)
        + strings
        + lanterns
    )
    body = f'<g clip-path="url(#card)">{scene}</g>{_frame(w, h)}'
    title = SECTION["stack"](lang) + " · " + ", ".join(t for _, tools in STACK for t in tools)
    svg = document(w, h, body, title=title, css=MOTION_CSS + LIGHTUP_CSS, defs=_defs(w, h))
    return embed_fonts(svg, fonts)
