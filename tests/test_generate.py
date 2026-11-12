"""Task 12: privacy check and the generator CLI (python -m scripts.generate)."""
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from helpers import assert_no_external, assert_under, assert_valid_svg
from scripts.generate import __main__ as gen
from scripts.generate.github_data import FetchError, load_fixture
from scripts.generate.privacy import PrivacyError, check, mask, parse_denylist
from scripts.shrine.svg import visible_strings

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "github"
NAMES = (
    "torii-desktop", "torii-phone", "feed-desktop", "feed-phone",
    "stat-contrib", "stat-streak", "stat-stars", "stat-followers",
    "enso", "hours", "plaque-phisheye",
)
NOW = "2026-11-12T00:00Z"


def _svg(body: str, style: str = "") -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        f"<title>card</title><style>{style}</style>{body}</svg>"
    )


def _tree(d: Path) -> list[str]:
    return sorted(str(p.relative_to(d)) for p in d.rglob("*"))


PREV = ["out", "out/.shrine-output", "out/keep.txt"]


def _prev_out(tmp_path: Path) -> Path:
    """An earlier generator output: marker + a file we can watch."""
    out = tmp_path / "out"
    out.mkdir()
    (out / ".shrine-output").write_text("x")
    (out / "keep.txt").write_text("old")
    return out


# ---------------------------------------------------------------- privacy.check


def test_privacy_catches_private_name():
    with pytest.raises(PrivacyError) as ei:
        check({"jp/feed.svg": _svg("<text>pushed to private-one</text>")}, ["private-one"], [])
    assert "jp/feed.svg" in str(ei.value)
    assert "private-one" not in str(ei.value)


def test_privacy_private_name_is_case_insensitive_in_title_and_aria():
    with pytest.raises(PrivacyError):
        check({"a.svg": _svg("<g aria-label='Private-One'/>")}, ["private-one"], [])
    with pytest.raises(PrivacyError):
        check({"a.svg": _svg("<text>sky9262/PRIVATE-ONE</text>")}, ["private-one"], [])


def test_privacy_private_name_word_boundaries():
    # longer names that merely contain the private name are different repos
    svgs = {"a.svg": _svg("<text>my-private-one private-ones private_one2</text>")}
    check(svgs, ["private-one", "private_one"], [])


def test_privacy_catches_name_split_across_text_nodes():
    # the feed breaks long repo names over several <text> lines after '-', '_', '.'
    svg = _svg('<text>sky9262/</text><text>secret-client-</text><text>portal</text><text>12d ago</text>')
    with pytest.raises(PrivacyError):
        check({"a.svg": svg}, ["secret-client-portal"], [])
    with pytest.raises(PrivacyError):
        check({"a.svg": svg}, [], ["client-portal"])


def test_privacy_catches_hard_cut_name():
    svg = _svg("<text>averyveryveryl</text><text>ongreponame</text>")
    with pytest.raises(PrivacyError):
        check({"a.svg": svg}, ["averyveryverylongreponame"], [])


def test_privacy_catches_truncated_name_and_term():
    # fit(repo, 28) keeps 27 characters + an ellipsis
    svg = _svg("<text>sky9262/</text><text>megacorp-internal-po…</text>")
    with pytest.raises(PrivacyError):
        check({"a.svg": svg}, ["megacorp-internal-portal-v2"], [])
    with pytest.raises(PrivacyError):
        check({"a.svg": _svg("<text>example/Megaco…</text>")}, [], ["MegaCorporation"])


def test_privacy_catches_deny_jp():
    term = "テスト社"
    with pytest.raises(PrivacyError) as ei:
        check({"en/hours.svg": _svg(f"<text>案件: {term}の仕事</text>")}, [], [term])
    msg = str(ei.value)
    assert term not in msg
    assert "en/hours.svg" in msg
    assert mask(term) in msg


def test_privacy_deny_is_case_insensitive_substring():
    with pytest.raises(PrivacyError):
        check({"a.svg": _svg("<text>worked at megacorpinc</text>")}, [], ["MegaCorp"])


def test_privacy_ignores_base64_and_css():
    svg = _svg(
        '<image href="data:image/png;base64,private-one=="/>'
        '<image xlink:href="data:text/plain,MegaCorp"/>',
        style=".private-one{fill:red} /* MegaCorp */",
    )
    check({"a.svg": svg}, ["private-one"], ["MegaCorp"])


