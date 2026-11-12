"""GitHub data layer for the live cards (stdlib only).

Privacy: only public data is parsed into cards. Private repos are fetched by
*name only*, so the generator can refuse to emit them; private activity enters
only as anonymous counts in the contributions calendar. Nothing in this module
logs repo names, response bodies or the token.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

log = logging.getLogger(__name__)

API = "https://api.github.com"
TIMEOUT = 20
PER_PAGE = 100
MAX_COMMIT_REPOS = 30
MAX_COMMIT_PAGES = 3
MAX_PAGES = 10  # safety bound for repo / private-repo pagination
WINDOW = timedelta(days=365)
JST = timezone(timedelta(hours=9))
DEFAULT_COLOR = "#8B8B8B"  # GitHub returns null colour for some languages

Kind = Literal["push", "create", "release", "star", "fork"]
_KINDS: dict[str, Kind] = {
    "PushEvent": "push",
    "CreateEvent": "create",
    "ReleaseEvent": "release",
    "WatchEvent": "star",
    "ForkEvent": "fork",
}

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!, $after: String) {
  user(login: $login) {
    login
    followers { totalCount }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false,
                 privacy: PUBLIC, orderBy: {field: PUSHED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        nameWithOwner
        isFork
        owner { login }
        stargazerCount
        forkCount
        pushedAt
        defaultBranchRef { name }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


class FetchError(RuntimeError):
    """Any failed GitHub request: non-2xx, timeout, network error, GraphQL errors."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass
class Event:
    kind: Kind
    repo: str  # owner/name
    at: datetime  # UTC


@dataclass
class Data:
    login: str
    days: list[tuple[date, int]]
    total_year: int
    public_repos: int
    stars: int
    followers: int
    languages: list[tuple[str, int, str]]
    events: list[Event]
    commit_times: list[datetime]
    live: dict[str, tuple[int, int]]
    private_repo_names: list[str]
    # own public non-fork repos as (full_name, pushed_at UTC), newest first. Since
    # owner edit 3 no card renders these; kept as data, never shown
    recent_repos: list[tuple[str, datetime]] = field(default_factory=list)


# ---------------------------------------------------------------- parsing


def _ts(s: str) -> datetime:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)


def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _owned_repos(nodes: list[dict], login: str) -> list[dict]:
    return [
        n
        for n in nodes
        if not n.get("isFork") and n["owner"]["login"].lower() == login.lower()
    ]


def _parse(
    user: dict,
    repo_nodes: list[dict],
    events: list[dict],
    commits: list[dict],
    private: list[dict],
    login: str,
    today: date | None = None,
) -> Data:
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = sorted(
        (date.fromisoformat(d["date"]), int(d["contributionCount"]))
        for w in cal["weeks"]
        for d in w["contributionDays"]
    )
    if today is not None:
        days = [d for d in days if d[0] <= today]
    days = days[-365:]

    repos = _owned_repos(repo_nodes, login)
    langs: dict[str, list] = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            entry = langs.setdefault(name, [0, e["node"].get("color") or DEFAULT_COLOR])
            entry[0] += int(e["size"])
    languages = sorted(
        ((n, b, c) for n, (b, c) in langs.items()), key=lambda x: (-x[1], x[0])
    )

    # The profile repo is left out: the generator force-pushes the output branch
    # there every run, so its pushedAt says nothing about the owner's work.
    recent = sorted(
        (
            (r["nameWithOwner"], _ts(r["pushedAt"]))
            for r in repos
            if r.get("pushedAt") and r["nameWithOwner"].lower() != f"{login}/{login}".lower()
        ),
        key=lambda x: (x[1], x[0]),
        reverse=True,
    )

    evs = [
        Event(kind=_KINDS[e["type"]], repo=e["repo"]["name"], at=_ts(e["created_at"]))
        for e in events
        if e.get("type") in _KINDS
    ]

    return Data(
        login=user["login"],
        days=days,
        total_year=sum(c for _, c in days),
        public_repos=len(repos),
        stars=sum(int(r["stargazerCount"]) for r in repos),
        followers=int(user["followers"]["totalCount"]),
        languages=languages,
        events=evs,
        commit_times=sorted(_ts(c["commit"]["author"]["date"]) for c in commits),
        live={
            r["nameWithOwner"]: (int(r["stargazerCount"]), int(r["forkCount"]))
            for r in repos
        },
        private_repo_names=[p["name"] for p in private],
        recent_repos=recent,
    )


def load_fixture(dir: Path) -> Data:
    """Parse recorded API responses (same shapes as `fetch` receives)."""
    dir = Path(dir)
    gql = json.loads((dir / "graphql.json").read_text())
    user = gql["data"]["user"]
    commits: list[dict] = []
    for p in sorted(dir.glob("commits_*.json")):
        commits += json.loads(p.read_text())
    return _parse(
        user,
        user["repositories"]["nodes"],
        json.loads((dir / "events.json").read_text()),
        commits,
        json.loads((dir / "private_repos.json").read_text()),
        login=user["login"],
    )


