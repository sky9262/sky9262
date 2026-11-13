import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FILES = {"jp": ROOT / "README.md", "en": ROOT / "README-EN.md"}
OUT = "https://raw.githubusercontent.com/sky9262/sky9262/"
JP_CHARS = re.compile(r"[぀-ヿ一-鿿]")
HERO_SVG = re.compile(r"hero-[a-z]+\.svg$")
LIVE = re.compile(r'(?:src|srcset)="(https://[^"]+)"')


def _read(lang: str) -> str:
    return FILES[lang].read_text(encoding="utf-8")


def _srcs(text: str) -> list[str]:
    return re.findall(r'(?:src|srcset)="([^"]+)"', text)


def test_readme_assets_exist():
    for lang in FILES:
        for s in _srcs(_read(lang)):
            if s.startswith("http"):
                continue
            assert (ROOT / s).exists(), f"{lang}: missing {s}"


def test_readme_output_urls():
    for lang in FILES:
        text = _read(lang)
        live = [u for u in _srcs(text) if u.startswith(OUT)]
        assert live, f"{lang}: no live images"
        branches = {u[len(OUT):].split("/")[0] for u in live}
        assert len(branches) == 1, branches
        assert branches <= {"output", "output-test"}, branches
        assert f"/{lang}/plaque-phisheye.svg" in text
        for name in ("torii-desktop", "torii-phone", "feed-desktop", "feed-phone",
                     "stat-contrib", "stat-month", "stat-peak", "stat-stars",
                     "enso", "hours"):
            assert f"/{lang}/{name}.svg" in text, name


@pytest.mark.parametrize("branch", ["output", "output-test"])
@pytest.mark.parametrize("lang", ["jp", "en"])
def test_render_readme_branch(lang, branch):
    from scripts.build.readme import render_readme

    live = [u for u in _srcs(render_readme(lang, branch)) if u.startswith(OUT)]
    assert live and all(u.startswith(f"{OUT}{branch}/{lang}/") for u in live)


def test_build_deterministic(fonts):
    from scripts.build.subset import subset_woff2
    from scripts.shrine.cards.cando import render_cando
    from conftest import SERIF_DIR

    ttf = SERIF_DIR / "NotoSerifJP-Regular.ttf"
    assert subset_woff2(ttf, "絵馬ABC") == subset_woff2(ttf, "絵馬ABC")
    assert render_cando("jp", "phone", fonts) == render_cando("jp", "phone", fonts)


BLOB = "https://github.com/sky9262/sky9262/blob/"


def _branch(text: str) -> str:
    branches = {u[len(OUT):].split("/")[0] for u in _srcs(text) if u.startswith(OUT)}
    assert len(branches) == 1, branches
    return branches.pop()


def test_readmes_share_one_output_branch():
    """Both READMEs point at the same single output branch (built together)."""
    jp, en = _branch(_read("jp")), _branch(_read("en"))
    assert jp == en, (jp, en)
    assert jp in {"output", "output-test"}


@pytest.mark.parametrize(
    "branch,source", [("output-test", "profile-v2"), ("output", "main")]
)
def test_toggle_href_is_absolute_and_branch_aware(branch, source):
    from scripts.build.readme import render_readme, toggle_href

    assert toggle_href("jp", branch) == f"{BLOB}{source}/README-EN.md"
    assert toggle_href("en", branch) == f"{BLOB}{source}/README.md"
    jp, en = render_readme("jp", branch), render_readme("en", branch)
    assert f'<a href="{BLOB}{source}/README-EN.md">' in jp
    assert f'<a href="{BLOB}{source}/README.md">' in en
    assert "README.md" not in jp.replace("README-EN.md", "")


def test_toggle_links():
    """The committed READMEs' toggles match their output branch."""
    source = {"output-test": "profile-v2", "output": "main"}[_branch(_read("jp"))]
    assert f'href="{BLOB}{source}/README-EN.md"' in _read("jp")
    assert f'href="{BLOB}{source}/README.md"' in _read("en")
    assert "README.md" not in _read("jp").replace("README-EN.md", "")
    for lang in FILES:
        assert 'href="README' not in _read(lang)  # never relative


def test_alt_language():
    for lang in FILES:
        alts = re.findall(r'alt="([^"]*)"', _read(lang))
        assert alts
        for a in alts:
            assert a, "empty alt"
            if lang == "jp":
                assert JP_CHARS.search(a), a
            else:
                assert a.isascii(), a
    for lang in FILES:
        text = _read(lang)
        assert text.count("<img") == len(re.findall(r'<img [^>]*alt="', text))


def test_no_pending_plaques():
    for lang in FILES:
        text = _read(lang)
        assert "client_a" not in text and "oss_b" not in text


