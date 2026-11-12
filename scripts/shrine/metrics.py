"""Stdlib text measurement for the embedded fonts (no fontTools at runtime).

Advance widths (units per em = 1000) of Noto Serif JP Regular/Bold for printable
ASCII and the symbols the cards use, read from the fonts with fontTools once and
pinned here; tests/test_cards_static.py::test_metrics_match_fonts re-checks them.
East Asian wide/full-width characters are one em; JetBrains Mono is 0.6 em.
"""
from __future__ import annotations

import unicodedata

_CHARS = ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~·–—→≥≤×%°’“”…'
_REGULAR = (
    256, 308, 376, 574, 550, 923, 779, 196, 364, 364, 478, 580, 327, 346, 327, 352,
    557, 471, 558, 557, 555, 558, 558, 549, 558, 562, 327, 327, 580, 580, 580, 432,
    912, 718, 670, 691, 770, 652, 629, 741, 853, 405, 403, 731, 625, 975, 796, 767,
    641, 767, 715, 567, 659, 797, 714, 1053, 700, 687, 605, 344, 352, 344, 580, 563,
    435, 557, 638, 538, 629, 547, 388, 566, 663, 332, 311, 607, 334, 974, 661, 596,
    638, 607, 462, 473, 367, 653, 548, 838, 564, 552, 498, 374, 316, 374, 580, 327,
    563, 890, 1000, 1000, 1000, 1000, 923, 342, 232, 426, 425, 1000,
)
_BOLD = (
    250, 355, 447, 615, 589, 966, 803, 235, 400, 400, 485, 603, 335, 370, 335, 400,
    593, 466, 594, 593, 593, 594, 594, 588, 594, 596, 335, 335, 603, 603, 603, 473,
    970, 746, 708, 702, 789, 666, 648, 757, 864, 426, 428, 767, 642, 1001, 815, 785,
    673, 785, 751, 597, 695, 818, 734, 1091, 726, 701, 627, 372, 400, 372, 603, 593,
    447, 585, 672, 565, 658, 572, 402, 596, 687, 349, 335, 651, 355, 1008, 685, 623,
    671, 640, 500, 499, 393, 678, 578, 874, 599, 582, 517, 380, 338, 380, 603, 335,
    593, 928, 1000, 1000, 1000, 1000, 966, 358, 245, 464, 461, 1000,
)
SERIF: dict[int, dict[str, int]] = {
    400: dict(zip(_CHARS, _REGULAR)),
    700: dict(zip(_CHARS, _BOLD)),
}
MONO_ADVANCE = 600


def _advance(ch: str, weight: int) -> int:
    table = SERIF[700 if weight >= 600 else 400]
    if ch in table:
        return table[ch]
    if unicodedata.east_asian_width(ch) in ("W", "F", "A"):
        return 1000
    return 600


def text_width(
    text: str,
    size: float,
    *,
    weight: int = 400,
    mono: bool = False,
    letter_spacing: float = 0.0,
) -> float:
    """Rendered width in user units of one line set at `size`."""
    units = MONO_ADVANCE * len(text) if mono else sum(_advance(c, weight) for c in text)
    return units * size / 1000 + letter_spacing * len(text)
