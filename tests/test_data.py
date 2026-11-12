import io
import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.generate import github_data as gd
from scripts.generate.github_data import (
    Data,
    Event,
    FetchError,
    fetch,
    filter_events,
    hour_buckets,
    load_fixture,
)

FIX = Path(__file__).parent / "fixtures" / "github"
NOW = datetime(2026, 11, 12, 6, 0, tzinfo=timezone.utc)


# ---------- fixture parsing ----------


def test_parse_fixture():
    d = load_fixture(FIX)
    assert isinstance(d, Data)
    assert d.login == "sky9262"
    assert len(d.days) == 365
    assert d.days == sorted(d.days)
    assert d.days[-1][0] == date(2026, 11, 12)
    assert d.days[0][0] == date(2025, 11, 13)
    assert d.total_year == sum(c for _, c in d.days)
    assert d.total_year > 0
    # 6 owned non-fork public repos; the fork node in the fixture is dropped
    assert d.public_repos == 6
    assert d.stars == 87 + 2 + 0 + 0 + 0 + 0
    assert d.followers == 29
    assert d.live["sky9262/phishEye"] == (87, 24)
    assert "sky9262/forked-example" not in d.live
    names = [n for n, _, _ in d.languages]
    assert "Go" not in names  # from the fork only
    sizes = [b for _, b, _ in d.languages]
    assert sizes == sorted(sizes, reverse=True)
    assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", c) for _, _, c in d.languages)
    # 17 recorded events, of which 2 PR + 1 member event have no Event kind
    assert len(d.events) == 14
    kinds = {e.kind for e in d.events}
    assert kinds == {"push", "create", "release", "star", "fork"}
    assert all(e.at.tzinfo is not None for e in d.events)
    # commits_*.json: 1 + 4 + 16
    assert len(d.commit_times) == 21
    assert all(t.tzinfo is not None for t in d.commit_times)
    assert d.private_repo_names == ["private-one", "private-two", "private-three", "private-four"]


def test_recent_repos():
    """Own public non-fork repos by most recent push (UTC, newest first) for the feed
    backfill. The profile repo itself is left out: the generator's force-push to the
    output branch bumps its pushedAt every run."""
    d = load_fixture(FIX)
    names = [n for n, _ in d.recent_repos]
    assert names == [
        "sky9262/hermes-run",
        "sky9262/cinematic-glb2particle-skill",
        "sky9262/voice_identify",
        "sky9262/winLock",
        "sky9262/phishEye",
    ]
    times = [t for _, t in d.recent_repos]
    assert times == sorted(times, reverse=True)
    assert all(t.tzinfo is not None and t.utcoffset() == timedelta(0) for t in times)
    assert d.recent_repos[0][1] == datetime(2026, 6, 26, 5, 51, 53, tzinfo=timezone.utc)
    assert "sky9262/forked-example" not in names


def test_recent_repos_default_empty():
    d = Data("x", [], 0, 0, 0, 0, [], [], [], {}, [])
    assert d.recent_repos == []


def test_fixtures_are_anonymised():
    text = "".join(p.read_text() for p in FIX.glob("*.json"))
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    owners = set(re.findall(r'"(?:name|nameWithOwner|full_name)": "([^"/]+)/', text))
    assert owners <= {"sky9262", "example-org"}


# ---------- hour buckets ----------


def test_hour_buckets_jst():
    b = hour_buckets(
        [
            datetime(2026, 1, 1, 20, 30, tzinfo=timezone.utc),  # JST 05:30 -> asa
            datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc),  # JST 11:00 -> hiru
        ]
    )
    assert b == {"asa": 1, "hiru": 1, "yu": 0, "yoru": 0}


def test_hour_buckets_boundaries():
    def at(jst_hour):
        return datetime(2026, 1, 2, jst_hour, 0, tzinfo=timezone(timedelta(hours=9)))

    b = hour_buckets([at(h) for h in range(24)])
    assert b == {"asa": 6, "hiru": 6, "yu": 4, "yoru": 8}
    assert hour_buckets([at(17)])["yu"] == 1
    assert hour_buckets([at(21)])["yoru"] == 1
    assert hour_buckets([at(4)])["yoru"] == 1
    assert hour_buckets([]) == {"asa": 0, "hiru": 0, "yu": 0, "yoru": 0}


# ---------- filter_events ----------


