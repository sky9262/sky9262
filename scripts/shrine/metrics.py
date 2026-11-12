"""Stdlib text measurement for the embedded fonts (no fontTools at runtime).

Advance widths (units per em = 1000) of Noto Serif JP Regular/Bold for printable
ASCII and the symbols the cards use, read from the fonts with fontTools once and
pinned here; tests/test_cards_static.py::test_metrics_match_fonts re-checks them.
East Asian wide/full-width characters are one em; JetBrains Mono is 0.6 em.
"""
from __future__ import annotations

import re
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


# Break costs, in the same units as the squared slack (in ems) of a line.
_FREE_AFTER = set("、。，．！？：；")  # a break right after these is natural
_PROHIBIT = 500.0  # effectively forbidden; only taken when nothing else fits
# A line that would start with hiragana begins with a particle (は が を に で と の
# も へ や から まで より) or with okurigana / a word's continuation: never do that.
# Breaking after a particle, before a new word, is the natural Japanese break.
_AFTER_PARTICLE = 0.5
_AFTER_NAKAGURO = 1.0  # 検索・|AI: between list items
_BEFORE_BRACKET = 8.0  # allowed, but keep a name with its gloss: Cloud Armor（WAF）
_PAIR_COST = {
    ("K", "K"): 100.0,  # inside a katakana word
    ("K", "C"): 60.0, ("C", "K"): 60.0,  # katakana+kanji compound: テナント分離, 音声モデル
    ("C", "C"): 30.0,  # inside a kanji compound
    ("A", "C"): 25.0, ("A", "K"): 25.0, ("C", "A"): 25.0, ("K", "A"): 25.0,  # Silicon上, AIエージェント
}
_DASHES = set("–—")
_CAP_PAIR = 15.0  # English: between two Capitalised words ("Cloud Run")
BAD_BREAK = 25.0  # a break this costly (split compound, line-initial particle) is worse than an extra line
# Multi-word names that never break (Japanese and English text alike).
NO_BREAK = (
    "Cloud Armor", "Cloud Run", "Apple Silicon", "Hugging Face", "Identity Platform",
    "Agent SDK", "Claude API", "Burp Suite", "Parrot OS",
)
_NO_BREAK_PAIRS = {
    (a, b) for name in NO_BREAK for a, b in zip(name.split(" "), name.split(" ")[1:])
}


def _word_core(tok: str, end: bool) -> str:
    """The Latin word at the end (or start) of a token."""

    word = r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*"  # "Three.js" yes, a trailing "." no
    m = re.search(word + "$" if end else "^" + word, tok)
    return m.group(0) if m else ""


def _break_cost(before: str, after: str, spaced: bool) -> float:
    """Cost of ending a line with token `before` and starting the next with `after`."""
    if spaced:
        if after[:1] in _DASHES or before[-1:] in _DASHES:
            # a spaced dash binds both sides: "デベロッパー – アソシエイト" stays on one line
            return BAD_BREAK
        a, b = _word_core(before, True), _word_core(after, False)
        if (a, b) in _NO_BREAK_PAIRS:
            return _PROHIBIT
        if a[:1].isupper() and b[:1].isupper():
            return _CAP_PAIR
        return 0.0
    x, y = before[-1], after[0]
    if x in _FREE_AFTER:
        return 0.0
    ky = _kind(y)
    if ky == "H":
        return _PROHIBIT
    if x == "・":
        return _AFTER_NAKAGURO
    if y in "（「『【〔〈《":
        return _BEFORE_BRACKET
    kx = "A" if x in "）」』】〕〉》" else _kind(x)  # a particle after a bracket binds to it
    if kx == "H":
        return _AFTER_PARTICLE
    return _PAIR_COST.get((kx, ky), 2.0)


def wrap(text: str, size: float, width: float, *, weight: int = 400, letter_spacing: float = 0.0) -> list[str]:
    """Line breaking for Japanese and English that never truncates.

    Avoids bad breaks first (a line starting with a particle or okurigana, a
    split katakana/kanji compound, a split product name such as "Cloud Armor"),
    even at the price of an extra line; then uses the fewest lines; then picks
    the most even line lengths with no orphaned last line, preferring breaks
    after 、。 and after particles, and following kinsoku rules. English breaks only at
    spaces. A single piece wider than `width` gets its own (overlong) line, so
    callers that must fit should check the result with text_width().
    """
    toks = _tokens(text)
    n = len(toks)

    def measure(s: str) -> float:
        return text_width(s, size, weight=weight, letter_spacing=letter_spacing)

    def penalty(j: int) -> float:
        if toks[j - 1] == " " or toks[j] == " ":
            before = next((t for t in reversed(toks[:j]) if t != " "), "")
            after = next((t for t in toks[j:] if t != " "), "")
            return _break_cost(before, after, True)
        return _break_cost(toks[j - 1], toks[j], False)

    INF = (10**9, 10**9, 0.0)
    best: list[tuple[int, int, float]] = [INF] * (n + 1)
    nxt = [n] * (n + 1)
    best[n] = (0, 0, 0.0)
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
            bad = 0
            if j == n:  # last line: only penalise an orphan
                cost = 4 * max(0.0, (0.5 * width - w) / size) ** 2
            else:
                pen = penalty(j)
                bad = int(pen >= BAD_BREAK)
                cost = ((width - w) / size) ** 2 + pen
            cand = (best[j][0] + bad, best[j][1] + 1, best[j][2] + cost)
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
