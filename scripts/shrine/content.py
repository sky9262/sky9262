"""Every string the Night Shrine cards render, in Japanese (default) and English.

Client plaques follow the client-detail policy: what the system does and
engineering results that measure the system itself. No client names, no client
or industry descriptors, no team sizes, no counts of a client's own data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Lang = Literal["jp", "en"]


@dataclass(frozen=True)
class T:
    jp: str
    en: str

    def __call__(self, lang: Lang) -> str:
        return self.jp if lang == "jp" else self.en


PORTFOLIO = "https://sky9262.github.io"

# ---------------------------------------------------------------- hero
HERO: dict[str, T] = {
    "terminal": T("kami@jinja:~$ summon --engineer", "kami@jinja:~$ summon --engineer"),
    "name": T("Akash Kumar", "Akash Kumar"),
    "kana": T("アカシュ・クマァ", "アカシュ・クマァ"),
    "role": T("AI・セキュリティエンジニア · 日本在住", "AI & Security Engineer · 日本で働いています"),
    "tagline": T("古き社に、新しい知性を。", "Where ancient spirits meet artificial minds."),
}

TOGGLE = T("English →", "← 日本語")

NDA = T("守秘義務によりクライアント名・詳細は非公開", "Client details withheld under NDA")

SECTION: dict[str, T] = {
    "hero": T("夜の神社 · ごあいさつ", "Welcome · 夜の神社"),
    "projects": T("絵馬 · プロジェクト", "Projects · 絵馬"),
    "cando": T("我が道 · できること", "What I can do · 我が道"),
    "stack": T("道具 · 技術スタック", "Tech stack · 道具"),
    "activity": T("千本鳥居 · 活動", "Activity · 千本鳥居"),
    "connect": T("ご縁 · 連絡先", "Connect · ご縁"),
}


# ---------------------------------------------------------------- projects
@dataclass
class Plaque:
    id: str
    kind: Literal["client", "oss"]
    title: T
    subtitle: T
    years: str
    lines: T  # newline-separated, 3–4 lines per language
    tags: list[str]
    link: str | None
    motif: Literal["sigil", "dashboard", "facilitator", "drone", "eye", "wave", "custom"]
    stamp: Literal["prod", "stars", "hf"]
    repo: str | None  # owner/name, for live stars
    pending: bool = False


def _named(jp: str, en: str) -> tuple[T, T]:
    """(title, subtitle): the card's own language is the title, the other the subtitle."""
    return T(jp, en), T(en, jp)


# Pending plaques (client_a, oss_b) carry placeholder text only, because their
# details are not known yet. Renderers must filter them out with active_plaques().
_PENDING = T("準備中", "Coming soon")

