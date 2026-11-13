import dataclasses
import os
import re

import pytest

from scripts.shrine import content
from scripts.shrine.content import HERO, LINKS, PLAQUES, T, active_plaques

# Every number a client plaque may show. Anything else (fleet sizes, data
# counts, team sizes) must not appear on a client plaque.
ALLOWED_CLIENT_NUMBERS = {
    "2025", "2026",       # project years
    "250",                # automated regression tests
    "197",                # seconds: task that used to time out
    "5",                  # seconds per transcription chunk
    "4",                  # AI persona viewpoints
    "8", "24",            # seconds: agenda check before
    "1.5", "2.5",         # seconds: agenda check after; also 1.5 m drone spacing
    "12.4", "0.4",        # seconds: time to start, before -> after
    "38.4", "3.6",        # percent: mesh rate, before -> after
    "2.99", "0.5",        # seconds: background removal, before -> after
}

# Broad, generic industry words (EN + JP). A client plaque names the problem
# domain only, never an industry.
INDUSTRY_WORDS = [
    "banking", "bank", "銀行", "insurance", "保険", "retail", "小売",
    "automotive", "自動車", "pharma", "製薬", "telecom", "通信",
    "energy", "エネルギー", "gas", "ガス", "airline", "航空",
    "real estate", "不動産", "manufacturing", "製造", "game", "ゲーム",
    "media", "メディア", "logistics", "物流", "government", "官公庁",
    "hospital", "病院", "finance", "金融", "food", "食品",
    "construction", "建設", "chemical", "化学", "semiconductor", "半導体",
    "railway", "鉄道", "electronics", "電機", "trading company", "商社",
    "staffing", "人材派遣", "apparel", "アパレル", "utility", "電力",
]


def _walk(value):
    """Yield every T reachable from a module-level value."""
    if isinstance(value, T):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _walk(v)
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for f in dataclasses.fields(value):
            yield from _walk(getattr(value, f.name))


def _module_Ts():
    for name, value in vars(content).items():
        if name.startswith("_"):
            continue
        if isinstance(value, T):
            yield name, value
            continue
        if isinstance(value, type) or callable(value):
            continue
        yield from ((name, t) for t in _walk(value))


def _plaque_text(p, lang):
    parts = [p.title(lang), p.subtitle(lang), p.lines(lang), p.years, *p.tags]
    return "\n".join(parts)


def test_kana_name():
    assert HERO["kana"].jp == HERO["kana"].en == "アカシュ・クマァ"


def test_every_T_has_both_languages():
    found = list(_module_Ts())
    assert len(found) > 40
    names = {name for name, _ in found}
    assert {"TOGGLE", "NDA", "HERO", "PLAQUES"} <= names
    for name, t in found:
        assert t.jp.strip(), f"{name}: empty jp in {t!r}"
        assert t.en.strip(), f"{name}: empty en in {t!r}"


def test_T_call_picks_language():
    t = T("日本語", "English")
    assert t("jp") == "日本語"
    assert t("en") == "English"


def _clients():
    clients = [p for p in PLAQUES if p.kind == "client"]
    assert clients
    return clients


def test_client_plaque_numbers_allowlisted():
    for p in _clients():
        for lang in ("jp", "en"):
            for num in re.findall(r"\d+(?:\.\d+)?", _plaque_text(p, lang)):
                assert num in ALLOWED_CLIENT_NUMBERS, f"{p.id}/{lang}: number {num}"


def test_client_plaques_no_industry_words():
    for p in _clients():
        for lang in ("jp", "en"):
            text = _plaque_text(p, lang).lower()
            for word in INDUSTRY_WORDS:
                if word.isascii():
                    hit = re.search(rf"\b{re.escape(word)}\b", text)
                else:
                    hit = word in text
                assert not hit, f"{p.id}/{lang}: industry word {word!r}"


def test_client_plaques_clear_of_denylist():
    raw = os.environ.get("PROFILE_DENYLIST")
    if not raw:
        pytest.skip("PROFILE_DENYLIST not set")
    terms = [t.strip().lower() for t in raw.splitlines() if t.strip()]
    for p in PLAQUES:
        for lang in ("jp", "en"):
            text = _plaque_text(p, lang).lower()
            for term in terms:
                assert term not in text, f"{p.id}/{lang}: deny-listed term"


def test_pending_excluded():
    assert [p.id for p in active_plaques()] == [
        "scout", "marketing", "facilitator", "drone", "phisheye", "whisper",
    ]


def test_plaque_order_and_links():
    assert [p.id for p in PLAQUES] == [
        "scout", "marketing", "facilitator", "drone", "client_a",
        "phisheye", "whisper", "oss_b",
    ]
    by_id = {p.id: p for p in PLAQUES}
    for pid in ("scout", "marketing", "facilitator", "drone"):
        assert by_id[pid].link == "https://sky9262.github.io"
    assert by_id["phisheye"].link == "https://github.com/sky9262/phishEye"
    assert by_id["whisper"].link == "https://huggingface.co/sky9262/whisper-base-japanese-anime"


def test_plaque_line_limits():
    for p in active_plaques():
        jp = p.lines.jp.split("\n")
        en = p.lines.en.split("\n")
        assert 3 <= len(jp) <= 4, f"{p.id}: {len(jp)} jp lines"
        assert 3 <= len(en) <= 4, f"{p.id}: {len(en)} en lines"
        for line in jp:
            assert len(line) <= 34, f"{p.id} jp line too long: {line}"
        for line in en:
            assert len(line) <= 42, f"{p.id} en line too long: {line}"
        assert len(p.tags) <= 4


def test_links_exact():
    assert [(i, u) for i, _, u in LINKS] == [
        ("gmail", "mailto:akash2002.pat@gmail.com"),
        ("linkedin", "https://www.linkedin.com/in/sky9262/"),
        ("x", "https://x.com/sky9262"),
        ("instagram", "https://instagram.com/sky926296"),
        ("portfolio", "https://sky9262.github.io"),
        ("huggingface", "https://huggingface.co/sky9262"),
        ("tryhackme", "https://tryhackme.com/p/sky9262"),
    ]


def test_counts():
    assert len(content.CANDO) == 5
    assert len(content.STACK) == 6
    assert len(content.ACHIEVEMENTS) == 6
    assert set(content.HERO) == {"terminal", "name", "kana", "role", "tagline"}
    assert set(content.CONNECT) == {"heading", "bell", "signoff"}
    assert content.NDA == T("守秘義務によりクライアント名・詳細は非公開", "Client details withheld under NDA")
    assert content.TOGGLE == T("English →", "← 日本語")