# ---------------------------------------------------------------- network


def _request(token: str, url: str, body: dict | None = None) -> object:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method="POST" if data is not None else "GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "profile-readme-generator",
            **({"Content-Type": "application/json"} if data is not None else {}),
        },
    )
    path = urllib.parse.urlsplit(url).path
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status = getattr(resp, "status", 200)
            if not 200 <= status < 300:
                raise FetchError(f"HTTP {status} on {path}", status)
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} on {path}", e.code) from None
    except urllib.error.URLError as e:
        raise FetchError(f"network error on {path}: {type(e.reason).__name__}") from None
    except (TimeoutError, OSError) as e:
        raise FetchError(f"timeout/socket error on {path}: {type(e).__name__}") from None
    try:
        return json.loads(raw)
    except ValueError:
        raise FetchError(f"invalid JSON from {path}") from None


def _graphql(token: str, variables: dict) -> dict:
    out = _request(token, f"{API}/graphql", {"query": QUERY, "variables": variables})
    if not isinstance(out, dict) or out.get("errors") or not out.get("data"):
        raise FetchError("GraphQL returned errors")
    if out["data"].get("user") is None:
        raise FetchError("GraphQL returned no user")
    return out["data"]["user"]


def _private_repo_names(token: str) -> list[dict]:
    """Owner's private repos (names only). A metadata-only fine-grained token may be
    refused here (403/404); that degrades to an empty list, never to a crash."""
    out: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        url = (
            f"{API}/user/repos?visibility=private&affiliation=owner"
            f"&per_page={PER_PAGE}&page={page}"
        )
        try:
            batch = _request(token, url)
        except FetchError as e:
            if e.status in (403, 404):
                log.warning(
                    "private repo list unavailable to this token; "
                    "the private-name check falls back to the deny-list only"
                )
                return []
            raise
        out += [{"name": r["name"]} for r in batch]
        if len(batch) < PER_PAGE:
            break
    return out


def fetch(token: str, login: str = "sky9262", now: datetime | None = None) -> Data:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    since = now - WINDOW

    user: dict | None = None
    nodes: list[dict] = []
    after = None
    for _ in range(MAX_PAGES):
        u = _graphql(
            token,
            {"login": login, "from": _iso(since), "to": _iso(now), "after": after},
        )
        user = user or u
        nodes += u["repositories"]["nodes"]
        info = u["repositories"]["pageInfo"]
        if not info["hasNextPage"]:
            break
        after = info["endCursor"]
    assert user is not None

    events = _request(token, f"{API}/users/{login}/events/public?per_page={PER_PAGE}")

    recent = [
        r
        for r in _owned_repos(nodes, login)
        if r.get("defaultBranchRef") and r.get("pushedAt") and _ts(r["pushedAt"]) >= since
    ][:MAX_COMMIT_REPOS]
    commits: list[dict] = []
    for r in recent:
        owner, name = r["nameWithOwner"].split("/", 1)
        for page in range(1, MAX_COMMIT_PAGES + 1):
            q = urllib.parse.urlencode(
                {"author": login, "since": _iso(since), "per_page": PER_PAGE, "page": page},
                safe=":",
            )
            batch = _request(
                token,
                f"{API}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/commits?{q}",
            )
            commits += batch
            if len(batch) < PER_PAGE:
                break

    private = _private_repo_names(token)
    return _parse(user, nodes, events, commits, private, login, today=now.date())


# ---------------------------------------------------------------- helpers


def hour_buckets(times: list[datetime]) -> dict[str, int]:
    """JST buckets, start-inclusive: asa 05-11, hiru 11-17, yu 17-21, yoru 21-05.
    Naive datetimes are taken as UTC."""
    out = {"asa": 0, "hiru": 0, "yu": 0, "yoru": 0}
    for t in times:
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        h = t.astimezone(JST).hour
        if 5 <= h < 11:
            out["asa"] += 1
        elif 11 <= h < 17:
            out["hiru"] += 1
        elif 17 <= h < 21:
            out["yu"] += 1
        else:
            out["yoru"] += 1
    return out


def filter_events(events: list[Event], login: str, deny: list[str]) -> list[Event]:
    """Keep star/fork on any repo and other kinds only on `login`'s own repos; then
    drop any event whose repo contains a deny term (case-insensitive, blanks ignored)."""
    terms = [t.strip().lower() for t in deny if t and t.strip()]
    me = login.lower()
    out = []
    for e in events:
        if e.kind not in ("star", "fork") and e.repo.split("/", 1)[0].lower() != me:
            continue
        if any(t in e.repo.lower() for t in terms):
            continue
        out.append(e)
    return out