PLAQUES: list[Plaque] = [
    Plaque(
        "scout", "client",
        *_named("スカウトAIエージェント", "AI Scout Agent"),
        years="2025–",
        lines=T(
            "採用サイトを自動操作するマルチエージェントAI\n"
            "候補者検索、AIによる並列評価、日英のスカウト文作成\n"
            "送信前には必ず人が承認\n"
            "GCP上で本番運用中",
            "Multi-agent AI that drives a live\n"
            "recruiting site: search, parallel AI\n"
            "scoring, JP/EN outreach drafts, human\n"
            "approval gate. In production on GCP.",
        ),
        tags=["Claude API", "Multi-agent", "CDP", "FastAPI"],
        link=PORTFOLIO, motif="sigil", stamp="prod", repo=None,
    ),
    Plaque(
        "marketing", "client",
        *_named("マーケティングAIエージェント", "AI Marketing Agent Platform"),
        years="2026",
        lines=T(
            "チャットとダッシュボードから使える\n"
            "マーケティング業務のAIエージェント基盤\n"
            "250件超の自動回帰テストを構築\n"
            "タイムアウトしていた処理が約197秒で完了",
            "Agents for marketing work, driven from\n"
            "chat or a dashboard (Agent SDK + MCP).\n"
            "Built 250+ automated regression tests.\n"
            "A task that timed out now ends in ~197 s.",
        ),
        tags=["Claude Agent SDK", "MCP", "FastAPI", "PostgreSQL"],
        link=PORTFOLIO, motif="dashboard", stamp="prod", repo=None,
    ),
    Plaque(
        "facilitator", "client",
        *_named("AI会議ファシリテーター", "Real-time AI Meeting Facilitator"),
        years="2026",
        lines=T(
            "経営会議の音声を5秒ごとに文字起こしして論点と照合\n"
            "推進・慎重・監査・法務の4つの視点からAIが指摘\n"
            "論点の判定 8〜24秒 → 1.5〜2.5秒\n"
            "処理開始まで 12.4秒 → 0.4秒",
            "Transcribes executive meetings live and\n"
            "checks them against the agenda; 4 AI\n"
            "personas raise points. Agenda check:\n"
            "8–24 s → 1.5–2.5 s; startup 12.4 → 0.4 s.",
        ),
        tags=["Gemini API", "RAG", "Next.js", "Cloud Run"],
        link=PORTFOLIO, motif="facilitator", stamp="prod", repo=None,
    ),
    Plaque(
        "drone", "client",
        *_named("ドローン編隊自動生成エンジン", "Drone Light-Show Formation Engine"),
        years="2026",
        lines=T(
            "写真やSVGからドローンの編隊を自動生成\n"
            "機数は指定どおり、機体間隔1.5m以上を保証\n"
            "メッシュ率 38.4% → 3.6%\n"
            "背景除去 2.99秒 → 0.5秒",
            "Turns a photo or SVG into a drone\n"
            "formation: exact count, ≥1.5 m apart.\n"
            "Mesh rate 38.4% → 3.6%.\n"
            "Background removal 2.99 s → 0.5 s.",
        ),
        tags=["OpenCV", "Blender Python", "FastAPI", "NumPy"],
        link=PORTFOLIO, motif="drone", stamp="prod", repo=None,
    ),
    Plaque(
        "client_a", "client", _PENDING, _PENDING, years="", lines=_PENDING,
        tags=[], link=PORTFOLIO, motif="custom", stamp="prod", repo=None, pending=True,
    ),
    Plaque(
        "phisheye", "oss",
        *_named("フィッシング対策訓練ツール", "phishEye"),
        years="2021",
        lines=T(
            "フィッシングの手口を体験して学ぶ\n"
            "防御のためのセキュリティ教育ツール\n"
            "Python・Flaskで開発し、OSSとして公開",
            "Phishing-awareness training tool\n"
            "for defensive security education.\n"
            "Built with Python and Flask; open source.",
        ),
        tags=["Python", "Flask", "Security"],
        link="https://github.com/sky9262/phishEye",
        motif="eye", stamp="stars", repo="sky9262/phishEye",
    ),
    Plaque(
        "whisper", "oss",
        *_named("アニメ音声文字起こしモデル", "Whisper JP-Anime ASR"),
        years="2025",
        lines=T(
            "約26.9万件のアニメ音声でWhisperを追加学習\n"
            "感情のこもった独特な話し方にも対応\n"
            "文字誤り率（CER）44.3% → 31.2%\n"
            "Hugging Faceでモデルとデモを公開",
            "Whisper fine-tuned on ~269k Japanese\n"
            "anime audio samples (emotive speech).\n"
            "CER 44.3% → 31.2%.\n"
            "Model and demo on Hugging Face.",
        ),
        tags=["Whisper", "Hugging Face", "LoRA", "Transformers"],
        link="https://huggingface.co/sky9262/whisper-base-japanese-anime",
        motif="wave", stamp="hf", repo=None,
    ),
    Plaque(
        "oss_b", "oss", _PENDING, _PENDING, years="", lines=_PENDING,
        tags=[], link=None, motif="custom", stamp="stars", repo=None, pending=True,
    ),
]