def _ev(kind, repo):
    return Event(kind=kind, repo=repo, at=NOW)


def test_filter_events_drops_foreign_and_denied():
    evs = [
        _ev("push", "example-org/x"),
        _ev("star", "foo/bar"),
        _ev("star", "example-org/y"),
        _ev("push", "sky9262/phishEye"),
    ]
    assert filter_events(evs[:2], "sky9262", []) == [evs[1]]
    out = filter_events(evs, "sky9262", ["example-org"])
    assert out == [evs[1], evs[3]]


def test_filter_events_deny_is_case_insensitive_and_ignores_blanks():
    evs = [_ev("push", "sky9262/Secret-Thing"), _ev("fork", "foo/bar")]
    assert filter_events(evs, "sky9262", ["", "  ", "secret"]) == [evs[1]]
    assert filter_events(evs, "SKY9262", ["\n"]) == evs


# ---------- fetch (urlopen monkeypatched; no network) ----------


class _Resp:
    def __init__(self, payload, status=200):
        self._b = json.dumps(payload).encode()
        self.status = status

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(url, code):
    return urllib.error.HTTPError(url, code, "err", {}, io.BytesIO(b"{}"))


class FakeGitHub:
    """Routes requests to the recorded fixtures; records every call."""

    def __init__(self, overrides=None):
        self.calls = []
        self.overrides = overrides or {}

    def __call__(self, req, timeout=None):
        url = req.full_url
        self.calls.append((req, timeout))
        for key, action in self.overrides.items():
            if key in url:
                return action(req)
        if url.endswith("/graphql"):
            return _Resp(json.loads((FIX / "graphql.json").read_text()))
        if "/events/public" in url:
            return _Resp(json.loads((FIX / "events.json").read_text()))
        if "/user/repos" in url:
            return _Resp(json.loads((FIX / "private_repos.json").read_text()))
        m = re.search(r"/repos/sky9262/([^/]+)/commits", url)
        if m:
            p = FIX / f"commits_{m.group(1)}.json"
            return _Resp(json.loads(p.read_text()) if p.exists() else [])
        raise AssertionError(f"unexpected url {url}")


def test_fetch_matches_fixture(monkeypatch):
    fake = FakeGitHub()
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    d = fetch("tok", now=NOW)
    f = load_fixture(FIX)
    assert d == f
    for req, timeout in fake.calls:
        assert timeout == 20
        assert req.get_header("Authorization") == "Bearer tok"
    urls = [r.full_url for r, _ in fake.calls]
    assert any("/users/sky9262/events/public?per_page=100" in u for u in urls)
    assert any("/user/repos?visibility=private&affiliation=owner&per_page=100" in u for u in urls)
    commit_urls = [u for u in urls if "/commits" in u]
    assert commit_urls and all("author=sky9262" in u and "per_page=100" in u for u in commit_urls)
    assert all("since=2025-11-12T06:00:00Z" in u for u in commit_urls)
    # winLock and phishEye were last pushed > 365 days ago: no commit calls
    assert not any("/winLock/" in u or "/phishEye/" in u for u in commit_urls)
    # the graphql variables carry the 365-day window
    gql = [r for r, _ in fake.calls if r.full_url.endswith("/graphql")][0]
    v = json.loads(gql.data)["variables"]
    assert v["login"] == "sky9262"
    assert v["from"] == "2025-11-12T06:00:00Z" and v["to"] == "2026-11-12T06:00:00Z"


def test_fetch_raises_on_http_error(monkeypatch):
    def boom(req, timeout=None):
        raise _http_error(req.full_url, 502)

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(FetchError):
        fetch("tok", now=NOW)


@pytest.mark.parametrize("code", [403, 404])
def test_fetch_private_repos_forbidden_is_empty(monkeypatch, caplog, code):
    def deny(req):
        raise _http_error(req.full_url, code)

    monkeypatch.setattr(urllib.request, "urlopen", FakeGitHub({"/user/repos": deny}))
    with caplog.at_level("WARNING"):
        d = fetch("tok", now=NOW)
    assert d.private_repo_names == []
    assert d.live["sky9262/phishEye"] == (87, 24)
    assert "private" in caplog.text.lower()
    assert "private-one" not in caplog.text


