"""README.md (Japanese) and README-EN.md (English) generators."""
from __future__ import annotations

from scripts.shrine.content import (
    ACHIEVEMENTS, LINKS, SECTION, TOGGLE, CONNECT, Lang, active_plaques,
)

RAW = "https://raw.githubusercontent.com/sky9262/sky9262"
FILE = {"jp": "README.md", "en": "README-EN.md"}

# alt text per image, in the README's language
ALT: dict[str, dict[str, str]] = {
    "hero": {"jp": "夜の神社 アカシュ・クマァ（Akash Kumar）のプロフィール",
             "en": "Akash Kumar, AI and Security Engineer: night shrine profile banner"},
    "cando": {"jp": "我が道: 私にできること", "en": "What I can do"},
    "stack": {"jp": "道具: 技術スタック", "en": "Tech stack"},
    "torii": {"jp": "千本鳥居: 活動の入り口", "en": "Torii gate path into my activity"},
    "feed": {"jp": "最近のGitHub活動の一覧", "en": "Recent GitHub activity feed"},
    "stat-contrib": {"jp": "貢献数", "en": "Contributions"},
    "stat-streak": {"jp": "連続コミット日数", "en": "Commit streak"},
    "stat-stars": {"jp": "獲得スター数", "en": "Stars earned"},
    "stat-followers": {"jp": "フォロワー数", "en": "Followers"},
    "enso": {"jp": "円相: 使用言語の割合", "en": "Enso chart of top languages"},
    "hours": {"jp": "時間帯別のコミット数", "en": "Commits by hour of day"},
    "connect": {"jp": "ご縁: 連絡先", "en": "Connect with me"},
    "toggle": {"jp": "English版を開く", "en": "Switch to Japanese"},
}
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


def render_readme(lang: Lang, output_branch: str) -> str:
    other = FILE["en" if lang == "jp" else "jp"]
    blocks: list[str] = []

    # 1. toggle
    blocks.append(
        f'<p align="right"><a href="{other}">'
        f'<img src="assets/{lang}/toggle.svg" width="140" alt="{ALT["toggle"][lang]}"></a></p>'
    )
    # 2. hero
    blocks.append(_picture("hero", ALT["hero"][lang], lang))
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
    # 6. activity
    blocks.append(_heading(SECTION["activity"](lang)))
    blocks.append(_picture("torii", ALT["torii"][lang], lang, live_branch=output_branch))
    blocks.append(_picture("feed", ALT["feed"][lang], lang, live_branch=output_branch))
    stats = [
        _img(_live(lang, output_branch, k), ALT[k][lang])
        for k in ("stat-contrib", "stat-streak", "stat-stars", "stat-followers")
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
    # 7. connect
    blocks.append(_picture("connect", ALT["connect"][lang], lang))
    buttons = [
        f'<a href="{url}"><img src="assets/common/btn-{lid}.svg" alt="{LINK_ALT[lang][lid]}"></a>'
        for lid, _label, url in LINKS
    ]
    blocks.append(_centered("\n".join(buttons)))
    # 8. sign-off
    blocks.append(f'<p align="center"><sub>{CONNECT["signoff"](lang)}</sub></p>')
    return "\n\n".join(blocks) + "\n"