def active_plaques() -> list[Plaque]:
    return [p for p in PLAQUES if not p.pending]


# ---------------------------------------------------------------- what I can do
# (icon_id, title, line)
CANDO: list[tuple[str, T, T]] = [
    (
        "agent",
        T("本番で動くAIエージェント", "Production AI agents"),
        T(
            "実際のWebサービスを操作し、検索・AIによる並列評価・日英の文面作成まで"
            "一貫して自動化するマルチエージェント。送信前は必ず人が承認。",
            "Multi-agent systems that drive real web apps end to end (search, parallel "
            "AI scoring, bilingual JP/EN drafting), with a human approval gate.",
        ),
    ),
    (
        "rag",
        T("LLM・RAG・ファインチューニング", "LLMs, RAG & fine-tuning"),
        T(
            "社内文書を根拠に回答するRAG（LangChain）と、LoRA・QLoRAによる追加学習。"
            "Whisperのアニメ音声モデルでは文字誤り率を44.3%から31.2%に改善。",
            "Grounded answers over your own documents (RAG, LangChain); LoRA/QLoRA "
            "fine-tunes. Whisper JP-anime ASR: CER 44.3% → 31.2%.",
        ),
    ),
    (
        "local",
        T("データを外に出さないローカルAI", "Local & private AI"),
        T(
            "Apple Silicon上のOllama・GGUFで、モデルもデータも手元のマシンで完結。"
            "文字起こしと話者識別もローカルで処理。",
            "Models that never leave your machine: Ollama/GGUF on Apple Silicon, "
            "local transcription and speaker ID.",
        ),
    ),
    (
        "gen3d",
        T("生成AI・3D表現", "Generative & 3D"),
        T(
            "拡散モデルによるポートレート生成の研究、GLBモデルをパーティクルに変える"
            "Three.jsの演出、再利用できるエージェントスキルの開発。",
            "Diffusion portrait research, GLB-to-particle Three.js scenes, "
            "reusable agent skills.",
        ),
    ),
    (
        "shield",
        T("AIとクラウドのセキュリティ", "Secure-AI & cloud security"),
        T(
            "自律型AIのガードレール、テナント分離、監査ログ。GCPのIAPとCloud Armor（WAF）"
            "による防御。CTFでは75チーム中1位。",
            "Guardrails for autonomous AI, tenant isolation, audit logs; GCP IAP and "
            "Cloud Armor WAF. CTF: 1st of 75 teams.",
        ),
    ),
]

# ---------------------------------------------------------------- tech stack
STACK: list[tuple[T, list[str]]] = [
    (T("AI・LLM", "AI & LLM"), [
        "Claude API / Agent SDK / MCP", "OpenAI", "Gemini", "LangChain", "Hermes",
        "RAG", "Ollama", "Whisper", "Hugging Face", "LoRA/QLoRA", "vector DBs",
    ]),
    (T("バックエンド", "Backend"), [
        "Python", "FastAPI", "Flask", "Django", "WebSockets", "CDP", "pytest",
    ]),
    (T("フロントエンド・3D", "Frontend & 3D"), [
        "TypeScript", "React", "Next.js", "Vite", "Three.js / WebGL",
        "Blender (Python)", "OpenCV",
    ]),
    (T("クラウド・DevOps", "Cloud & DevOps"), [
        "GCP (Cloud Run, IAP, Cloud Armor, Identity Platform)", "AWS", "Docker",
        "Terraform", "Nginx", "Linux",
    ]),
    (T("データベース", "Data"), ["PostgreSQL", "MySQL", "MongoDB", "SQLite"]),
    (T("セキュリティ", "Security"), [
        "Burp Suite", "Nmap", "Metasploit", "Kali / Parrot OS", "OSINT",
    ]),
]