@pytest.mark.parametrize("code", [401, 500])
def test_fetch_private_repos_other_errors_raise(monkeypatch, code):
    def deny(req):
        raise _http_error(req.full_url, code)

    monkeypatch.setattr(urllib.request, "urlopen", FakeGitHub({"/user/repos": deny}))
    with pytest.raises(FetchError):
        fetch("tok", now=NOW)


@pytest.mark.parametrize("path", ["/events/public", "/commits"])
def test_fetch_404_elsewhere_raises(monkeypatch, path):
    def nf(req):
        raise _http_error(req.full_url, 404)

    monkeypatch.setattr(urllib.request, "urlopen", FakeGitHub({path: nf}))
    with pytest.raises(FetchError):
        fetch("tok", now=NOW)


def test_fetch_raises_on_graphql_errors(monkeypatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        FakeGitHub({"/graphql": lambda r: _Resp({"errors": [{"message": "nope"}], "data": None})}),
    )
    with pytest.raises(FetchError):
        fetch("tok", now=NOW)


@pytest.mark.parametrize(
    "exc", [TimeoutError("timed out"), urllib.error.URLError("unreachable")]
)
def test_fetch_raises_on_timeout_and_urlerror(monkeypatch, exc):
    def boom(req, timeout=None):
        raise exc

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(FetchError):
        fetch("tok", now=NOW)


def test_fetch_commit_loop_is_bounded(monkeypatch):
    nodes = [
        {
            "nameWithOwner": f"sky9262/r{i}",
            "isFork": False,
            "owner": {"login": "sky9262"},
            "stargazerCount": 0,
            "forkCount": 0,
            "pushedAt": "2026-11-01T00:00:00Z",
            "defaultBranchRef": {"name": "main"},
            "languages": {"edges": []},
        }
        for i in range(40)
    ]
    gql = json.loads((FIX / "graphql.json").read_text())
    gql["data"]["user"]["repositories"]["nodes"] = nodes
    page = [{"commit": {"author": {"date": "2026-10-01T00:00:00Z"}}}] * 100
    fake = FakeGitHub(
        {"/graphql": lambda r: _Resp(gql), "/commits": lambda r: _Resp(page)}
    )
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    d = fetch("tok", now=NOW)
    commit_urls = [r.full_url for r, _ in fake.calls if "/commits" in r.full_url]
    assert len(commit_urls) == 30 * 3
    assert len({u.split("/commits")[0] for u in commit_urls}) == 30
    assert {re.search(r"[?&]page=(\d+)", u).group(1) for u in commit_urls} == {"1", "2", "3"}
    assert len(d.commit_times) == 30 * 3 * 100


def test_fetch_skips_empty_repos(monkeypatch):
    gql = json.loads((FIX / "graphql.json").read_text())
    for n in gql["data"]["user"]["repositories"]["nodes"]:
        if n["nameWithOwner"] == "sky9262/voice_identify":
            n["defaultBranchRef"] = None
    fake = FakeGitHub({"/graphql": lambda r: _Resp(gql)})
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    fetch("tok", now=NOW)
    assert not any("/voice_identify/" in r.full_url for r, _ in fake.calls)


def test_fetch_paginates_repositories(monkeypatch):
    full = json.loads((FIX / "graphql.json").read_text())
    nodes = full["data"]["user"]["repositories"]["nodes"]
    p1 = json.loads(json.dumps(full))
    p1["data"]["user"]["repositories"]["nodes"] = nodes[:3]
    p1["data"]["user"]["repositories"]["pageInfo"] = {"hasNextPage": True, "endCursor": "C1"}
    p2 = json.loads(json.dumps(full))
    p2["data"]["user"]["repositories"]["nodes"] = nodes[3:]

    def gql(req):
        after = json.loads(req.data)["variables"].get("after")
        return _Resp(p2 if after == "C1" else p1)

    monkeypatch.setattr(urllib.request, "urlopen", FakeGitHub({"/graphql": gql}))
    assert fetch("tok", now=NOW) == load_fixture(FIX)


def test_module_is_stdlib_only():
    src = Path(gd.__file__).read_text()
    imports = re.findall(r"^\s*(?:from|import)\s+([\w.]+)", src, re.M)
    allowed = {"__future__", "dataclasses", "datetime", "json", "logging", "pathlib",
               "typing", "urllib", "urllib.error", "urllib.parse", "urllib.request",
               "socket", "collections"}
    assert set(imports) <= allowed, set(imports) - allowed
