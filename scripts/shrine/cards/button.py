"""Link buttons and the language toggle.

Buttons (220x56, shown at native width, language-neutral): one black-lacquer plate
per LINKS entry, with a gold rim, the brand glyph in a lacquered roundel, the label
and a small gold chevron. A soft lantern-gold glow breathes along the rim and a
sheen crosses the lacquer now and then (no hover: GitHub shows them as <img>).
Each plate fills its whole viewBox, so it reads the same in light and dark mode.

Toggle (180x44): a small wooden sign (立て札) with TOGGLE(lang) in ink.

Stdlib only.
"""
from __future__ import annotations

from ..content import LINKS, TOGGLE, Lang
from ..icons import icon
from ..metrics import text_width
from ..palette import PALETTE as P
from ..svg import document, embed_fonts, esc
from .connect import glyph_color

SERIF = 'font-family="Shrine Serif"'
GOLD_DARK = "#9a6424"

BW, BH = 220, 56
LABEL_X = 60
CHEVRON_X = 201  # left edge of the chevron path
LABEL_MAX = 190 - LABEL_X  # stop 11 units short of the chevron
LABEL_SIZE = 18
MIN_SIZE = 12

TW, TH = 180, 44
TOGGLE_SIZE = 17

BUTTON_CSS = """
.rim{animation:rim 4.5s ease-in-out infinite}
@keyframes rim{0%,100%{opacity:.35}50%{opacity:.85}}
.bsheen{animation:bsheen 9s ease-in-out infinite}
@keyframes bsheen{0%,70%{transform:translateX(-120px)}88%,100%{transform:translateX(330px)}}
.nudge{animation:nudge 2.6s ease-in-out infinite}
@keyframes nudge{0%,100%{transform:translateX(0)}50%{transform:translateX(2.5px)}}
"""

TOGGLE_CSS = """
.tsheen{animation:tsheen 8s ease-in-out infinite}
@keyframes tsheen{0%,72%{transform:translateX(-90px)}90%,100%{transform:translateX(260px)}}
"""


def _g(v: float) -> str:
    return f"{round(v, 2):g}"


def _fit(text: str, size: float, width: float) -> float:
    while text_width(text, size, weight=700, letter_spacing=0.3) > width and size > MIN_SIZE:
        size -= 0.5
    return size


def _link(link_id: str) -> tuple[int, str]:
    for i, (lid, label, _) in enumerate(LINKS):
        if lid == link_id:
            return i, label
    raise KeyError(link_id)


def render_button(link_id: str, fonts) -> str:
    i, label = _link(link_id)
    color = glyph_color(link_id)
    size = _fit(label, LABEL_SIZE, LABEL_MAX)
    cy = BH / 2
    defs = (
        f'<clipPath id="plate"><rect width="{BW}" height="{BH}" rx="12"/></clipPath>'
        f'<linearGradient id="lac" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a1f48"/>'
        f'<stop offset="0.5" stop-color="{P["night-1"]}"/><stop offset="1" stop-color="{P["night-0"]}"/></linearGradient>'
        f'<linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.12"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="rimG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["moon-a"]}"/>'
        f'<stop offset="0.4" stop-color="{P["lantern-gold"]}"/><stop offset="1" stop-color="{GOLD_DARK}"/></linearGradient>'
        f'<linearGradient id="sheenG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{P["moon-a"]}" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="{P["moon-a"]}" stop-opacity="0.16"/><stop offset="1" stop-color="{P["moon-a"]}" stop-opacity="0"/></linearGradient>'
        f'<radialGradient id="tint" cx="0.14" cy="0.5" r="0.5"><stop offset="0" stop-color="{color}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
        '<filter id="blur" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="3"/></filter>'
    )
    body = (
        '<g clip-path="url(#plate)">'
        f'<rect width="{BW}" height="{BH}" fill="url(#lac)"/>'
        f'<rect width="{BW}" height="{BH}" fill="url(#tint)"/>'
        f'<rect width="{BW}" height="{_g(BH / 2)}" fill="url(#gloss)"/>'
        # lantern-gold glow breathing along the inside of the rim
        f'<rect x="1" y="1" width="{BW - 2}" height="{BH - 2}" rx="11" fill="none" stroke="{P["lantern-glow-a"]}" '
        f'stroke-width="7" filter="url(#blur)" class="rim" style="animation-delay:{-0.6 * i:g}s"/>'
        f'<g transform="rotate(18 {BW / 2} {cy})"><rect class="bsheen" x="-40" y="-40" width="44" height="140" fill="url(#sheenG)" '
        f'style="animation-delay:{0.9 * i:g}s"/></g>'
        "</g>"
        f'<rect x="0.75" y="0.75" width="{BW - 1.5}" height="{BH - 1.5}" rx="11.25" fill="none" stroke="url(#rimG)" stroke-width="1.5"/>'
        f'<rect x="4.5" y="4.5" width="{BW - 9}" height="{BH - 9}" rx="8" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.22" stroke-width="0.8"/>'
        # vermilion lacquer accent on the left edge
        f'<path d="M4.5,14 V42" stroke="{P["vermilion"]}" stroke-width="2" stroke-linecap="round"/>'
        # roundel with the glyph
        f'<circle cx="31" cy="{cy}" r="17" fill="{P["night-0"]}" stroke="url(#rimG)" stroke-width="1.4"/>'
        f'<circle cx="31" cy="{cy}" r="13.6" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.25" stroke-width="0.7"/>'
        + icon(link_id, 31 - 9.5, cy - 9.5, 19, color)
        + f'<text x="{LABEL_X}" y="{_g(cy + size * 0.36)}" {SERIF} font-size="{_g(size)}" font-weight="700" '
        f'fill="{P["moon-a"]}" letter-spacing="0.3">{esc(label)}</text>'
        f'<g class="nudge"><path d="M{CHEVRON_X},{_g(cy - 5.5)} l5.5,5.5 l-5.5,5.5" fill="none" stroke="{P["lantern-gold"]}" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></g>'
    )
    svg = document(BW, BH, body, title=label, css=BUTTON_CSS, defs=defs)
    return embed_fonts(svg, fonts)