def test_structure():
    for lang in FILES:
        text = _read(lang)
        assert text.count('media="(max-width: 600px)"') == 6  # hero, can-do, stack, torii, feed, connect
    assert len(re.findall(r"<picture>", _read("jp"))) == len(
        re.findall(r"<picture>", _read("en"))
    )


def test_assets_budget():
    files = [f for f in (ROOT / "assets").rglob("*") if f.is_file()]
    assert files
    for f in files:
        rel = f.relative_to(ROOT / "assets").as_posix()
        limit = 1536 if re.fullmatch(r"(jp|en)/hero-[a-z]+\.svg", rel) else 500
        assert f.stat().st_size <= limit * 1024, f"{rel}: {f.stat().st_size} B > {limit} KB"


DIVIDER = "assets/common/walker-divider.svg"


@pytest.mark.parametrize("lang", ["jp", "en"])
def test_walker_divider(lang):
    """The walking kitsune strip sits between hero/projects, stack/activity and in the footer."""
    from scripts.build.readme import render_readme
    from scripts.shrine.content import SECTION

    markers = ("hero-desktop.svg", SECTION["projects"](lang), "stack-desktop.svg",
               SECTION["activity"](lang), "btn-gmail.svg")

    for text in (render_readme(lang, "output-test"), _read(lang)):
        assert text.count(f'<img src="{DIVIDER}" width="100%"') == 3
        pos = [m.start() for m in re.finditer(re.escape(DIVIDER), text)]
        hero, projects, stack, activity, connect = (text.index(m) for m in markers)
        assert hero < pos[0] < projects
        assert stack < pos[1] < activity
        assert connect < pos[2]