def test_privacy_blank_terms_ignored():
    check({"a.svg": _svg("<text>hello</text>")}, ["", "  "], ["", "   "])


def test_mask():
    assert mask("MegaCorp") == "M***"
    assert mask("テスト社") == "テ***"


def test_parse_denylist():
    raw = "  MegaCorp \n\n# a comment\nテスト社\r\n   \n  #indented comment\nmc\n"
    assert parse_denylist(raw) == ["MegaCorp", "テスト社", "mc"]
    assert parse_denylist("") == []
    assert parse_denylist(None) == []


# ---------------------------------------------------------------- CLI helpers


@pytest.fixture
def env(monkeypatch):
    monkeypatch.delenv("PROFILE_TOKEN", raising=False)
    monkeypatch.setenv("PROFILE_DENYLIST", "")
    return monkeypatch


def _run(tmp_path, *extra, fixtures=True):
    out = tmp_path / "out"
    argv = ["--out", str(out), "--now", NOW, *extra]
    if fixtures:
        argv += ["--fixtures", str(FIX)]
    return gen.main(argv), out


def _all_visible(out: Path) -> str:
    return "\n".join(visible_strings(p.read_text(encoding="utf-8")) for p in out.rglob("*.svg"))


def test_parse_now():
    assert gen.parse_now(NOW) == datetime(2026, 11, 12, tzinfo=timezone.utc)
    assert gen.parse_now("2026-11-12T09:00+09:00") == datetime(2026, 11, 12, tzinfo=timezone.utc)
    assert gen.parse_now("2026-11-12T00:00") == datetime(2026, 11, 12, tzinfo=timezone.utc)


def test_main_fixture_run(tmp_path, env, capsys):
    code, out = _run(tmp_path)
    assert code == 0
    expect = sorted(f"{lang}/{n}.svg" for lang in ("jp", "en") for n in NAMES)
    assert sorted(str(p.relative_to(out)) for p in out.rglob("*.svg")) == expect
    assert _tree(out) == sorted(expect + ["jp", "en", ".shrine-output"])
    for rel in expect:
        svg = (out / rel).read_text(encoding="utf-8")
        assert_valid_svg(svg)
        assert_no_external(svg)
        assert_under(svg)
    # nothing left next to --out (temp/backup dirs)
    assert _tree(tmp_path) == ["out"] + [f"out/{p}" for p in _tree(out)]
    assert capsys.readouterr().out.strip() == "generated 22 files"


def test_main_feed_uses_now_override(tmp_path, env):
    code, out = _run(tmp_path)
    assert code == 0
    feed = visible_strings((out / "en" / "feed-desktop.svg").read_text(encoding="utf-8"))
    # phishEye release at 2026-10-29T12:00Z is 13 days before --now
    assert "13d ago" in feed


def test_main_phisheye_plaque_has_live_numbers_and_wave_index(tmp_path, env, monkeypatch):
    from scripts.shrine import content

    calls = []
    real = gen.render_plaque

    def spy(p, lang, index, fonts, stars=None, forks=None):
        calls.append((p.id, lang, index, stars, forks))
        return real(p, lang, index, fonts, stars=stars, forks=forks)

    monkeypatch.setattr(gen, "render_plaque", spy)
    code, _ = _run(tmp_path)
    assert code == 0
    idx = [p.id for p in content.active_plaques()].index("phisheye")
    assert calls == [("phisheye", "jp", idx, 87, 24), ("phisheye", "en", idx, 87, 24)]


def test_main_fails_when_phisheye_live_missing(tmp_path, env, monkeypatch):
    def no_live(d):
        data = load_fixture(d)
        data.live.pop("sky9262/phishEye")
        return data

    monkeypatch.setattr(gen, "load_fixture", no_live)
    _prev_out(tmp_path)
    code, out = _run(tmp_path)
    assert code == 1
    assert _tree(tmp_path) == PREV


def test_main_writes_nothing_on_fetch_error(tmp_path, env, monkeypatch, capsys):
    env.setenv("PROFILE_TOKEN", "ghp_secret_value_123")

    def boom(token, login="sky9262", now=None):
        raise FetchError("HTTP 502 on /graphql", 502)

    monkeypatch.setattr(gen, "fetch", boom)
    _prev_out(tmp_path)
    code, out = _run(tmp_path, fixtures=False)
    assert code == 1
    assert _tree(tmp_path) == PREV
    assert (out / "keep.txt").read_text() == "old"
    cap = capsys.readouterr()
    assert "FetchError" in cap.err
    assert "ghp_secret_value_123" not in cap.out + cap.err


