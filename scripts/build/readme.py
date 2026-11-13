"""README.md (Japanese) and README-EN.md (English) generators."""
from __future__ import annotations

from scripts.shrine.content import (
    ACHIEVEMENTS, HACKERRANK, HACKERRANK_URL, LINKS, PICOCTF, SECTION, TOGGLE, CONNECT, Lang, active_plaques,
)

RAW = "https://raw.githubusercontent.com/sky9262/sky9262"
BLOB = "https://github.com/sky9262/sky9262/blob"
FILE = {"jp": "README.md", "en": "README-EN.md"}
# the source branch whose READMEs the toggle opens: the test build lives on
# profile-v2 until go-live, when the `output` build is committed to main
SOURCE_BRANCH = {"output": "main", "output-test": "profile-v2"}

# alt text per image, in the README's language
ALT: dict[str, dict[str, str]] = {
    "hero": {"jp": "夜の神社 アカシュ・クマァ（Akash Kumar）のプロフィール",
             "en": "Akash Kumar, AI and Security Engineer: night shrine profile banner"},
    "cando": {"jp": "我が道: 私にできること", "en": "What I can do"},
    "stack": {"jp": "道具: 技術スタック", "en": "Tech stack"},
    "torii": {"jp": "千本鳥居: 活動の入り口", "en": "Torii gate path into my activity"},
    "feed": {"jp": "今週の参拝: 直近7日間の毎日の貢献数", "en": "This week: contributions on each of the last 7 days"},
    "stat-contrib": {"jp": "過去1年の貢献数", "en": "Contributions in the last year"},
    "stat-month": {"jp": "直近30日の貢献数", "en": "Contributions in the last 30 days"},
    "stat-peak": {"jp": "最も貢献の多かった一日", "en": "Busiest day of the year"},
    "stat-stars": {"jp": "獲得スター数", "en": "Stars earned"},
    "enso": {"jp": "円相: 使用言語の割合", "en": "Enso chart of top languages"},
    "hours": {"jp": "時間帯別のコミット数", "en": "Commits by hour of day"},
    "connect": {"jp": "ご縁: 連絡先", "en": "Connect with me"},
    "toggle": {"jp": "English版を開く", "en": "Switch to Japanese"},
    "divider": {"jp": "提灯を持って歩く狐（区切り）", "en": "A kitsune walking with a lantern (section divider)"},
}
DIVIDER = "assets/common/walker-divider.svg"
LINK_ALT = {
    "jp": {"gmail": "Gmailで連絡", "linkedin": "LinkedInを開く", "x": "Xを開く",
           "instagram": "Instagramを開く", "portfolio": "ポートフォリオを開く",
           "huggingface": "Hugging Faceを開く", "tryhackme": "TryHackMeを開く"},
    "en": {i: f"{label} link" for i, label, _ in LINKS},
}
ACH_HEADING = {"jp": "御守り · 実績と認定", "en": "Achievements · Charms"}
PLAQUE_ALT = {
    "jp": lambda p: f"絵馬: {p.title('jp')}",
    "en": lambda p: f"Project plaque: {p.title('en') if p.title('en').isascii() else p.id}",
}
ACH_ALT_EN = {
    "squid_ctf": "Squid CTF 2022, 1st of 75 teams",
    "knight_ctf": "Knight CTF 2022, 18th of 752 teams",
    "aws_dev": "AWS Certified Developer Associate, 2023",
    "agentforce": "Salesforce Certified Agentforce Specialist, 2025",
    "tryhackme": "TryHackMe, top 5 percent",
    "jlpt": "JLPT N3, passed 2024",
}


def _hackerrank_alt(lang: str) -> str:
    if lang == "jp":
        return "HackerRankのスキルバッジ: " + "、".join(f"{b} 星{st}（{n}問）" for b, st, n, _ in HACKERRANK)
    return "HackerRank skill badges: " + ", ".join(f"{b} {st} stars ({n} solved)" for b, st, n, _ in HACKERRANK)