# ---------------------------------------------------------------- achievements
# (id, title, detail)
ACHIEVEMENTS: list[tuple[str, T, T]] = [
    ("squid_ctf", T("Squid CTF 2022", "Squid CTF 2022"), T("75チーム中 1位", "1st / 75 teams")),
    ("knight_ctf", T("Knight CTF 2022", "Knight CTF 2022"), T("752チーム中 18位", "18th / 752 teams")),
    ("aws_dev", T("AWS認定 デベロッパー – アソシエイト", "AWS Certified Developer – Associate"),
     T("2023年 取得", "Certified 2023")),
    ("agentforce", T("Salesforce認定 Agentforce スペシャリスト", "Salesforce Certified Agentforce Specialist"),
     T("2025年 取得", "Certified 2025")),
    ("tryhackme", T("TryHackMe", "TryHackMe"), T("上位5%", "Top 5%")),
    ("jlpt", T("日本語能力試験 N3", "JLPT N3"), T("2024年 合格", "Passed 2024")),
]

# HackerRank skill badges: (badge, stars, problems solved, tier).
# Checked by hand on 2026-11-13 from hackerrank.com/rest/hackers/sky9262/badges and
# refreshed by hand; static, never fetched at build time.
HACKERRANK: list[tuple[str, int, int, Literal["gold", "silver", "bronze"]]] = [
    ("C++", 5, 18, "gold"),
    ("Python", 5, 26, "gold"),
    ("Ruby", 4, 31, "silver"),
]
HACKERRANK_URL = "https://www.hackerrank.com/profile/sky9262"
HACKERRANK_TEXT: dict[str, T] = {
    "title": T("HackerRank", "HackerRank"),
    # the sub-line names what the medals are, without repeating the title
    "sub": T("言語別スキルバッジ", "Skill badges"),
    "solved": T("{n}問", "{n} solved"),
}

# picoCTF practice score: owner-provided on 2026-11-13, refreshed by hand (static).
# picoCTF has no public profile pages, so the tablet links to the site itself.
PICOCTF: dict = {
    "user": "sky9262",
    "score": "11,600+",
    "url": "https://picoctf.org",
    "title": T("picoCTF", "picoCTF"),
    "sub": T("CTF演習スコア", "CTF score"),
}

# CTFtime team ranking, verified from the CTFtime API on 2026-11-13; refreshed by hand
# (static). The owner wants the team named. years: (year, global place, points, India place).
CTFTIME: dict = {
    "team": "warlock_rootx",
    "country": "IN",
    "url": "https://ctftime.org/team/75661",
    "years": [(2019, 110, 188.0, 5), (2020, 58, 309.7, 2), (2021, 39, 355.2, 3)],
    "role": T("チームメンバー", "Team member"),
    "world": T("世界{n}位", "World #{n}"),
    "india": T("インド{n}位", "India #{n}"),
    # caption of the climb, which switches between the two rank sets
    "state": {"world": T("世界", "World"), "india": T("インド", "India")},
}

# ---------------------------------------------------------------- connect
# (id, label, url), in spec table order
LINKS: list[tuple[str, str, str]] = [
    ("gmail", "Gmail", "mailto:akash2002.pat@gmail.com"),
    ("linkedin", "LinkedIn", "https://www.linkedin.com/in/sky9262/"),
    ("x", "X", "https://x.com/sky9262"),
    ("instagram", "Instagram", "https://instagram.com/sky926296"),
    ("portfolio", "Portfolio", PORTFOLIO),
    ("huggingface", "Hugging Face", "https://huggingface.co/sky9262"),
    ("tryhackme", "TryHackMe", "https://tryhackme.com/p/sky9262"),
]

CONNECT: dict[str, T] = {
    "heading": T("ご縁を結ぶ", "Let's connect"),
    "bell": T("鈴を鳴らすように、お気軽にご連絡ください", "Ring the bell to say hi"),
    "signoff": T("ご参拝いただき、ありがとうございました。", "Thanks for visiting the shrine."),
}