def test_main_fetch_receives_token_and_now(tmp_path, env, monkeypatch):
    env.setenv("PROFILE_TOKEN", "tok")
    seen = {}

    def fake(token, login="sky9262", now=None):
        seen.update(token=token, login=login, now=now)
        return load_fixture(FIX)

    monkeypatch.setattr(gen, "fetch", fake)
    code, _ = _run(tmp_path, fixtures=False)
    assert code == 0
    assert seen == {"token": "tok", "login": "sky9262", "now": datetime(2026, 11, 12, tzinfo=timezone.utc)}


def test_main_blocks_on_privacy(tmp_path, env, capsys):
    # a feed label, not part of any repo name, so filter_events cannot remove it
    term = "Released"
    env.setenv("PROFILE_DENYLIST", f"# comment\n\n{term}\n")
    _prev_out(tmp_path)
    code, out = _run(tmp_path)
    assert code == 1
    assert _tree(tmp_path) == PREV
    cap = capsys.readouterr()
    assert "PrivacyError" in cap.err
    assert "en/feed-desktop.svg" in cap.err and "R***" in cap.err
    assert term not in cap.out + cap.err


def test_privacy_term_never_printed_jp(tmp_path, env, capsys):
    term = "最近の活動"  # part of the JP feed title
    env.setenv("PROFILE_DENYLIST", term)
    code, _ = _run(tmp_path)
    assert code == 1
    cap = capsys.readouterr()
    assert term not in cap.out + cap.err
    assert "最***" in cap.err


def test_main_filters_events_and_recent_repos_before_render(tmp_path, env, monkeypatch):
    def with_private(d):
        data = load_fixture(d)
        data.private_repo_names += ["voice_identify", "hermes-run"]
        return data

    monkeypatch.setattr(gen, "load_fixture", with_private)
    env.setenv("PROFILE_DENYLIST", "example-org")
    code, out = _run(tmp_path)
    assert code == 0, "filtered names must not reach the cards"
    text = _all_visible(out).lower()
    for gone in ("voice_identify", "hermes-run", "example-org", "starred-repo", "forked-repo"):
        assert gone not in text
    # the backfill still shows a remaining public repo
    assert "cinematic-" in text


def test_main_succeeds_with_deny_term_only_in_dropped_events(tmp_path, env):
    env.setenv("PROFILE_DENYLIST", "voice")
    code, out = _run(tmp_path)
    assert code == 0
    assert "voice" not in _all_visible(out).lower()


def test_main_replaces_existing_out(tmp_path, env):
    out = tmp_path / "out"
    (out / "jp").mkdir(parents=True)
    (out / "stale.svg").write_text("x")
    (out / ".shrine-output").write_text("x")
    (out / "jp" / "old.svg").write_text("x")
    code, _ = _run(tmp_path)
    assert code == 0
    assert not (out / "stale.svg").exists() and not (out / "jp" / "old.svg").exists()
    assert len(list(out.rglob("*.svg"))) == 22
    assert sorted(p.name for p in tmp_path.iterdir()) == ["out"]


def test_main_missing_token_exits_2(tmp_path, env, capsys):
    env.setenv("PROFILE_DENYLIST", "SecretCorpName")
    code, out = _run(tmp_path, fixtures=False)
    assert code == 2
    assert not out.exists()
    cap = capsys.readouterr()
    assert "PROFILE_TOKEN" in cap.err
    assert "SecretCorpName" not in cap.out + cap.err


def test_main_empty_token_exits_2(tmp_path, env):
    env.setenv("PROFILE_TOKEN", "   ")
    code, _ = _run(tmp_path, fixtures=False)
    assert code == 2


def test_main_unexpected_error_message_is_scrubbed(tmp_path, env, monkeypatch, capsys):
    env.setenv("PROFILE_DENYLIST", "MegaCorp")

    def explode(*a, **k):
        raise ValueError("cannot fit 'MegaCorp-internal' and private-one")

    monkeypatch.setattr(gen, "render_enso", explode)
    code, _ = _run(tmp_path)
    assert code == 1
    err = capsys.readouterr().err
    assert "ValueError" in err
    assert "MegaCorp" not in err and "megacorp" not in err.lower()
    assert "private-one" not in err
    assert not (tmp_path / "out").exists()
    assert list(tmp_path.iterdir()) == []


