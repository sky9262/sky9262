"""Privacy check: the last net before anything is published (spec §7.3).

Scans only what a viewer can see (`visible_strings`: text nodes, title/desc,
aria-label/alt/href; never <style> or base64 `data:` payloads) and refuses a
render that names one of the owner's private repos or any deny-list term.

Secrets never leave this module in clear text: errors carry only the file name
and a masked term (first character + `***`). Stdlib only.
"""
from __future__ import annotations

import re
import unicodedata

from ..shrine.svg import visible_strings


class PrivacyError(Exception):
    """A generated SVG names a private repo or a deny-list term."""


def mask(term: str) -> str:
    term = term.strip()
    return (term[:1] or "?") + "***"


def parse_denylist(raw: str | None) -> list[str]:
    """PROFILE_DENYLIST: newline-separated; stripped; blank and `#` lines dropped."""
    out = []
    for line in (raw or "").splitlines():
        t = line.strip()
        if t and not t.startswith("#"):
            out.append(t)
    return out


def _norm(s: str) -> str:
    # NFKC folds full-width / compatibility forms (e.g. ＡＢＣ → ABC) before casefold
    return unicodedata.normalize("NFKC", s).casefold()


def name_pattern(name: str) -> re.Pattern[str]:
    """A private repo name as a whole word: `-` and `\\w` count as name characters."""
    return re.compile(rf"(?<![\w-]){re.escape(_norm(name.strip()))}(?![\w-])")


WINDOW = 4  # the feed breaks a repo name over at most 3 <text> lines
ELLIPSIS = re.compile(r"…|\.\.\.")  # NFKC turns … into ...
MIN_PREFIX = 3  # shortest visible prefix of a cut-off name that still counts


def views(text: str) -> str:
    """visible_strings output plus every run of up to WINDOW adjacent strings joined
    with no separator, so a name broken over several <text> lines is seen whole."""
    lines = [ln for ln in text.split("\n") if ln]
    out = []
    for n in range(1, WINDOW + 1):
        out += ["".join(lines[i:i + n]) for i in range(len(lines) - n + 1)]
    return "\n".join(out)


def _cut_prefix(t: str, term: str, *, word: bool) -> bool:
    """`term` shown cut short: some prefix (>= MIN_PREFIX chars) right before an ellipsis."""
    for m in ELLIPSIS.finditer(t):
        before = t[: m.start()]
        for k in range(len(term) - 1, MIN_PREFIX - 1, -1):
            if before.endswith(term[:k]):
                lead = before[: len(before) - k]
                if not word or not lead or not re.match(r"[\w-]", lead[-1]):
                    return True
    return False


def names_in(text: str, private_names: list[str]) -> list[str]:
    t = _norm(views(text))
    return [
        n for n in private_names
        if n and n.strip()
        and (name_pattern(n).search(t) or _cut_prefix(t, _norm(n.strip()), word=True))
    ]


def terms_in(text: str, deny: list[str]) -> list[str]:
    t = _norm(views(text))
    return [
        d for d in deny
        if d and d.strip()
        and (_norm(d.strip()) in t or _cut_prefix(t, _norm(d.strip()), word=False))
    ]


_STYLE = re.compile(r"<style\b[^>]*>.*?</style\s*>", re.DOTALL | re.IGNORECASE)
_DATA_URI = re.compile(r"data:[^\"'\s)<>]*", re.IGNORECASE)


def markup(svg: str) -> str:
    """The raw SVG minus <style> blocks and data: URIs (ids, classes, data-*,
    comments and attribute values stay in)."""
    return _DATA_URI.sub(" ", _STYLE.sub(" ", svg))


def check(svgs: dict[str, str], private_names: list[str], deny: list[str]) -> None:
    """Raise PrivacyError (file + masked term) on the first leak found.

    Pass 1 (visible text): private names and deny terms. Pass 2 (raw markup):
    private names only; deny substrings would trip on hex colours and path data."""
    names = [n for n in private_names if n and n.strip()]
    for fname in sorted(svgs):
        text = visible_strings(svgs[fname])
        hit = names_in(text, private_names)
        if hit:
            raise PrivacyError(f"{fname}: private repo name {mask(hit[0])}")
        hit = terms_in(text, deny)
        if hit:
            raise PrivacyError(f"{fname}: deny-list term {mask(hit[0])}")
        raw = _norm(markup(svgs[fname]))
        hit = [n for n in names if name_pattern(n).search(raw)]
        if hit:
            raise PrivacyError(f"{fname}: private repo name {mask(hit[0])} in SVG markup")


def scrub(message: str, private_names: list[str], deny: list[str]) -> str:
    """Mask every private name / deny term inside an arbitrary message. The message
    is NFKC-normalised first, so full-width variants are masked too."""
    message = unicodedata.normalize("NFKC", message)
    terms = {t.strip() for t in [*private_names, *deny] if t and t.strip()}
    for term in sorted(terms, key=len, reverse=True):
        m = mask(term)
        for form in {term, unicodedata.normalize("NFKC", term)}:
            message = re.sub(re.escape(form), lambda _, m=m: m, message, flags=re.IGNORECASE)
    return message
