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


# ---------------------------------------------------------------- line wrapping

# Japanese line-breaking (禁則処理): never start a line with these ...
_NO_START = set("、。，．・：；？！ー）」』】〕〉》｝’”%％,.:;!?)]}…‥々ゝゞぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ")
# ... and never end a line with these.
_NO_END = set("（「『【〔〈《｛‘“([{")


def _is_wide(ch: str) -> bool:
    return unicodedata.east_asian_width(ch) in ("W", "F")


def _tokens(text: str) -> list[str]:
    """Unbreakable pieces: one wide character, a run of narrow non-space characters, or a space."""
    out: list[str] = []
    run = ""
    for ch in text:
        if ch == " " or _is_wide(ch):
            if run:
                out.append(run)
                run = ""
            out.append(ch)
        else:
            run += ch
    if run:
        out.append(run)
    # glue kinsoku characters to their neighbours
    glued: list[str] = []
    for tok in out:
        if glued and glued[-1] != " " and (tok[0] in _NO_START or glued[-1][-1] in _NO_END):
            glued[-1] += tok
        else:
            glued.append(tok)
    return glued


def _kind(ch: str) -> str:
    o = ord(ch)
    if ch in "、。，．）」』】〕〉》・：；？！":
        return "P"
    if 0x3040 <= o <= 0x309F:
        return "H"  # hiragana
    if 0x30A0 <= o <= 0x30FF:
        return "K"  # katakana (incl. ー)
    if _is_wide(ch):
        return "C"  # kanji and other wide characters
    return "A"  # Latin, digits, narrow symbols


# Cost of a line break between two character kinds. Breaking after punctuation or
# a particle (hiragana before a new word) is natural Japanese; splitting a
# katakana or kanji compound is not.
_BREAK_COST = {
    ("H", "C"): 1, ("H", "K"): 1, ("H", "A"): 1,
    ("A", "C"): 3, ("A", "K"): 3, ("C", "A"): 3, ("K", "A"): 3, ("C", "K"): 4, ("K", "C"): 4,
    ("C", "H"): 5, ("K", "H"): 5, ("A", "H"): 6, ("H", "H"): 6,
    ("C", "C"): 14, ("K", "K"): 40, ("A", "A"): 2,
}


def wrap(text: str, size: float, width: float, *, weight: int = 400, letter_spacing: float = 0.0) -> list[str]:
    """Line breaking for Japanese and English that never truncates.

    Uses the fewest lines possible; among those, picks the breaks with the most
    even line lengths, no orphaned last line, and (for Japanese) breaks at
    natural phrase boundaries, following kinsoku rules. English breaks only at
    spaces. A single piece wider than `width` gets its own (overlong) line, so
    callers that must fit should check the result with text_width().
    """
    toks = _tokens(text)
    n = len(toks)

    def measure(s: str) -> float:
        return text_width(s, size, weight=weight, letter_spacing=letter_spacing)

    def penalty(j: int) -> float:
        a, b = toks[j - 1], toks[j]
        if a == " " or b == " ":
            return 0.0
        ka, kb = _kind(a[-1]), _kind(b[0])
        return 0.0 if ka == "P" else float(_BREAK_COST.get((ka, kb), 2))

    INF = (10**9, 0.0)
    best: list[tuple[int, float]] = [INF] * (n + 1)
    nxt = [n] * (n + 1)
    best[n] = (0, 0.0)
    for i in range(n - 1, -1, -1):
        if toks[i] == " ":
            best[i], nxt[i] = best[i + 1], nxt[i + 1]
            continue
        for j in range(i + 1, n + 1):
            line = "".join(toks[i:j]).strip()
            w = measure(line)
            if w > width and j > i + 1:
                break
            if best[j] == INF:
                continue
            if j == n:  # last line: only penalise an orphan
                cost = 4 * max(0.0, (0.4 * width - w) / size) ** 2
            else:
                cost = ((width - w) / size) ** 2 + penalty(j)
            cand = (best[j][0] + 1, best[j][1] + cost)
            if cand < best[i]:
                best[i], nxt[i] = cand, j
    lines, i = [], 0
    while i < n:
        j = nxt[i]
        line = "".join(toks[i:j]).strip()
        if line:
            lines.append(line)
        i = j
    return lines