def test_main_kitsune_sheet_passed_when_present(tmp_path, env, monkeypatch):
    seen = []
    real = gen.render_torii_path

    def spy(data, lang, layout, fonts, kitsune_png=None):
        seen.append(kitsune_png)
        return real(data, lang, layout, fonts, kitsune_png=None)

    monkeypatch.setattr(gen, "render_torii_path", spy)
    sheet = tmp_path / "kitsune-sheet.png"
    monkeypatch.setattr(gen, "KITSUNE", sheet)
    code, _ = _run(tmp_path)
    assert code == 0 and seen == [None] * 4
    seen.clear()
    sheet.write_bytes(b"\x89PNG fake")
    code, _ = _run(tmp_path)
    assert code == 0 and seen == [b"\x89PNG fake"] * 4


def test_generate_stdlib_only(tmp_path):
    """The Action runs without fontTools or any third-party package."""
    out = tmp_path / "o"
    code = (
        "import sys; sys.modules['fontTools'] = None\n"
        "before = set(sys.modules)\n"
        "from scripts.generate import __main__ as g\n"
        f"rc = g.main(['--fixtures', 'tests/fixtures/github', '--now', '{NOW}', '--out', {str(out)!r}])\n"
        "assert rc == 0, rc\n"
        "new = {m.split('.')[0] for m in set(sys.modules) - before if sys.modules[m] is not None}\n"
        "third = sorted(new - set(sys.stdlib_module_names) - {'scripts'})\n"
        "assert not third, third\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "PROFILE_DENYLIST": ""},
    )
    assert r.returncode == 0, r.stderr
    assert len(list(out.rglob("*.svg"))) == 22


def test_module_entrypoint_missing_token(tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "scripts.generate", "--out", str(tmp_path / "o")],
        cwd=ROOT, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"},
    )
    assert r.returncode == 2
    assert not (tmp_path / "o").exists()


# ---------------------------------------------------------------- fix round 1

from scripts.generate.privacy import scrub  # noqa: E402

SVGS = {"jp/a.svg": _svg("<text>hello</text>")}


def test_privacy_raw_pass_catches_private_name_in_markup():
    for body in (
        '<g id="private-one"/>',
        '<g class="x Private-One"/>',
        '<g data-repo="sky9262/private-one"/>',
        "<!-- private-one --><g/>",
    ):
        with pytest.raises(PrivacyError) as ei:
            check({"a.svg": _svg(body)}, ["private-one"], [])
        assert "private-one" not in str(ei.value).lower()


def test_privacy_raw_pass_skips_deny_terms_and_payloads():
    # deny substrings are not run over markup: hex colours / path data would trip them
    check({"a.svg": _svg('<path d="M10 10" fill="#abcdef"/><g id="cafe"/>')}, [], ["abcdef", "cafe"])
    # style blocks and data: URIs stay excluded in the raw pass too
    svg = _svg('<image href="data:image/png;base64,AAprivate-one=="/>', style="#private-one{}")
    check({"a.svg": svg}, ["private-one"], [])


def test_scrub_masks_fullwidth_variants():
    msg = scrub("failed on ＭｅｇａＣｏｒｐ and ｐｒｉｖａｔｅ－ｏｎｅ", ["private-one"], ["MegaCorp"])
    assert "megacorp" not in msg.lower() and "ＭｅｇａＣｏｒｐ" not in msg
    assert "private-one" not in msg and "ｐｒｉｖａｔｅ" not in msg
    assert "M***" in msg and "p***" in msg


def test_scrub_backslash_term():
    assert scrub(r"bad \qterm here", [], [r"\qterm"]) == r"bad \*** here"


def test_short_deny_terms_warn_by_count_only(tmp_path, env, capsys):
    env.setenv("PROFILE_DENYLIST", "qz\n本社\nLongEnoughTerm")
    code, _ = _run(tmp_path)
    assert code == 0
    err = capsys.readouterr().err
    assert "warning: 2 deny-list terms shorter than 3 characters" in err
    for t in ("qz", "本社", "LongEnoughTerm"):
        assert t not in err


def test_swap_interrupt_after_first_rename_restores_out(tmp_path, monkeypatch):
    out = _prev_out(tmp_path)
    real = os.replace
    calls = []

    def flaky(a, b):
        calls.append((a, b))
        real(a, b)
        if len(calls) == 1:  # out -> backup done, then the runner is killed
            raise KeyboardInterrupt

    monkeypatch.setattr(gen.os, "replace", flaky)
    with pytest.raises(KeyboardInterrupt):
        gen.write_atomic(SVGS, out, [], [])
    assert _tree(tmp_path) == PREV