# 410-wide shrine tablets after the six achievements, paired two per centred row
# (url, asset name, alt per language). A picoCTF tablet will join HackerRank here.
EXTRA_TABLETS: list[tuple[str, str, dict[str, str]]] = [
    (HACKERRANK_URL, "hackerrank", {lang: _hackerrank_alt(lang) for lang in ("jp", "en")}),
    (PICOCTF["url"], "picoctf", {
        "jp": f"picoCTF（{PICOCTF['user']}）: CTF演習スコア {PICOCTF['score']}点",
        "en": f"picoCTF ({PICOCTF['user']}): CTF score {PICOCTF['score']} points",
    }),
]


def tablet_rows(tablets: list[tuple[str, str, dict[str, str]]], lang: str) -> list[str]:
    return _pairs([
        f'<a href="{url}">{_img(f"assets/{lang}/{name}.svg", alt[lang])}</a>'
        for url, name, alt in tablets
    ])


BEAR = "https://static.wikia.nocookie.net/571b16ac-136f-42f4-99eb-173a75d4aa90"
GREETING = {
    "jp": "<em>いろいろな方とつながるのが大好きです。気軽に<b>こんにちは</b>と声をかけてください。"
          "お会いできるのを楽しみにしています！<b>😊</b></em>",
    "en": "<em>I love connecting with different people so if you want to say <b>hi</b>, "
          "I'll be happy to meet you more! <b>😊</b></em>",
}
_ANIM = "https://raw.githubusercontent.com/acervenky/animated-github-badges/master/assets"
GH_BADGES = [
    ("https://docs.github.com/en/developers", f"{_ANIM}/devbadge.gif",
     {"jp": "GitHub開発者ドキュメント", "en": "GitHub developer program"}),
    ("https://github.com/pricing", f"{_ANIM}/pro.gif",
     {"jp": "GitHub Proの料金プラン", "en": "GitHub Pro"}),
    ("https://docs.github.com/en/github/supporting-the-open-source-community-with-github-sponsors",
     f"{_ANIM}/sponsorbadge.gif",
     {"jp": "GitHubスポンサーの案内", "en": "GitHub Sponsors"}),
]
THM_URL = "https://tryhackme.com/p/sky9262"
THM_IMG = "https://tryhackme-badges.s3.amazonaws.com/sky9262.png?0"
SOLVED_URL = "https://solved.ac/sky9262"
SOLVED_CARD = "http://mazassumnida.wtf/api/v2/generate_badge?boj=sky9262"
OWNER_ALT = {
    "thm": {"jp": "TryHackMe（sky9262）のバッジ", "en": "TryHackMe - sky9262"},
    "solved": {"jp": "Solved.ac（sky9262）の実績", "en": "Solved.ac - sky9262"},
    "love": {"jp": "インドで愛を込めて作りました", "en": "Made with love in India"},
    "views": {"jp": "プロフィールの閲覧数", "en": "Profile views"},
    "bear": {"jp": "手を振るクマ", "en": "Waving bear"},
}
MADE_WITH_LOVE = "https://madewithlove.now.sh/in?heart=true&amp;template=for-the-badge"
VIEWS = "https://komarev.com/ghpvc/?username=sky9262&amp;label=Profile%20views&amp;color=0e75b6&amp;style=flat"


def _live(lang: str, branch: str, name: str) -> str:
    return f"{RAW}/{branch}/{lang}/{name}.svg"


def _picture(base: str, alt: str, lang: str, *, live_branch: str | None = None) -> str:
    def u(layout: str) -> str:
        if live_branch:
            return _live(lang, live_branch, f"{base}-{layout}")
        return f"assets/{lang}/{base}-{layout}.svg"

    return (
        f'<picture><source media="(max-width: 600px)" srcset="{u("phone")}">'
        f'<img src="{u("desktop")}" width="100%" alt="{alt}"></picture>'
    )


def _img(src: str, alt: str, width: int = 410) -> str:
    return f'<img src="{src}" width="{width}" alt="{alt}">'


def _pairs(items: list[str]) -> list[str]:
    """Two images per centred paragraph; they wrap to one per row on phones."""
    return [
        '<p align="center">\n' + "\n".join(items[i:i + 2]) + "\n</p>"
        for i in range(0, len(items), 2)
    ]


def _heading(text: str) -> str:
    return f'<h2 align="center">{text}</h2>'


def _centered(inner: str) -> str:
    return f'<p align="center">\n{inner}\n</p>'


def _divider(lang: str) -> str:
    return _centered(f'<img src="{DIVIDER}" width="100%" alt="{ALT["divider"][lang]}">')