@pytest.mark.network
def test_github_renders_picture():
    r = subprocess.run(
        ["gh", "api", "markdown", "-f", "mode=gfm", "-F", f"text=@{FILES['jp']}"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert 'media="(max-width: 600px)"' in r.stdout


# ---- owner-kept v2.1 items: greeting, THM/solved.ac badges, footer badges ----
def _amp(u: str) -> str:
    return u.replace("&", "&amp;")


BEAR_URL = "https://static.wikia.nocookie.net/571b16ac-136f-42f4-99eb-173a75d4aa90"
_ANIM_URL = "https://raw.githubusercontent.com/acervenky/animated-github-badges/master/assets"
OWNER_URLS = [
    "https://docs.github.com/en/developers",
    f"{_ANIM_URL}/devbadge.gif",
    "https://github.com/pricing",
    f"{_ANIM_URL}/pro.gif",
    "https://docs.github.com/en/github/supporting-the-open-source-community-with-github-sponsors",
    f"{_ANIM_URL}/sponsorbadge.gif",
    BEAR_URL,
    "https://tryhackme-badges.s3.amazonaws.com/sky9262.png?0",
    "http://mazassumnida.wtf/api/v2/generate_badge?boj=sky9262",
    "https://madewithlove.now.sh/in?heart=true&amp;template=for-the-badge",
    "https://komarev.com/ghpvc/?username=sky9262&amp;label=Profile%20views&amp;color=0e75b6&amp;style=flat",
]
GREETING_LINE = {
    "jp": "いろいろな方とつながるのが大好きです。気軽に<b>こんにちは</b>と声をかけてください。"
          "お会いできるのを楽しみにしています！<b>😊</b>",
    "en": "I love connecting with different people so if you want to say <b>hi</b>, "
          "I'll be happy to meet you more! <b>😊</b>",
}


@pytest.mark.parametrize("lang", ["jp", "en"])
def test_owner_urls_once(lang):
    text = _read(lang)
    for u in OWNER_URLS:
        assert text.count(f'"{u}"') == 1, (lang, u, text.count(f'"{u}"'))
    for u in ("https://tryhackme.com/p/sky9262", "https://solved.ac/sky9262"):
        assert text.count(f'href="{u}"') >= 1
    assert text.count('href="https://tryhackme.com/p/sky9262"') == 2  # THM badge + link button
    assert "api/mini/generate_badge" not in text  # owner removed the small solved.ac badge


@pytest.mark.parametrize("lang", ["jp", "en"])
def test_owner_connect_greeting(lang):
    text = _read(lang)
    card, first_btn = text.index("connect-desktop.svg"), text.index("btn-gmail.svg")
    greeting = text.index(GREETING_LINE[lang])
    assert f"<em>{GREETING_LINE[lang]}</em>" in text
    bear = text.index(BEAR_URL)
    badges = [text.index(u) for u in OWNER_URLS[:6:2]]
    assert card < bear < greeting < min(badges)
    assert max(badges) < first_btn
    assert text.count('width="40" height="40"') == 3
    other = "en" if lang == "jp" else "jp"
    assert GREETING_LINE[other] not in text


@pytest.mark.parametrize("lang", ["jp", "en"])
def test_owner_achievement_badges(lang):
    text = _read(lang)
    last_tablet = text.rindex("achievement-")
    pair = text.index(f"assets/{lang}/hackerrank.svg")
    ctftime = text.index(f"assets/{lang}/ctftime.svg")
    thm = text.index("https://tryhackme-badges.s3.amazonaws.com/sky9262.png?0")
    card = text.index("http://mazassumnida.wtf/api/v2/generate_badge?boj=sky9262")
    assert last_tablet < pair < ctftime < thm < card < text.index("connect-desktop.svg")


@pytest.mark.parametrize("lang", ["jp", "en"])
def test_owner_footer(lang):
    from scripts.shrine.content import CONNECT

    text = _read(lang)
    signoff = text.index(CONNECT["signoff"](lang))
    love = text.index("https://madewithlove.now.sh/")
    views = text.index("https://komarev.com/ghpvc/")
    assert signoff < love < views


@pytest.mark.parametrize("lang", ["jp", "en"])
def test_owner_html_whitelist(lang):
    tags = set(re.findall(r"</?([a-zA-Z0-9]+)", _read(lang)))
    assert tags <= {"p", "a", "img", "em", "b", "picture", "source", "sub", "h2", "h3"}, tags
    assert not re.search(r'<[^>]*\s(style|class)=', _read(lang))


# ---- owner edit 5: HackerRank shrine tablet ----
HR_URL = "https://www.hackerrank.com/profile/sky9262"


@pytest.mark.parametrize("lang", ["jp", "en"])
def test_hackerrank_tablet_placement(lang):
    text = _read(lang)
    img = f'src="assets/{lang}/hackerrank.svg"'
    assert text.count(img) == 1
    assert text.count(f'href="{HR_URL}"') == 1
    m = re.search(rf'<a href="{re.escape(HR_URL)}"><img {img} width="410" alt="([^"]+)"></a>', text)
    assert m, "HackerRank tablet must be a linked 410-wide image"
    if lang == "jp":
        assert JP_CHARS.search(m.group(1))
    else:
        assert not JP_CHARS.search(m.group(1))
    last_tablet = text.rindex("achievement-")
    hr = text.index(img)
    thm = text.index("https://tryhackme-badges.s3.amazonaws.com/sky9262.png?0")
    assert last_tablet < hr < thm
    # its own centred paragraph, ready for a second 410-wide tablet beside it
    para = text[text.rindex("<p", 0, hr):text.index("</p>", hr)]
    assert para.startswith('<p align="center">') and "achievement-" not in para


def test_extra_tablets_pair():
    """HackerRank and picoCTF sit side by side in one centred paragraph."""
    from scripts.build import readme

    assert [name for _, name, _ in readme.EXTRA_TABLETS] == ["hackerrank", "picoctf"]
    out = readme.tablet_rows(readme.EXTRA_TABLETS, "en")
    assert len(out) == 1 and out[0].count("<img ") == 2


# ---- owner edit 6: picoCTF tablet beside HackerRank ----
@pytest.mark.parametrize("lang", ["jp", "en"])
def test_picoctf_pairs_with_hackerrank(lang):
    text = _read(lang)
    hr = text.index(f'src="assets/{lang}/hackerrank.svg"')
    pico = text.index(f'src="assets/{lang}/picoctf.svg"')
    para = text[text.rindex("<p", 0, hr):text.index("</p>", hr)]
    assert f'<a href="https://picoctf.org"><img src="assets/{lang}/picoctf.svg" width="410" alt="' in para
    assert hr < pico
    assert text.count('href="https://picoctf.org"') == 1


# ---- owner edit 7: CTFtime team tablet, alone in its row after the pair ----
@pytest.mark.parametrize("lang", ["jp", "en"])
def test_ctftime_tablet_row(lang):
    text = _read(lang)
    url = "https://ctftime.org/team/75661"
    img = f'<img src="assets/{lang}/ctftime.svg" width="410" alt="'
    assert text.count(f'href="{url}"') == 1
    assert f'<a href="{url}">{img}' in text
    pos = text.index(img)
    para = text[text.rindex("<p", 0, pos):text.index("</p>", pos)]
    assert para.startswith('<p align="center">') and para.count("<img ") == 1
    assert text.index("picoctf.svg") < pos
    alt = re.search(re.escape(img) + r'([^"]+)"', text).group(1)
    assert "warlock_rootx" in alt