def test_swap_second_rename_failure_restores_out(tmp_path, monkeypatch):
    out = _prev_out(tmp_path)
    real = os.replace
    calls = []

    def flaky(a, b):
        calls.append((a, b))
        if len(calls) == 2:  # tmp -> out
            raise OSError("disk full")
        real(a, b)

    monkeypatch.setattr(gen.os, "replace", flaky)
    with pytest.raises(OSError):
        gen.write_atomic(SVGS, out, [], [])
    assert _tree(tmp_path) == PREV


def _orphan(tmp_path: Path) -> Path:
    bak = tmp_path / ".out.bak-abc123"
    bak.mkdir()
    (bak / ".shrine-output").write_text("x")
    (bak / "keep.txt").write_text("old")
    return bak


def test_orphaned_backup_recovered_on_next_run(tmp_path, env):
    _orphan(tmp_path)
    code, out = _run(tmp_path)
    assert code == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["out"]
    assert len(list(out.rglob("*.svg"))) == 22


def test_orphaned_backup_recovered_even_when_run_fails(tmp_path, env, monkeypatch):
    _orphan(tmp_path)
    monkeypatch.setattr(gen, "render_enso", lambda *a, **k: 1 / 0)
    code, _ = _run(tmp_path)
    assert code == 1
    assert _tree(tmp_path) == PREV


def test_orphan_not_recovered_when_ambiguous(tmp_path):
    _orphan(tmp_path)
    (tmp_path / ".out.bak-zzz").mkdir()
    gen.recover_orphan(tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_out_with_foreign_files_is_refused(tmp_path, env, capsys):
    out = tmp_path / "out"
    (out / "sub").mkdir(parents=True)
    (out / "precious.txt").write_text("mine")
    (out / "sub" / "x.txt").write_text("mine")
    before = _tree(tmp_path)
    code, _ = _run(tmp_path)
    assert code == 1
    assert _tree(tmp_path) == before
    assert (out / "precious.txt").read_text() == "mine"
    assert "--out" in capsys.readouterr().err


def test_out_that_is_a_file_is_refused(tmp_path, env):
    (tmp_path / "out").write_text("mine")
    code, _ = _run(tmp_path)
    assert code == 1
    assert (tmp_path / "out").read_text() == "mine"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["out"]


def test_out_dot_in_foreign_dir_is_refused(tmp_path, env, monkeypatch):
    (tmp_path / "precious.txt").write_text("mine")
    monkeypatch.chdir(tmp_path)
    assert gen.main(["--out", ".", "--fixtures", str(FIX), "--now", NOW]) == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["precious.txt"]


def test_empty_out_dir_is_accepted(tmp_path, env):
    (tmp_path / "out").mkdir()
    code, out = _run(tmp_path)
    assert code == 0 and (out / ".shrine-output").is_file()


def test_interrupt_while_scrubbing_prints_type_only(tmp_path, env, monkeypatch, capsys):
    env.setenv("PROFILE_DENYLIST", "MegaCorp")

    def explode(*a, **k):
        raise ValueError("MegaCorp leaked")

    def interrupted(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(gen, "render_enso", explode)
    monkeypatch.setattr(gen, "scrub", interrupted)
    code, _ = _run(tmp_path)
    assert code == 1
    err = capsys.readouterr().err
    assert "error: ValueError" in err
    assert "MegaCorp" not in err


def test_main_keyboard_interrupt_returns_1(tmp_path, env, monkeypatch, capsys):
    def interrupted(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(gen, "render_hours", interrupted)
    code, _ = _run(tmp_path)
    assert code == 1
    assert "error: KeyboardInterrupt" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_entry_never_prints_a_traceback(monkeypatch, capsys):
    class Exited(BaseException):
        pass

    def boom(argv=None):
        raise ValueError("MegaCorp leaked")

    def fake_exit(code):
        raise Exited(code)

    monkeypatch.setattr(gen, "main", boom)
    monkeypatch.setattr(gen.os, "_exit", fake_exit)
    with pytest.raises(Exited) as ei:
        gen.entry()
    assert ei.value.args == (1,)
    err = capsys.readouterr().err
    assert err.strip() == "error: ValueError"