def toggle_href(lang: Lang, output_branch: str) -> str:
    """Absolute link to the other-language README on the matching source branch.
    (A relative link from the profile page would resolve against the profile URL.)"""
    other = FILE["en" if lang == "jp" else "jp"]
    return f"{BLOB}/{SOURCE_BRANCH[output_branch]}/{other}"


def render_readme(lang: Lang, output_branch: str) -> str:
    blocks: list[str] = []

    # 1. toggle
    blocks.append(
        f'<p align="right"><a href="{toggle_href(lang, output_branch)}">'
        f'<img src="assets/{lang}/toggle.svg" width="140" alt="{ALT["toggle"][lang]}"></a></p>'
    )
    # 2. hero
    blocks.append(_picture("hero", ALT["hero"][lang], lang))
    blocks.append(_divider(lang))
    # 3. projects
    blocks.append(_heading(SECTION["projects"](lang)))
    items = []
    for p in active_plaques():
        src = (
            _live(lang, output_branch, f"plaque-{p.id}")
            if p.id == "phisheye" else f"assets/{lang}/plaque-{p.id}.svg"
        )
        items.append(f'<a href="{p.link}">{_img(src, PLAQUE_ALT[lang](p))}</a>')
    blocks += _pairs(items)
    # 4-5. can-do, stack (cards carry their own headings)
    blocks.append(_picture("cando", ALT["cando"][lang], lang))
    blocks.append(_picture("stack", ALT["stack"][lang], lang))
    blocks.append(_divider(lang))
    # 6. activity
    blocks.append(_heading(SECTION["activity"](lang)))
    blocks.append(_picture("torii", ALT["torii"][lang], lang, live_branch=output_branch))
    blocks.append(_picture("feed", ALT["feed"][lang], lang, live_branch=output_branch))
    stats = [
        _img(_live(lang, output_branch, k), ALT[k][lang])
        for k in ("stat-contrib", "stat-month", "stat-peak", "stat-stars")
    ]
    blocks += _pairs(stats)
    blocks += _pairs([
        _img(_live(lang, output_branch, k), ALT[k][lang]) for k in ("enso", "hours")
    ])
    blocks.append(f'<h3 align="center">{ACH_HEADING[lang]}</h3>')
    ach = [
        _img(f"assets/{lang}/achievement-{aid}.svg",
             (f"{t('jp')}: {d('jp')}" if lang == "jp" else ACH_ALT_EN[aid]))
        for aid, t, d in ACHIEVEMENTS
    ]
    blocks += _pairs(ach)
    blocks += tablet_rows(EXTRA_TABLETS, lang)
    blocks.append(_centered(
        f'<a href="{THM_URL}"><img src="{THM_IMG}" alt="{OWNER_ALT["thm"][lang]}"></a>'))
    blocks.append(_centered(
        f'<a href="{SOLVED_URL}"><img src="{SOLVED_CARD}" alt="{OWNER_ALT["solved"][lang]}"></a>'))
    # 7. connect
    blocks.append(_picture("connect", ALT["connect"][lang], lang))
    blocks.append(_centered(
        f'<img src="{BEAR}" width="60" alt="{OWNER_ALT["bear"][lang]}"> {GREETING[lang]}'))
    blocks.append(_centered("\n".join(
        f'<a href="{u}"><img src="{g}" width="40" height="40" alt="{a[lang]}"></a>'
        for u, g, a in GH_BADGES)))
    buttons = [
        f'<a href="{url}"><img src="assets/common/btn-{lid}.svg" alt="{LINK_ALT[lang][lid]}"></a>'
        for lid, _label, url in LINKS
    ]
    blocks.append(_centered("\n".join(buttons)))
    # footer: the walker, then the sign-off
    blocks.append(_divider(lang))
    # 8. sign-off
    blocks.append(f'<p align="center"><sub>{CONNECT["signoff"](lang)}</sub></p>')
    blocks.append(_centered(
        f'<img src="{MADE_WITH_LOVE}" alt="{OWNER_ALT["love"][lang]}">\n'
        f'<img src="{VIEWS}" alt="{OWNER_ALT["views"][lang]}">'))
    return "\n\n".join(blocks) + "\n"