def render_toggle(lang: Lang, fonts) -> str:
    text = TOGGLE(lang)
    size = TOGGLE_SIZE
    ico = 16
    gap = 7
    tw = text_width(text, size, weight=700)
    x0 = (TW - (ico + gap + tw)) / 2
    cy = TH / 2
    edge = "#6b4420"
    defs = (
        f'<clipPath id="sign"><rect width="{TW}" height="{TH}" rx="8"/></clipPath>'
        f'<linearGradient id="wood" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["wood-a"]}"/>'
        f'<stop offset="0.55" stop-color="#c3914f"/><stop offset="1" stop-color="{P["wood-b"]}"/></linearGradient>'
        f'<linearGradient id="sheenG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff4dc" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="#fff4dc" stop-opacity="0.35"/><stop offset="1" stop-color="#fff4dc" stop-opacity="0"/></linearGradient>'
    )
    grain = "".join(
        f'<path d="M0,{y} C50,{y - 4 + d} 120,{y + 4 - d} {TW},{y - 1}"/>' for y, d in ((9, 0), (19, 2), (29, -1), (38, 2))
    )
    nails = "".join(
        f'<circle cx="{x}" cy="{cy}" r="2.6" fill="{P["ink-b"]}"/><circle cx="{x - 0.6}" cy="{cy - 0.6}" r="0.9" fill="{P["moon-b"]}" opacity="0.6"/>'
        for x in (10, TW - 10)
    )
    body = (
        '<g clip-path="url(#sign)">'
        f'<rect width="{TW}" height="{TH}" fill="url(#wood)"/>'
        f'<g stroke="{P["wood-grain"]}" stroke-opacity="0.25" fill="none" stroke-width="1.1">{grain}</g>'
        f'<g transform="rotate(20 {TW / 2} {cy})"><rect class="tsheen" x="-40" y="-40" width="40" height="124" fill="url(#sheenG)"/></g>'
        f'<rect y="{TH - 4}" width="{TW}" height="4" fill="{edge}" opacity="0.55"/>'
        "</g>"
        f'<rect x="1" y="1" width="{TW - 2}" height="{TH - 2}" rx="7" fill="none" stroke="{edge}" stroke-width="2"/>'
        f'<rect x="5" y="5" width="{TW - 10}" height="{TH - 10}" rx="4" fill="none" stroke="{P["ink-red"]}" stroke-opacity="0.5" stroke-width="1"/>'
        + nails
        + icon("globe", x0, cy - ico / 2, ico, P["ink-red"])
        + f'<text x="{_g(x0 + ico + gap)}" y="{_g(cy + size * 0.36)}" {SERIF} font-size="{size}" font-weight="700" '
        f'fill="{P["ink-a"]}">{esc(text)}</text>'
    )
    svg = document(TW, TH, body, title=text, css=TOGGLE_CSS, defs=defs)
    return embed_fonts(svg, fonts)
