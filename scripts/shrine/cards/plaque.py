"""Open plaques (絵馬): one wooden prayer plaque per project, 420 wide, shown at 360 px.

Owner edit 2 (2026-11-12): the earlier flip plaques were hard to read, so each
plaque now shows everything at once. Top row: kind pill and years. Title block:
the primary title large and the secondary title small, with the project's
animated motif in a round window to the right. Then a divider, the detail lines,
the NDA line (client plaques), and the tags with the hanko stamp beside them.

The board hangs still so the text never moves; the shide on the rope flutter,
the motif animates, a sheen sweeps the wood and the lantern glow breathes. The
sheen, glow, shide and motif are delayed by -1.5 s x index, so a row of plaques
never pulses in sync. Every plaque shares one height (PLAQUE_H) so README pairs
line up.

Stdlib only: the CI generator calls render_plaque() for live star counts.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from functools import lru_cache

from ..content import NDA, Lang, Plaque, active_plaques
from ..icons import icon
from ..metrics import _break_cost, _tokens, text_width, wrap
from ..palette import PALETTE as P
from ..svg import MOTION_CSS, document, embed_fonts, esc, petal_def, petals, rope

W = 420
CX = 210
PL, PR = 10, 410  # board edges
PAD = 34  # text padding from the board edge
LEFT, RIGHT = PL + PAD, PR - PAD  # 44 .. 376
INNER_W = RIGHT - LEFT  # 332
MIN_SIZE = 14  # 12 px at 360 rendered
PEAK, SHOULDER = 50, 88
BOARD_PAD_BOTTOM = 10  # card bottom to board bottom

# detail lines: a small diamond marker, then the text with a hanging indent
BULLET_W = 15
DETAIL_X = LEFT + BULLET_W
DETAIL_W = RIGHT - DETAIL_X
DETAIL_SIZE = {"jp": 15, "en": 16}
DETAIL_LH = {"jp": 23, "en": 25}
ITEM_GAP = 6

TITLE_SIZES = (26, 24, 22)
SUB_SIZE = 15
MOTIF_R = 46  # outer radius of the motif window as drawn on the plaque
WINDOW_R = 54  # radius the motifs are drawn at (scaled to MOTIF_R)
MOTIF_CX = RIGHT - MOTIF_R + 4
TITLE_W = MOTIF_CX - MOTIF_R - 14 - LEFT

TAG_H, TAG_GAP = 24, 6
# vertical rhythm (units)
ROW_GAP = 14  # pill row to title row
DIV_ABOVE, DIV_BELOW = 14, 18  # around the divider
NDA_GAP = 20  # last detail baseline to the NDA rule area
FOOT_GAP = 18  # text to the tags/stamp footer
FOOT_PAD = 18  # footer to the board's bottom edge
STAMP_R = 30

SERIF = 'font-family="Shrine Serif"'
MONO = 'font-family="Shrine Mono"'
MONO_W = 0.6
EDGE = "#6b4420"  # board outline, darker than the grain
STAMP = P["ink-red"]
TEAL = "#0f3a40"

PLAQUE_CSS = """
.sheen{animation:sheen 12s ease-in-out infinite}
@keyframes sheen{0%,6%{transform:translateX(-320px)}30%,100%{transform:translateX(320px)}}
.rope path:nth-child(n+3){transform-box:fill-box;transform-origin:50% 0;animation:flutter 3.2s ease-in-out infinite}
.rope path:nth-child(2n+4){animation-duration:2.7s}
@keyframes flutter{0%,100%{transform:rotate(-7deg)}50%{transform:rotate(7deg)}}
.tassel{transform-box:fill-box;transform-origin:50% 0;animation:flutter 4s ease-in-out infinite}
.spin{animation:spin 14s linear infinite}
.spinr{animation:spin 26s linear infinite reverse}
.spinc{transform-box:fill-box;transform-origin:center;animation:spin 6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.core{transform-box:fill-box;transform-origin:center;animation:core 2.6s ease-in-out infinite}
@keyframes core{0%,100%{transform:scale(.85)}50%{transform:scale(1.15)}}
"""


def _g(v: float) -> str:
    return f"{round(v, 2):g}"


class _Phase:
    """animation-delay styles for one plaque: a motif's own offset minus the plaque's stagger."""

    def __init__(self, index: int) -> None:
        self.off = 1.5 * index

    def __call__(self, base: float = 0.0) -> str:
        return f' style="animation-delay:{_g(base - self.off)}s"'

    @property
    def delay(self) -> str:
        return f"-{self.off:g}s"


# ---------------------------------------------------------------- layout


@dataclass
class _Layout:
    title_size: float
    title: list[str]
    sub: list[str]
    sub_ls: float
    items: list[list[str]]  # detail lines, each wrapped
    nda: list[str]
    tag_rows: list[list[tuple[str, float]]]  # (tag, chip width)
    stamp_half: float
    height: float = 0.0  # natural content height from the top of the title row
    parts: dict = field(default_factory=dict)


def _fits(lines: list[str], size: float, width: float, *, weight: int = 400, ls: float = 0) -> bool:
    return all(text_width(t, size, weight=weight, letter_spacing=ls) <= width for t in lines)


# Japanese title words that must stay whole when a title breaks onto two lines.
TITLE_WORDS = (
    "文字起こし", "自動生成", "対策", "訓練", "会議", "編隊", "音声",
    "エージェント", "ファシリテーター", "フィッシング", "マーケティング", "スカウト", "ドローン",
)


def _split_jp(text: str, size: float) -> list[str] | None:
    """Best two-line break of an unspaced Japanese title, keeping TITLE_WORDS whole."""
    toks = _tokens(text)
    keep = [(m, m + len(w)) for w in TITLE_WORDS for m in range(len(text)) if text.startswith(w, m)]
    best, best_cost, pos = None, float("inf"), 0
    for j in range(1, len(toks)):
        pos += len(toks[j - 1])
        if any(a < pos < b for a, b in keep):
            continue
        a, b = "".join(toks[:j]), "".join(toks[j:])
        wa, wb = text_width(a, size, weight=700), text_width(b, size, weight=700)
        if max(wa, wb) > TITLE_W:
            continue
        cost = _break_cost(toks[j - 1], toks[j], False) + 0.02 * ((wa - wb) / size) ** 2
        if cost < best_cost:
            best, best_cost = [a, b], cost
    return best


def _title_lines(text: str) -> tuple[float, list[str]]:
    """Largest title size whose wrap fits the column in at most two lines."""
    for size in TITLE_SIZES:
        lines = wrap(text, size, TITLE_W, weight=700)
        if len(lines) == 2 and " " not in text:
            lines = _split_jp(text, size) or lines
        if len(lines) <= 2 and _fits(lines, size, TITLE_W, weight=700):
            return size, lines
    size = TITLE_SIZES[-1]
    return size, wrap(text, size, TITLE_W, weight=700)


def detail_lines(p: Plaque, lang: Lang) -> tuple[float, list[list[str]]]:
    """(font size, items): the detail text wrapped to the padded width, never truncated.

    JP lines are standalone statements, so each is an item with a diamond marker.
    EN lines are one or two sentences broken at phrase boundaries by the author, so
    they stay as written in a single unmarked paragraph (wrapped only if too wide).
    """
    lines = p.lines(lang).split("\n")
    if lang == "en":
        size = DETAIL_SIZE["en"]
        return size, [[x for line in lines for x in wrap(line, size, INNER_W)]]
    size = DETAIL_SIZE["jp"]
    return size, [wrap(line, size, DETAIL_W) for line in lines]


def _stamp_half(p: Plaque, stars: int | None, forks: int | None) -> float:
    if p.stamp == "stars" and (stars is not None or forks is not None):
        row1 = f"{stars}" if stars is not None else ""
        row2 = f"{forks} forks" if forks is not None else ""
        return max(MONO_W * 16 * len(row1) + 20, MONO_W * 14 * len(row2), 40) / 2 + 9
    return STAMP_R if p.stamp != "stars" else 27


def _tag_rows(tags: list[str], width: float) -> list[list[tuple[str, float]]]:
    rows: list[list[tuple[str, float]]] = [[]]
    x = 0.0
    for t in tags:
        w = text_width(t, 14, mono=True) + 18
        if rows[-1] and x + w > width:
            rows.append([])
            x = 0.0
        if w > width:
            raise ValueError(f"tag does not fit: {t}")
        rows[-1].append((t, w))
        x += w + TAG_GAP
    return [r for r in rows if r]


def _layout(p: Plaque, lang: Lang, stars: int | None = None, forks: int | None = None) -> _Layout:
    size, title = _title_lines(p.title(lang))
    sub_ls = 1.0 if lang == "en" else 0.5  # the subtitle is JP on EN plaques
    sub = wrap(p.subtitle(lang), SUB_SIZE, TITLE_W, letter_spacing=sub_ls)
    _, items = detail_lines(p, lang)
    nda_w = INNER_W - 19
    nda = wrap(NDA(lang), 14, nda_w) if p.kind == "client" else []
    half = _stamp_half(p, stars, forks)
    rows = _tag_rows(p.tags, (RIGHT - 2 * half - 8) - LEFT)
    lay = _Layout(size, title, sub, sub_ls, items, nda, rows, half)
    # natural heights of each part
    title_h = size * 0.82 + (len(title) - 1) * size * 1.2 + 13 + SUB_SIZE * 0.85 + (len(sub) - 1) * 20
    lay.parts["title_h"] = title_h
    lay.parts["row_h"] = max(title_h, 2 * MOTIF_R + 4)
    n_lines = sum(len(i) for i in items)
    lay.parts["details_h"] = DETAIL_SIZE[lang] * 0.85 + (n_lines - 1) * DETAIL_LH[lang] + (len(items) - 1) * ITEM_GAP
    lay.parts["nda_h"] = (14 + (len(nda) - 1) * 20) if nda else 0
    tags_h = len(rows) * TAG_H + (len(rows) - 1) * TAG_GAP
    lay.parts["foot_h"] = max(tags_h, 2 * STAMP_R + 4)
    lay.parts["tags_h"] = tags_h
    # pill row 98..124, then: gap, title row, gap, divider, gap, details, (gap, NDA), gap, footer, pad
    lay.height = (
        124 + ROW_GAP + lay.parts["row_h"] + DIV_ABOVE + DIV_BELOW + lay.parts["details_h"]
        + ((NDA_GAP + lay.parts["nda_h"]) if nda else 0) + FOOT_GAP + lay.parts["foot_h"] + FOOT_PAD
    )
    return lay


@lru_cache(maxsize=1)
def plaque_height() -> int:
    """One shared viewBox height for every plaque: the tallest plaque, rounded up to 10."""
    tallest = max(
        _layout(p, lang, 99999, 99999).height for p in active_plaques() for lang in ("jp", "en")
    )
    return int(math.ceil((tallest + BOARD_PAD_BOTTOM) / 10) * 10)


# ---------------------------------------------------------------- defs


def _shape(bottom: float, inset: float = 0) -> str:
    i = inset
    return (
        f"M{_g(PL + i)},{_g(SHOULDER + i * 0.6)} L{CX},{_g(PEAK + i * 1.15)} L{_g(PR - i)},{_g(SHOULDER + i * 0.6)} "
        f"L{_g(PR - i)},{_g(bottom - i)} L{_g(PL + i)},{_g(bottom - i)} Z"
    )


def _defs(h: int) -> str:
    bottom = h - BOARD_PAD_BOTTOM
    grain_ys = [112 + k * 38 for k in range(int((bottom - 112) / 38) + 1)]
    grain = "".join(
        f'<path d="M{PL},{y} C{PL + 120},{y - 9 + d} {PR - 150},{y + 9 - d} {PR},{y - 3}"/>'
        for y, d in zip(grain_ys, [0, 4, -2, 5, 1, -4, 3, -1, 2, -3, 4, 0, -2])
    )
    return (
        f'<clipPath id="card"><rect width="{W}" height="{h}" rx="16"/></clipPath>'
        + petal_def()
        + f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["night-0"]}"/>'
        f'<stop offset="0.65" stop-color="{P["night-1"]}"/><stop offset="1" stop-color="{P["night-2"]}"/></linearGradient>'
        f'<radialGradient id="halo" cx="0.5" cy="0.45" r="0.6"><stop offset="0" stop-color="{P["lantern-glow-a"]}" stop-opacity="0.3"/>'
        f'<stop offset="1" stop-color="{P["lantern-glow-a"]}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="wood" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["wood-a"]}"/>'
        f'<stop offset="0.55" stop-color="#c3914f"/><stop offset="1" stop-color="{P["wood-b"]}"/></linearGradient>'
        f'<linearGradient id="sheenG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff4dc" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="#fff4dc" stop-opacity="0.26"/><stop offset="1" stop-color="#fff4dc" stop-opacity="0"/></linearGradient>'
        f'<radialGradient id="lacquer" cx="0.5" cy="0.4" r="0.65"><stop offset="0" stop-color="#22163a"/>'
        f'<stop offset="1" stop-color="{P["night-0"]}"/></radialGradient>'
        f'<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0.45"/>'
        f'<stop offset="0.5" stop-color="{P["vermilion"]}" stop-opacity="0.18"/>'
        f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0.35"/></linearGradient>'
        f'<linearGradient id="divider" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{P["ink-red"]}" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="{P["ink-red"]}" stop-opacity="0.7"/><stop offset="1" stop-color="{P["ink-red"]}" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="plaqueClip"><path d="{_shape(bottom)}"/></clipPath>'
        f'<clipPath id="win"><circle cx="0" cy="0" r="{WINDOW_R - 3}"/></clipPath>'
        '<filter id="hang" x="-10%" y="-10%" width="120%" height="130%">'
        '<feDropShadow dx="0" dy="7" stdDeviation="7" flood-color="#000" flood-opacity="0.55"/></filter>'
        '<filter id="carve" x="-5%" y="-20%" width="110%" height="150%">'
        f'<feDropShadow dx="0" dy="1" stdDeviation="0.2" flood-color="{P["moon-b"]}" flood-opacity="0.5"/></filter>'
        '<filter id="cglow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<filter id="ink" x="-10%" y="-10%" width="120%" height="120%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="7" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="1.6" xChannelSelector="R" yChannelSelector="G"/></filter>'
        f'<g id="grain" clip-path="url(#plaqueClip)" stroke="{P["wood-grain"]}" stroke-opacity="0.22" fill="none" stroke-width="1.3">{grain}</g>'
    )


# ---------------------------------------------------------------- frame pieces


def _scene_back(h: int, ph: _Phase) -> str:
    """Card background, breathing lantern glow, stars, petals behind the board, the rope."""
    stars = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff"' + (' class="node"' if i % 3 == 0 else ' opacity="0.6"') + "/>"
        for i, (x, y, r) in enumerate(
            ((30, 64, 1.1), (392, 52, 1.2), (110, 40, 0.8), (318, 36, 0.9), (6, 220, 0.9), (414, 300, 0.9))
        )
    )
    return (
        f'<rect width="{W}" height="{h}" fill="url(#bg)"/>'
        f'<rect width="{W}" height="{h}" fill="url(#halo)" class="toriiGlow"{ph()}/>'
        f"{stars}"
        + petals([(70, 1, 12, -2), (300, 0.8, 14, -7), (430, 1.1, 13, -4), (520, 0.9, 15, -1)])
        + f'<g transform="translate(0,4)">{rope(W)}</g>'
    )


def _cord(ph: _Phase) -> str:
    red = P["vermilion"]
    return (
        f'<path d="M{CX},24 L188,62 M{CX},24 L232,62" stroke="{red}" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
        f'<circle cx="{CX}" cy="24" r="4.5" fill="{red}"/>'
        f'<path class="tassel" d="M{CX},27 l-3,13 l3,-2 l3,2 z" fill="{red}" opacity="0.9"{ph(-1)}/>'
    )


def _board(h: int, ph: _Phase) -> str:
    bottom = h - BOARD_PAD_BOTTOM
    holes = "".join(f'<circle cx="{x}" cy="62" r="3.4" fill="{P["ink-a"]}" opacity="0.75"/>' for x in (188, 232))
    return (
        # the board's thickness, seen below and to the right of the face
        f'<path d="{_shape(bottom)}" transform="translate(2.5,3.5)" fill="{EDGE}"/>'
        f'<path d="{_shape(bottom)}" fill="url(#wood)" stroke="{EDGE}" stroke-width="2"/>'
        '<use href="#grain" xlink:href="#grain"/>'
        f'<path d="{_shape(bottom, 7)}" fill="none" stroke="{P["moon-b"]}" stroke-opacity="0.28" stroke-width="1.2"/>'
        f'<g clip-path="url(#plaqueClip)"><g transform="rotate(14 75 {h // 2})">'
        f'<rect class="sheen" x="40" y="-40" width="70" height="{h + 80}" fill="url(#sheenG)"{ph()}/></g></g>'
        + holes
        + f'<path d="M188,62 l-2,6 M232,62 l2,6" stroke="{P["vermilion"]}" stroke-width="2.6" stroke-linecap="round"/>'
        + icon("torii", CX - 9, 70, 18, P["ink-red"])
    )


# ---------------------------------------------------------------- stamps (hanko)


def _stamp(p: Plaque, stars: int | None, forks: int | None, x: float, y: float) -> str:
    """A hanko centred at (x, y)."""
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
    else:  # stars: filled square seal, star count over fork count
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
            half = _stamp_half(p, stars, forks)
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
    return f'<g transform="translate({_g(x)},{_g(y)}) rotate(-8)" filter="url(#ink)" opacity="0.92">{inner}</g>'


# ---------------------------------------------------------------- motifs
# Each motif is drawn around (0, 0) inside a window of radius WINDOW_R, then scaled
# down to MOTIF_R on the plaque. `ph(base)` gives an element its animation-delay.


def _window(body: str, x: float, y: float) -> str:
    """A round lacquered window (丸窓) that frames the motif."""
    s = MOTIF_R / WINDOW_R
    return (
        f'<g transform="translate({_g(x)},{_g(y)}) scale({_g(s)})">'
        f'<circle r="{WINDOW_R + 3}" fill="{P["ink-a"]}" opacity="0.35"/>'
        f'<circle r="{WINDOW_R}" fill="url(#lacquer)" stroke="{P["lantern-gold"]}" stroke-opacity="0.8" stroke-width="1.8"/>'
        f'<circle r="{WINDOW_R - 4}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.25" stroke-width="0.8"/>'
        f'<g clip-path="url(#win)">{body}</g></g>'
    )


def _sigil(ph: _Phase) -> tuple[str, str]:
    c = P["circuit-cyan"]
    ticks = "".join(
        f'<rect x="-0.8" y="-46" width="1.6" height="{5 if i % 3 == 0 else 3}" fill="{P["lantern-gold"]}" '
        f'opacity="0.7" transform="rotate({i * 15})"/>'
        for i in range(24)
    )
    nodes = "".join(
        f'<circle cx="{x}" cy="{y}" r="3.4" fill="{c}" class="node"{ph(d)}/>'
        for x, y, d in ((0, -34, 0), (34, 0, -0.6), (0, 34, -1.2), (-34, 0, -1.8))
    )
    body = (
        f'<g class="spinr"{ph()}>{ticks}</g>'
        f'<g filter="url(#cglow)"><g class="spin"{ph()}>'
        f'<circle r="34" fill="none" stroke="{c}" stroke-width="1.6" stroke-dasharray="10 6"/>{nodes}</g>'
        f'<path class="flow" d="M0,-31 L0,-13 M31,0 L13,0 M0,31 L0,13 M-31,0 L-13,0" stroke="{c}" stroke-width="1.6"{ph()}/>'
        f'<circle r="10" fill="{P["vermilion"]}" class="core"{ph()}/>'
        f'<circle r="4" fill="{P["lantern-gold"]}"/></g>'
    )
    return body, ""


def _dashboard(ph: _Phase) -> tuple[str, str]:
    c, gold = P["circuit-cyan"], P["lantern-gold"]
    bars = "".join(
        f'<rect class="bar" x="{-36 + i * 10}" y="{30 - h}" width="7" height="{h}" rx="1.5" '
        f'fill="{c if i != 3 else gold}"{ph(d)}/>'
        for i, (h, d) in enumerate(((16, 0), (26, -0.4), (20, -0.8), (34, -1.2), (28, -1.6)))
    )
    dots = "".join(
        f'<circle cx="{x}" cy="-19" r="2.4" fill="{P["night-1"]}" class="typing"{ph(d)}/>'
        for x, d in ((9, 0), (17, -0.2), (25, -0.4))
    )
    body = (
        f'<path d="M-40,31 L14,31" stroke="{P["text-soft-b"]}" stroke-width="1"/>'
        f'<g filter="url(#cglow)">{bars}</g>'
        f'<polyline class="trend" points="-33,16 -23,6 -13,11 -3,-4 7,1" fill="none" stroke="{P["sakura-b"]}" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"{ph()}/>'
        f'<g class="bob"{ph()}><path d="M0,-31 h34 a6,6 0 0 1 6,6 v12 a6,6 0 0 1 -6,6 h-20 l-8,8 v-8 h-6 '
        f'a6,6 0 0 1 -6,-6 v-12 a6,6 0 0 1 6,-6 z" fill="{P["moon-a"]}"/>{dots}</g>'
        f'<circle cx="34" cy="20" r="9" fill="none" stroke="{c}" stroke-width="1.4" stroke-dasharray="3 3" class="spinc"{ph()}/>'
        f'<circle cx="34" cy="20" r="3" fill="{P["vermilion"]}" class="core"{ph()}/>'
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


def _facilitator(ph: _Phase) -> tuple[str, str]:
    moon, gold = P["moon-b"], P["lantern-gold"]
    personas = (P["vermilion"], P["circuit-cyan"], gold, P["sakura-b"])
    nodes = "".join(
        f'<g transform="rotate({i * 90}) translate(0,-38)">'
        f'<circle r="6.5" fill="{col}" opacity="0.25"/><circle r="4" fill="{col}" class="node"{ph(-i * 0.6)}/></g>'
        for i, col in enumerate(personas)
    )
    ripples = "".join(
        f'<circle r="16" fill="none" stroke="{P["circuit-cyan"]}" stroke-width="1.2" class="ripple"{ph(d)}/>'
        for d in (0, -1, -2)
    )
    body = (
        f'<circle r="38" fill="none" stroke="{P["text-soft-b"]}" stroke-opacity="0.45" stroke-dasharray="2 5"/>'
        f"{ripples}"
        f'<g class="spin" filter="url(#cglow)"{ph()}>{nodes}</g>'
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
    """Points along a torii outline (motif coordinates), for the drone formation."""
    pts: list[tuple[float, float]] = []
    for i in range(13):  # kasagi: the top beam, curving up at the ends
        x = -36 + i * 6
        pts.append((x, -24 - 4 * (x / 36) ** 2))
    for i in range(9):  # nuki: the second beam
        pts.append((-28 + i * 7, -10))
    pts.append((0, -17))  # gakuzuka
    for side in (-1, 1):  # pillars, slightly splayed
        for i in range(7):
            t = i / 6
            pts.append((side * (19 + 4 * t), -10 + t * 38))
    return pts


def _drone(ph: _Phase) -> tuple[str, str]:
    """Drone lights drift, converge into a torii, glow gold, hold, and scatter again (12 s)."""
    rnd = random.Random(1500)
    dots, kf = [], []
    for i, (tx, ty) in enumerate(_torii_points()):
        while True:
            sx, sy = rnd.uniform(-44, 44), rnd.uniform(-44, 40)
            if sx * sx + sy * sy < 44 * 44:
                break
        dx1, dy1 = sx - tx, sy - ty
        dx2, dy2 = dx1 + rnd.uniform(-6, 6), dy1 + rnd.uniform(-6, 6)
        a, b = rnd.uniform(4, 10), rnd.uniform(20, 30)
        kf.append(
            f"@keyframes dr{i}{{0%,100%{{transform:translate({_g(dx1)}px,{_g(dy1)}px)}}"
            f"{_g(a)}%{{transform:translate({_g(dx2)}px,{_g(dy2)}px)}}"
            f"{_g(b)}%,70%{{transform:translate(0,0)}}"
            f"{_g(86 + a / 2)}%{{transform:translate({_g(dx2)}px,{_g(dy2)}px)}}}}"
        )
        dots.append(
            f'<circle cx="{_g(tx)}" cy="{_g(ty)}" r="1.9" class="dr" '
            f'style="animation-name:dr{i},drc;animation-delay:{ph.delay}"/>'
        )
    outline = "M-38,-25 Q0,-20 38,-25 M-30,-10 H30 M0,-22 V-10 M-19,-22 L-23,30 M19,-22 L23,30"
    body = (
        f'<path d="M-44,32 H44" stroke="{P["text-soft-b"]}" stroke-opacity="0.35" stroke-dasharray="1 4"/>'
        f'<path class="ghost" d="{outline}" fill="none" stroke="{P["vermilion"]}" stroke-width="5" '
        f'stroke-linecap="round" filter="url(#cglow)"{ph()}/>'
        f'<g filter="url(#cglow)">{"".join(dots)}</g>'
    )
    css = (
        ".dr{animation-duration:12s;animation-timing-function:ease-in-out;animation-iteration-count:infinite}"
        f"@keyframes drc{{0%,18%,88%,100%{{fill:{P['circuit-cyan']}}}32%,70%{{fill:{P['lantern-gold']}}}}}"
        ".ghost{opacity:0;animation:ghost 12s ease-in-out infinite}"
        "@keyframes ghost{0%,24%,80%,100%{opacity:0}34%,68%{opacity:.45}}"
        + "".join(kf)
    )
    return body, css


def _eye(ph: _Phase) -> tuple[str, str]:
    c = P["circuit-cyan"]
    body = (
        f'<circle r="44" fill="none" stroke="{c}" stroke-opacity="0.5" stroke-width="1.2" stroke-dasharray="14 8" class="spin"{ph()}/>'
        f'<g class="blink" filter="url(#cglow)"{ph()}>'
        f'<path d="M-38,0 Q0,-30 38,0 Q0,30 -38,0 Z" fill="{P["moon-a"]}" stroke="{c}" stroke-width="2"/>'
        f'<g class="look"{ph()}><circle r="13" fill="{c}"/><circle r="13" fill="none" stroke="#0b6b70" stroke-width="2"/>'
        f'<circle r="6" fill="{P["night-0"]}"/><circle cx="-4" cy="-4" r="2.6" fill="#fff"/></g></g>'
        # the phish hook, dangling on its line
        f'<g class="dangle"{ph()}><path d="M28,-60 V-18" stroke="{P["moon-b"]}" stroke-opacity="0.7" stroke-width="1"/>'
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


def _wave(ph: _Phase) -> tuple[str, str]:
    n = 17
    bars = []
    for i in range(n):
        x = -40 + i * 5
        env = 1 - abs(i - (n - 1) / 2) / ((n - 1) / 2)
        h = 8 + 52 * env * (0.6 + 0.4 * ((i * 7) % 5) / 4)
        bars.append(
            f'<rect class="wv" x="{_g(x - 1.6)}" y="{_g(-h / 2)}" width="3.2" height="{_g(h)}" rx="1.6"{ph(-i * 0.11)}/>'
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


# ---------------------------------------------------------------- the face


def _pill(p: Plaque) -> str:
    client = p.kind == "client"
    label = "CLIENT WORK" if client else "OPEN SOURCE"
    fg = P["lantern-gold"] if client else P["circuit-cyan"]
    bg = "#3a1d0e" if client else TEAL
    ls = 1
    w = 12 + 15 + 7 + text_width(label, 14, mono=True, letter_spacing=ls) + 10
    x, y = LEFT, 98
    return (
        f'<rect x="{x}" y="{y}" width="{_g(w)}" height="26" rx="13" fill="{bg}" fill-opacity="0.9"/>'
        + icon("lock" if client else "globe", x + 11, y + 5.5, 15, fg)
        + f'<text x="{_g(x + 33)}" y="{y + 18}" {MONO} font-size="14" font-weight="700" fill="{fg}" '
        f'letter-spacing="{ls}">{label}</text>'
    )


def _face(p: Plaque, lang: Lang, lay: _Layout, h: int, motif: str, stars: int | None, forks: int | None) -> str:
    ink, red = P["ink-a"], P["ink-red"]
    bottom = h - BOARD_PAD_BOTTOM
    extra = max(0.0, bottom - lay.height)  # spare height on shorter plaques
    out = [_pill(p)]
    if p.years:
        out.append(f'<text x="{RIGHT}" y="116" text-anchor="end" {MONO} font-size="14" fill="{P["ink-b"]}">{esc(p.years)}</text>')

    # title row: title block on the left, motif window on the right
    row_top = 124 + ROW_GAP + extra * 0.2
    row_h = lay.parts["row_h"]
    y = row_top + (row_h - lay.parts["title_h"]) / 2 + lay.title_size * 0.82
    ts = lay.title_size
    for i, t in enumerate(lay.title):
        out.append(
            f'<text x="{LEFT}" y="{_g(y + i * ts * 1.2)}" {SERIF} font-size="{ts}" font-weight="700" '
            f'fill="{ink}" filter="url(#carve)">{esc(t)}</text>'
        )
    y += (len(lay.title) - 1) * ts * 1.2 + 13 + SUB_SIZE * 0.85
    for i, t in enumerate(lay.sub):
        out.append(
            f'<text x="{LEFT}" y="{_g(y + i * 20)}" {SERIF} font-size="{SUB_SIZE}" fill="{red}" '
            f'letter-spacing="{_g(lay.sub_ls)}">{esc(t)}</text>'
        )
    out.append(_window(motif, MOTIF_CX, row_top + row_h / 2))

    # divider: a fading rule with a small diamond
    dy = row_top + row_h + DIV_ABOVE + extra * 0.15
    out.append(
        f'<rect x="{LEFT}" y="{_g(dy - 0.6)}" width="{INNER_W}" height="1.2" fill="url(#divider)"/>'
        f'<path d="M{CX},{_g(dy - 4)} l4,4 l-4,4 l-4,-4 z" fill="{red}"/>'
    )

    # details: JP items get a diamond marker and a hanging indent; the EN paragraph runs full width
    size, lh = DETAIL_SIZE[lang], DETAIL_LH[lang]
    y = dy + DIV_BELOW + extra * 0.2 + size * 0.85
    text = []
    marked = lang == "jp"
    tx = DETAIL_X if marked else LEFT
    for item in lay.items:
        if marked:
            text.append(f'<path d="M{LEFT + 4},{_g(y - 9)} l3.5,3.5 l-3.5,3.5 l-3.5,-3.5 z" fill="{red}" opacity="0.85"/>')
        for k, line in enumerate(item):
            text.append(
                f'<text x="{tx}" y="{_g(y + k * lh)}" {SERIF} font-size="{size}" fill="{ink}">{esc(line)}</text>'
            )
        y += len(item) * lh + ITEM_GAP
    y -= lh + ITEM_GAP  # back to the last baseline

    if lay.nda:
        y += NDA_GAP + 14
        text.append(
            f'<path d="M{LEFT},{_g(y - 21)} H{RIGHT}" stroke="{red}" stroke-opacity="0.35" stroke-dasharray="2 4"/>'
            + icon("lock", LEFT, y - 12.5, 14, red)
        )
        for k, line in enumerate(lay.nda):
            text.append(f'<text x="{LEFT + 19}" y="{_g(y + k * 20)}" {SERIF} font-size="14" fill="{red}">{esc(line)}</text>')
        y += (len(lay.nda) - 1) * 20
    out.append(f'<g filter="url(#carve)">{"".join(text)}</g>')

    # footer: tag chips on the left, the stamp on the right, anchored to the bottom
    foot_h = lay.parts["foot_h"]
    foot_top = bottom - FOOT_PAD - foot_h
    if foot_top < y + 10:
        raise ValueError(f"{p.id}/{lang}: plaque content overflows the board")
    ty = foot_top + (foot_h - lay.parts["tags_h"]) / 2
    for row in lay.tag_rows:
        x = LEFT
        for t, w in row:
            out.append(
                f'<rect x="{_g(x)}" y="{_g(ty)}" width="{_g(w)}" height="{TAG_H}" rx="5" fill="{ink}" fill-opacity="0.9"/>'
                f'<text x="{_g(x + w / 2)}" y="{_g(ty + 16.6)}" text-anchor="middle" {MONO} font-size="14" '
                f'fill="{P["moon-a"]}">{esc(t)}</text>'
            )
            x += w + TAG_GAP
        ty += TAG_H + TAG_GAP
    out.append(_stamp(p, stars, forks, RIGHT - lay.stamp_half + 2, foot_top + foot_h / 2))
    return "".join(out)


# ---------------------------------------------------------------- card


def render_plaque(
    p: Plaque,
    lang: Lang,
    index: int,
    fonts,
    stars: int | None = None,
    forks: int | None = None,
) -> str:
    h = plaque_height()
    ph = _Phase(index)
    lay = _layout(p, lang, stars, forks)
    motif_body, motif_css = MOTIFS.get(p.motif, _sigil)(ph)
    shide = f".rope path:nth-child(n+3){{animation-delay:-{ph.off:g}s}}" if index else ""
    body = (
        '<g clip-path="url(#card)">'
        + _scene_back(h, ph)
        + '<g filter="url(#hang)">'
        + _cord(ph)
        + _board(h, ph)
        + _face(p, lang, lay, h, motif_body, stars, forks)
        + "</g></g>"
        + f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{h - 1.5}" rx="15.25" fill="none" '
        'stroke="url(#frame)" stroke-width="1.5"/>'
    )
    title = f"{p.title(lang)} · {p.subtitle(lang)}"
    svg = document(W, h, body, title=title, css=MOTION_CSS + PLAQUE_CSS + shide + motif_css, defs=_defs(h))
    return embed_fonts(svg, fonts)
