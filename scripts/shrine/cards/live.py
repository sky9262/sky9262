"""Live activity cards (千本鳥居 · 活動), re-rendered by the GitHub Action every 3 hours.

  * Torii path (千本鳥居): one vermilion gate per week receding along a stone path,
    height 8 + 72 * week / max(1, max_week) and opacity scaled the same way. The
    gates rise one after another on load, fox-fire orbs (狐火) float over the busiest
    weeks, a spirit light walks the path and a stone lantern (or the kitsune sprite,
    Task 14) waits at the near end. Desktop 1200x300 (53 weeks), phone 600x420 (26).
  * Feed (今日の参拝): up to five omikuji paper slips tied to the shimenawa, each with
    a verb, fit(repo, 28) and ago(). Desktop: portrait slips in a row; phone: landscape
    slips hung one below another on red cords. When fewer than 3 events are given,
    the owner's recently pushed public repos fill the row as 更新 / "Updated".
  * Stat plaques: small wooden votive tablets (same family as the achievements) with
    an emblem in a lacquered window and a big carved number. 410x200.
  * Language ensō (円相): a tapered brush circle split by the top 5 languages + other,
    painted on with a mask on load, with a legend. 410x410.
  * Shrine hours: a moon dial; four JST buckets (朝/昼/夕/夜) as petals of light whose
    length scales with the public-commit count. 410x410.

Privacy: the cards render only what they are given. render_feed never filters
events itself (the generator passes already-filtered public events) and nothing
here reads Data.private_repo_names.

Shown as <img>: CSS keyframes only, no hover, no JS. Every glyph comes from the
prebuilt runtime fonts (labels.py + printable ASCII). Stdlib only.
"""
from __future__ import annotations

import base64
import math
import random
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from ...generate.github_data import Data, Event, hour_buckets, streaks
from ..content import Lang
from ..icons import icon
from ..labels import LABELS
from ..metrics import text_width, wrap
from ..palette import PALETTE as P
from ..svg import MOTION_CSS, document, embed_fonts, esc, heading_defs, lantern, petal_def, petals, rope, rope_y, section_heading
from . import achievement as ach

Layout = Literal["desktop", "phone"]
StatKind = Literal["contrib", "streak", "stars", "followers"]

SERIF = 'font-family="Shrine Serif"'
MONO = 'font-family="Shrine Mono"'
RX = 16
FEED_MAX = 5
BACKFILL_BELOW = 3
BACKFILL_WINDOW = timedelta(days=365)
REPO_CHARS = 28


def _g(v: float) -> str:
    return f"{round(v, 2):g}"


def L(key: str, lang: Lang) -> str:
    return LABELS[key][lang]


def fmt(n: int) -> str:
    return f"{n:,}"


def fit(text: str, n: int) -> str:
    """`text` cut to at most n characters, the last one an ellipsis when cut."""
    return text if len(text) <= n else text[: n - 1] + "…"


def ago(at: datetime, now: datetime, lang: Lang) -> str:
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    secs = (now - at).total_seconds()
    if secs < 3600:
        return L("ago_now", lang)
    if secs < 48 * 3600:
        return L("ago_hours", lang).format(n=int(secs // 3600))
    return L("ago_days", lang).format(n=int(secs // 86400))


# ---------------------------------------------------------------- shared scenery


FRAME_DEF = (
    f'<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["lantern-gold"]}" stop-opacity="0.45"/>'
    f'<stop offset="0.5" stop-color="{P["vermilion"]}" stop-opacity="0.18"/>'
    f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0.35"/></linearGradient>'
)

BASE_CSS = """
.gr{transform-box:fill-box;transform-origin:50% 100%;animation:grow 1s cubic-bezier(.2,.8,.2,1) both}
@keyframes grow{from{transform:scaleY(0);opacity:0}to{transform:none;opacity:1}}
.bob{animation:bob 4.6s ease-in-out infinite}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
.twk{animation:pulse 3.2s ease-in-out infinite}
.sheen{animation:sheen 11s ease-in-out infinite}
@keyframes sheen{0%,55%{transform:translateX(-260px)}80%,100%{transform:translateX(560px)}}
.halo{animation:breathe 5s ease-in-out infinite}
.drop{animation:drop 1.1s cubic-bezier(.2,.9,.25,1.15) both}
@keyframes drop{from{opacity:0;transform:translateY(-26px)}to{opacity:1;transform:none}}
"""


def _defs(w: float, h: float) -> str:
    return (
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="{RX}"/></clipPath>'
        + heading_defs()
        + petal_def()
        + FRAME_DEF
        + f'<linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["night-2"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{P["vermilion"]}" stop-opacity="0.10"/></linearGradient>'
        f'<radialGradient id="orb" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#fff4dc"/>'
        f'<stop offset="0.25" stop-color="{P["lantern-gold"]}" stop-opacity="0.95"/>'
        f'<stop offset="1" stop-color="{P["lantern-glow-b"]}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="cyanOrb" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#e9feff"/>'
        f'<stop offset="0.3" stop-color="{P["circuit-cyan"]}" stop-opacity="0.8"/>'
        f'<stop offset="1" stop-color="{P["circuit-cyan"]}" stop-opacity="0"/></radialGradient>'
        '<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>'
        '<filter id="shadow" x="-20%" y="-10%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#000" flood-opacity="0.5"/></filter>'
    )


def _stars(w: float, h: float, n: int, seed: int) -> str:
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        x, y = rnd.uniform(8, w - 8), rnd.uniform(8, h * 0.8)
        r = rnd.choice((0.7, 0.9, 1.1, 1.3))
        if i % 3 == 0:
            out.append(
                f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{r:g}" fill="#fff" class="twk" '
                f'style="animation-delay:-{_g(rnd.uniform(0, 3.2))}s"/>'
            )
        else:
            out.append(f'<circle cx="{_g(x)}" cy="{_g(y)}" r="{r:g}" fill="#fff" opacity="{_g(rnd.uniform(0.3, 0.7))}"/>')
    return "<g>" + "".join(out) + "</g>"


def _frame(w: float, h: float) -> str:
    return (
        f'<rect x="0.75" y="0.75" width="{_g(w - 1.5)}" height="{_g(h - 1.5)}" rx="{RX - 0.75}" '
        f'fill="none" stroke="url(#frame)" stroke-width="1.5"/>'
    )


def _petals(w: float, h: float, n: int, seed: int) -> str:
    rnd = random.Random(seed)
    spec = []
    for i in range(n):
        x = 60 + (w + 120) * (i + rnd.uniform(0.1, 0.9)) / n
        dur = rnd.uniform(11, 16) * h / 440
        spec.append((round(x, 1), round(rnd.uniform(0.7, 1.2), 2), round(dur, 2), round(-rnd.uniform(0, dur), 2)))
    return petals(spec)


def _card(w: float, h: float, scene: str, *, title: str, css: str, defs: str, fonts) -> str:
    body = f'<g clip-path="url(#card)"><rect width="{w}" height="{h}" fill="url(#sky)"/>{scene}</g>{_frame(w, h)}'
    return embed_fonts(document(int(w), int(h), body, title=title, css=MOTION_CSS + BASE_CSS + css, defs=defs), fonts)


# ---------------------------------------------------------------- torii path (千本鳥居)


def _week_start(d: date) -> date:
    """Sunday that starts d's week (GitHub's calendar weeks)."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _week_starts(days: list[tuple[date, int]], n: int) -> list[date]:
    last = max((d for d, _ in days), default=date(2026, 11, 12))
    end = _week_start(last)
    return [end - timedelta(weeks=n - 1 - i) for i in range(n)]


def weekly(days: list[tuple[date, int]], n: int) -> list[int]:
    """Contribution totals of the last n calendar weeks (Sunday start), oldest first."""
    if not days:
        return [0] * n
    starts = _week_starts(days, n)
    idx = {s: i for i, s in enumerate(starts)}
    out = [0] * n
    for d, c in days:
        i = idx.get(_week_start(d))
        if i is not None:
            out[i] += c
    return out


TORII = {
    # weeks, viewBox, first/last gate centre, baseline (near end), receding rise
    "desktop": dict(n=53, w=1200, h=300, x0=52, x1=1060, base=236, rise=14, end_x=1124),
    "phone": dict(n=26, w=600, h=420, x0=36, x1=492, base=344, rise=10, end_x=544),
}
TORII_SIZES = {
    "desktop": dict(title=32, caption=18, total=52, label=18, month=18, peak=18, now=18),
    "phone": dict(title=34, caption=20, total=56, label=20, month=20, peak=20, now=20),
}
HOT = 3  # busiest weeks that get a fox-fire orb

TORII_CSS = """
.walk{animation:walk 16s linear infinite}
.fx{animation:fx 7s ease-in-out infinite}
@keyframes fx{0%,100%{transform:translate(0,0);opacity:.2}30%{opacity:.9}50%{transform:translate(6px,-9px);opacity:.6}75%{transform:translate(-4px,-4px);opacity:.95}}
"""


def _gate_geometry(cfg: dict) -> list[tuple[float, float, float]]:
    """(centre x, baseline y, width) per gate: pitch and width grow and the baseline
    drops towards the near (right) end, so the row recedes into the distance."""
    n = cfg["n"]
    scale = [0.68 + 0.32 * (i / max(1, n - 1)) for i in range(n)]
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + (scale[i - 1] + scale[i]) / 2)
    span = cfg["x1"] - cfg["x0"]
    pitch = span / cum[-1] if cum[-1] else span
    out = []
    for i in range(n):
        t = i / max(1, n - 1)
        x = cfg["x0"] + cum[i] * pitch
        y = cfg["base"] - cfg["rise"] * (1 - t) ** 1.4
        out.append((x, y, pitch * scale[i] * 0.96))
    return out


def _gate(i: int, x: float, by: float, w: float, h: float, op: float, hot: bool) -> str:
    top = by - h
    kt = max(1.8, w * 0.14)  # kasagi (top beam) thickness
    pw = max(1.5, w * 0.15)  # pillar width
    px = w * 0.31  # pillar centre offset
    ov = w * 0.2  # kasagi overhang
    x0, x1 = x - px - ov, x + px + ov
    nuki_y = top + kt + max(1.2, min(h * 0.2, w * 0.5))
    nt = max(1.1, kt * 0.62)
    base_h = min(max(1.2, h * 0.1), 3.6)
    v = P["vermilion"]
    parts = [
        # pillars, slightly splayed
        f'<path d="M{_g(x - px - pw / 2)},{_g(top + kt)} h{_g(pw)} l{_g(-pw * 0.12)},{_g(h - kt)} h{_g(-pw * 1.05)} z'
        f' M{_g(x + px + pw / 2)},{_g(top + kt)} h{_g(-pw)} l{_g(pw * 0.12)},{_g(h - kt)} h{_g(pw * 1.05)} z" fill="url(#pillar)"/>',
        # nuki (tie beam)
        f'<rect x="{_g(x - px - ov * 0.55)}" y="{_g(nuki_y)}" width="{_g(2 * (px + ov * 0.55))}" height="{_g(nt)}" fill="{v}"/>',
        # shimaki under the kasagi, then the black kasagi with upturned ends
        f'<rect x="{_g(x0 + ov * 0.45)}" y="{_g(top + kt * 0.8)}" width="{_g(x1 - x0 - ov * 0.9)}" height="{_g(kt * 0.7)}" fill="{v}"/>',
        f'<path d="M{_g(x0)},{_g(top)} Q{_g(x)},{_g(top + kt * 0.75)} {_g(x1)},{_g(top)} L{_g(x1 - 0.8)},{_g(top + kt)} '
        f'Q{_g(x)},{_g(top + kt * 1.6)} {_g(x0 + 0.8)},{_g(top + kt)} Z" fill="{P["sumi-a"]}"/>'
        f'<path d="M{_g(x0)},{_g(top)} Q{_g(x)},{_g(top + kt * 0.75)} {_g(x1)},{_g(top)}" fill="none" stroke="#ffb08a" stroke-opacity="0.55" stroke-width="0.8"/>',
        # black bases (根巻)
        f'<rect x="{_g(x - px - pw * 0.8)}" y="{_g(by - base_h)}" width="{_g(pw * 1.6)}" height="{_g(base_h)}" fill="{P["sumi-b"]}"/>',
        f'<rect x="{_g(x + px - pw * 0.8)}" y="{_g(by - base_h)}" width="{_g(pw * 1.6)}" height="{_g(base_h)}" fill="{P["sumi-b"]}"/>',
    ]
    glow = (
        f'<ellipse cx="{_g(x)}" cy="{_g(top + h * 0.45)}" rx="{_g(w * 1.5)}" ry="{_g(h * 0.7 + 8)}" fill="url(#lanternGlow)" '
        f'class="lglow" opacity="0.55" style="animation-delay:-{_g(i * 0.37 % 3)}s"/>'
        if hot
        else ""
    )
    return (
        f'{glow}<g class="gate" data-h="{_g(h)}" opacity="{_g(op)}">'
        f'<g class="gr" style="animation-delay:{_g(0.25 + i * 0.028)}s">{"".join(parts)}</g></g>'
    )


def _stone_path(geo: list[tuple[float, float, float]], cfg: dict) -> str:
    """Flagstone path under the gates: thin and high far away, wide and low up close."""
    (fx, fy, fw), (nx, ny, nw) = geo[0], geo[-1]
    left = fx - fw * 1.4
    right = cfg["w"] + 10
    near_y = ny
    top = f"M{_g(left)},{_g(fy)} " + " ".join(f"L{_g(x)},{_g(y)}" for x, y, _ in geo[1:]) + f" L{_g(right)},{_g(near_y)}"
    bottom_far, bottom_near = fy + 7, near_y + 26
    shape = f"{top} L{_g(right)},{_g(bottom_near)} L{_g(left)},{_g(bottom_far)} Z"
    joints = []
    for i in range(0, len(geo) - 1):
        x, y, w = geo[i]
        x2 = (x + geo[i + 1][0]) / 2
        t = i / max(1, len(geo) - 1)
        depth = 7 + 19 * t
        joints.append(f"M{_g(x2)},{_g(y + 1)} l{_g(1.5 + 4 * t)},{_g(depth - 1)}")
    mid = "".join(
        f"M{_g(geo[i][0])},{_g(geo[i][1] + (7 + 19 * i / max(1, len(geo) - 1)) * 0.52)} h{_g(geo[i][2] * 0.9)}"
        for i in range(0, len(geo), 2)
    )
    return (
        f'<path d="{shape}" fill="url(#stone)"/>'
        f'<path d="{top}" fill="none" stroke="{P["moon-b"]}" stroke-opacity="0.22" stroke-width="1"/>'
        f'<path d="{"".join(joints)}{mid}" fill="none" stroke="#0b0a18" stroke-opacity="0.55" stroke-width="1"/>'
    )


def _month_labels(starts: list[date], geo, lang: Lang, size: float, y: float, stop_x: float) -> str:
    names = L("months", lang).split(",")
    out, last_x = [], -1e9
    for i in range(1, len(starts)):
        if starts[i].month == starts[i - 1].month:
            continue
        x = geo[i][0]
        label = names[starts[i].month - 1]
        half = text_width(label, size) / 2
        if x - half < last_x + 10 or x + half > stop_x or x - half < 8:
            continue
        out.append(
            f'<text x="{_g(x)}" y="{_g(y)}" text-anchor="middle" {SERIF} font-size="{size}" fill="{P["text-soft-b"]}">{esc(label)}</text>'
        )
        last_x = x + half
    return "".join(out)


def render_torii_path(data: Data, lang: Lang, layout: Layout, fonts, kitsune_png: bytes | None = None) -> str:
    cfg, sz = TORII[layout], TORII_SIZES[layout]
    n, W, H = cfg["n"], cfg["w"], cfg["h"]
    weeks = weekly(data.days, n)
    starts = _week_starts(data.days, n)
    top = max(1, max(weeks))
    geo = _gate_geometry(cfg)
    hot = {i for i in sorted(range(n), key=lambda i: (-weeks[i], -i))[:HOT] if weeks[i] > 0}
    peak = max(range(n), key=lambda i: (weeks[i], i)) if max(weeks) > 0 else None

    gates, orbs = [], []
    for i, ((x, by, w), c) in enumerate(zip(geo, weeks)):
        r = c / top
        h = 8 + 72 * r
        gates.append(_gate(i, x, by, w, h, 0.3 + 0.7 * r, i in hot))
        if i in hot:
            oy = by - h - 12
            orbs.append(
                f'<g class="bob" style="animation-delay:-{_g(i * 0.7 % 4.6)}s"><g class="drop" style="animation-delay:{_g(1.4 + i * 0.028)}s">'
                f'<circle cx="{_g(x)}" cy="{_g(oy)}" r="9" fill="url(#orb)" class="lglow"/>'
                f'<circle cx="{_g(x)}" cy="{_g(oy)}" r="2.2" fill="#fff4dc"/></g></g>'
            )

    # peak-week tag above the busiest gate
    tag = ""
    if peak is not None:
        x, by, w = geo[peak]
        ty = by - (8 + 72 * weeks[peak] / top) - 30
        tw = text_width(L("torii_peak", lang) + " ", sz["peak"]) + text_width(fmt(weeks[peak]), sz["peak"], weight=700)
        tx = min(max(x, tw / 2 + 14), cfg["end_x"] - 40 - tw / 2)
        tag = (
            f'<g class="rise d3"><text x="{_g(tx)}" y="{_g(ty)}" text-anchor="middle" {SERIF} font-size="{sz["peak"]}" '
            f'fill="{P["text-soft-a"]}">{esc(L("torii_peak", lang))} '
            f'<tspan font-weight="700" fill="{P["lantern-gold"]}">{esc(fmt(weeks[peak]))}</tspan></text>'
            f'<path d="M{_g(x)},{_g(ty + 6)} v8" stroke="{P["lantern-gold"]}" stroke-opacity="0.5" stroke-width="1" stroke-dasharray="2 2"/></g>'
        )

    # near end: the kitsune sprite (Task 14) or a stone lantern
    ex, ey = cfg["end_x"], geo[-1][1]
    if kitsune_png:
        size = 96 if layout == "desktop" else 84
        b64 = base64.b64encode(kitsune_png).decode("ascii")
        href = f"data:image/png;base64,{b64}"
        end = (
            f'<ellipse cx="{_g(ex)}" cy="{_g(ey - 30)}" rx="60" ry="46" fill="url(#lanternGlow)" class="lglow" opacity="0.6"/>'
            f'<image class="kitsune" x="{_g(ex - size / 2)}" y="{_g(ey - size + 6)}" width="{size}" height="{size}" '
            f'preserveAspectRatio="xMidYMax meet" href="{href}" xlink:href="{href}"/>'
        )
    else:
        end = lantern(ex, ey - 60, 0.8)
    now_w = text_width(L("torii_now", lang), sz["now"], weight=700)
    now_x = min(ex, W - 16 - now_w / 2)
    now_label = (
        f'<text x="{_g(now_x)}" y="{_g(MONTH_Y[layout])}" text-anchor="middle" {SERIF} font-size="{sz["now"]}" font-weight="700" '
        f'fill="{P["lantern-gold"]}">{esc(L("torii_now", lang))}</text>'
    )

    # spirit light walking the path
    (fx, fy, _), (lx, ly, _) = geo[0], geo[-1]
    walker = (
        f'<g class="walk" style="--dx:{_g(lx - fx)}px">'
        f'<circle cx="{_g(fx)}" cy="{_g(fy - 7)}" r="14" fill="url(#cyanOrb)" opacity="0.9"/>'
        f'<circle cx="{_g(fx)}" cy="{_g(fy - 7)}" r="2" fill="#e9feff"/></g>'
    )
    walk_css = (
        "@keyframes walk{0%{transform:translate(0,0);opacity:0}8%{opacity:1}88%{opacity:1}"
        f"100%{{transform:translate({_g(lx - fx)}px,{_g(ly - fy)}px);opacity:0}}}}"
    )

    head = _torii_header(data, lang, layout)
    month_y = MONTH_Y[layout]
    months = _month_labels(starts, geo, lang, sz["month"], month_y, now_x - now_w / 2 - 12)

    fireflies = "".join(
        f'<circle cx="{_g(x)}" cy="{_g(y)}" r="1.6" fill="{P["lantern-gold"]}" class="fx" style="animation-delay:-{_g(d)}s"/>'
        for x, y, d in _fireflies(W, cfg["base"], layout)
    )
    moon = (
        f'<g transform="translate({_g(W * (0.74 if layout == "desktop" else 0.86))},{_g(48 if layout == "desktop" else 40)})">'
        f'<circle r="46" fill="url(#moonGlow)"/><circle r="17" fill="{P["moon-a"]}"/>'
        f'<circle cx="7" cy="-4" r="15" fill="{P["night-0"]}" opacity="0.92"/></g>'
    )
    scene = (
        _stars(W, H * 0.7, 46 if layout == "desktop" else 36, 11)
        + moon
        + f'<rect y="{_g(H * 0.55)}" width="{W}" height="{_g(H * 0.45)}" fill="url(#mist)"/>'
        + _petals(W, H, 7 if layout == "desktop" else 5, 3)
        + head
        + _ridges(W, cfg)
        + _stone_path(geo, cfg)
        + walker
        + "".join(gates)
        + "".join(orbs)
        + fireflies
        + tag
        + end
        + months
        + now_label
    )
    title = f"{L('torii_title', lang)} · {fmt(data.total_year)} {L('torii_total', lang)}"
    defs = _defs(W, H) + (
        '<linearGradient id="pillar" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="#ff6a4a"/><stop offset="0.45" stop-color="{P["vermilion"]}"/>'
        '<stop offset="1" stop-color="#a8301d"/></linearGradient>'
        f'<linearGradient id="footMist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["night-2"]}" stop-opacity="0"/>'
        f'<stop offset="0.7" stop-color="{P["night-2"]}" stop-opacity="0.65"/><stop offset="1" stop-color="{P["night-2"]}" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="stone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b3550"/>'
        '<stop offset="1" stop-color="#1c1830"/></linearGradient>'
    )
    return _card(W, H, scene, title=title, css=TORII_CSS + walk_css, defs=defs, fonts=fonts)


def _ridges(w: float, cfg: dict) -> str:
    """Two layers of distant mountains behind the path, misted at the foot."""
    base = cfg["base"]
    out = []
    for k, (amp, lift, fill, op, seed) in enumerate(((34, 62, "#1d1840", 0.9, 1.3), (22, 34, "#120f29", 0.95, 2.9))):
        pts = []
        for i in range(0, 61):
            x = w * i / 60
            u = x / w
            y = base - lift - amp * (0.55 * math.sin(u * 7.1 + seed) + 0.3 * math.sin(u * 17.3 + seed * 2) + 0.15 * math.sin(u * 41 + seed)) * (0.6 + 0.4 * math.sin(u * 3.1 + seed))
            pts.append(f"{_g(x)},{_g(y)}")
        out.append(f'<path d="M0,{base + 120} L{" L".join(pts)} L{_g(w)},{base + 120} Z" fill="{fill}" opacity="{op}"/>')
    return "".join(out) + f'<rect y="{_g(base - 40)}" width="{_g(w)}" height="60" fill="url(#footMist)"/>'


MONTH_Y = {"desktop": 284, "phone": 400}


def _fireflies(w: float, base: float, layout: Layout) -> list[tuple[float, float, float]]:
    rnd = random.Random(5)
    n = 9 if layout == "desktop" else 6
    return [(rnd.uniform(40, w - 120), base - rnd.uniform(20, 110), rnd.uniform(0, 7)) for _ in range(n)]


def _torii_header(data: Data, lang: Lang, layout: Layout) -> str:
    sz = TORII_SIZES[layout]
    total = fmt(data.total_year)
    if layout == "desktop":
        ix, iy = 40, 36
        title = (
            icon("torii", ix, iy, 30, P["vermilion"])
            + f'<text x="{ix + 42}" y="62" {SERIF} font-size="{sz["title"]}" font-weight="700" fill="url(#headInk)" '
            f'letter-spacing="{_g(sz["title"] * 0.08)}">{esc(L("torii_title", lang))}</text>'
            f'<text x="{ix}" y="96" {SERIF} font-size="{sz["caption"]}" fill="{P["text-soft-a"]}" letter-spacing="0.5">'
            f'{esc(L("torii_caption", lang))}</text>'
        )
        right = 1160
        num = (
            f'<text x="{right}" y="74" text-anchor="end" {SERIF} font-size="{sz["total"]}" font-weight="700" '
            f'fill="url(#headInk)" filter="url(#numGlow)">{esc(total)}</text>'
            f'<text x="{right}" y="100" text-anchor="end" {SERIF} font-size="{sz["label"]}" fill="{P["text-soft-a"]}" '
            f'letter-spacing="0.6">{esc(L("torii_total", lang))}</text>'
        )
        return f'<g class="rise">{title}</g><g class="rise d1">{num}</g>' + _num_glow()
    cx = 300
    tw = text_width(L("torii_title", lang), sz["title"], weight=700, letter_spacing=sz["title"] * 0.08)
    title = (
        icon("torii", cx - tw / 2 - 40, 30, 30, P["vermilion"])
        + f'<text x="{_g(cx - tw / 2 + 4)}" y="58" {SERIF} font-size="{sz["title"]}" font-weight="700" fill="url(#headInk)" '
        f'letter-spacing="{_g(sz["title"] * 0.08)}">{esc(L("torii_title", lang))}</text>'
        f'<text x="{cx}" y="94" text-anchor="middle" {SERIF} font-size="{sz["caption"]}" fill="{P["text-soft-a"]}">'
        f'{esc(L("torii_caption", lang))}</text>'
    )
    num = (
        f'<text x="{cx}" y="156" text-anchor="middle" {SERIF} font-size="{sz["total"]}" font-weight="700" '
        f'fill="url(#headInk)" filter="url(#numGlow)">{esc(total)}</text>'
        f'<text x="{cx}" y="184" text-anchor="middle" {SERIF} font-size="{sz["label"]}" fill="{P["text-soft-a"]}" '
        f'letter-spacing="0.6">{esc(L("torii_total", lang))}</text>'
    )
    return f'<g class="rise">{title}</g><g class="rise d1">{num}</g>' + _num_glow()


def _num_glow() -> str:
    return (
        '<defs><filter id="numGlow" x="-20%" y="-40%" width="140%" height="180%">'
        f'<feDropShadow dx="0" dy="0" stdDeviation="7" flood-color="{P["lantern-glow-a"]}" flood-opacity="0.45"/></filter></defs>'
    )


# ---------------------------------------------------------------- feed (今日の参拝)


VERB_ICON = {"push": "torii", "create": "globe", "release": "bell", "star": "star", "fork": "fork", "updated": "torii"}


def _feed_items(events: list[Event], now: datetime, recent_repos) -> list[tuple[str, str, datetime]]:
    """Newest first, one slip per (kind, repo); backfilled from recent repos when
    fewer than BACKFILL_BELOW events are given. Renders exactly what it is given."""
    items: list[tuple[str, str, datetime]] = []
    seen: set[tuple[str, str]] = set()
    for e in sorted(events, key=lambda e: e.at, reverse=True):
        if (e.kind, e.repo) in seen:
            continue
        seen.add((e.kind, e.repo))
        items.append((e.kind, e.repo, e.at))
    if len(items) < BACKFILL_BELOW:
        shown = {r.lower() for _, r, _ in items}
        for name, at in recent_repos:
            if name.lower() in shown or now - at > BACKFILL_WINDOW:
                continue
            shown.add(name.lower())
            items.append(("updated", name, at))
    items.sort(key=lambda x: x[2], reverse=True)
    return items[:FEED_MAX]


def _repo_lines(repo: str, per_line: int, max_lines: int) -> list[tuple[str, bool]]:
    """fit(repo, 28) broken into (text, is_owner) lines of at most per_line characters:
    the owner and slash on their own line when they fit, then the name, broken after
    '-', '_' or '.' where possible."""
    s = fit(repo, REPO_CHARS)
    out: list[tuple[str, bool]] = []
    owner, slash, name = s.partition("/")
    if slash and len(owner) + 1 <= per_line:
        out.append((owner + "/", True))
        rest = name
    else:
        rest = s
    while rest:
        if len(rest) <= per_line:
            out.append((rest, False))
            break
        cut = max((rest.rfind(c, 0, per_line) for c in "-_./"), default=-1)
        cut = cut + 1 if cut >= per_line // 2 else per_line
        out.append((rest[:cut], False))
        rest = rest[cut:]
    if len(out) > max_lines:  # cannot happen for 28 characters; keep the end visible
        out = out[: max_lines - 1] + [("".join(t for t, _ in out[max_lines - 1:]), False)]
    return out


FEED_CSS = """
.slipsway{transform-box:fill-box;transform-origin:50% 0;animation:sway 5s ease-in-out infinite}
.chain{transform-box:view-box;animation:chain 6s ease-in-out infinite}
@keyframes chain{0%,100%{transform:rotate(-.5deg)}50%{transform:rotate(.5deg)}}
.flutter{transform-box:fill-box;transform-origin:50% 0;animation:flutter 3.6s ease-in-out infinite}
@keyframes flutter{0%,100%{transform:skewX(0)}50%{transform:skewX(-2deg)}}
"""


def _feed_defs(w: float, h: float) -> str:
    return _defs(w, h) + (
        '<linearGradient id="washi" x1="0" y1="0" x2="0.3" y2="1"><stop offset="0" stop-color="#fffaf0"/>'
        '<stop offset="0.6" stop-color="#f6ead3"/><stop offset="1" stop-color="#ead8b4"/></linearGradient>'
        f'<linearGradient id="band" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f05a3e"/>'
        f'<stop offset="1" stop-color="#c2331e"/></linearGradient>'
        f'<linearGradient id="bandV" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#c2331e"/>'
        f'<stop offset="1" stop-color="#ec5236"/></linearGradient>'
        '<linearGradient id="crease" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7a5a30" stop-opacity="0"/>'
        '<stop offset="0.45" stop-color="#7a5a30" stop-opacity="0.13"/><stop offset="0.55" stop-color="#fff" stop-opacity="0.5"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<filter id="paper" x="0" y="0" width="100%" height="100%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4" result="n"/>'
        '<feColorMatrix in="n" type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.32  0 0 0 0 0.16  0 0 0 0.10 0"/>'
        '<feComposite in2="SourceGraphic" operator="in"/></filter>'
        '<filter id="stampInk" x="-10%" y="-10%" width="120%" height="120%">'
        '<feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="2" seed="9" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="1.6" xChannelSelector="R" yChannelSelector="G"/></filter>'
    )


def _fortune(i: int) -> str:
    f = L("fortunes", "jp").split(",")
    return f[(i * 3 + 1) % len(f)] if i else f[0]


def _stamp(x: float, y: float, r: float, i: int) -> str:
    """Decorative omikuji fortune seal (大吉, 吉, ...), rotated a little."""
    t = _fortune(i)
    fs = r * (1.0 if len(t) == 1 else 0.78)
    return (
        f'<g transform="translate({_g(x)},{_g(y)}) rotate({-10 + (i * 7) % 18})" filter="url(#stampInk)" opacity="0.82">'
        f'<circle r="{_g(r)}" fill="none" stroke="{P["vermilion"]}" stroke-width="1.6"/>'
        f'<circle r="{_g(r - 3)}" fill="none" stroke="{P["vermilion"]}" stroke-width="0.6"/>'
        f'<text class="deco" y="{_g(fs * 0.36)}" text-anchor="middle" {SERIF} font-size="{_g(fs)}" font-weight="700" '
        f'fill="{P["vermilion"]}" letter-spacing="-0.5">{esc(t)}</text></g>'
    )


def _knot(x: float, y: float) -> str:
    """The slip folded and tied round the rope."""
    return (
        f'<path d="M{_g(x - 13)},{_g(y - 7)} l9,7 l-9,7 z M{_g(x + 13)},{_g(y - 7)} l-9,7 l9,7 z" fill="#f3e6cc" stroke="#cdb489" stroke-width="0.6"/>'
        f'<rect x="{_g(x - 6)}" y="{_g(y - 8)}" width="12" height="16" rx="1.5" fill="#fffaf0" stroke="#cdb489" stroke-width="0.6"/>'
        f'<path d="M{_g(x - 6)},{_g(y - 1)} h12" stroke="{P["vermilion"]}" stroke-width="1.4"/>'
    )


# desktop: portrait slips in a row
SLIP_W, SLIP_H, SLIP_GAP = 200, 228, 24
SLIP_NECK = 16
FEED_D = dict(w=1200, rope_y=86, head_y=50, verb=18, repo=18, owner=18, ago=18, empty=19)
# phone: landscape slips one below another
PSLIP_W, PSLIP_H, PSLIP_GAP, PBAND = 540, 104, 26, 140
FEED_P = dict(w=600, rope_y=92, head_y=56, verb=20, repo=20, owner=20, ago=20, empty=22)


def _slip_desktop(i: int, kind: str, repo: str, at: datetime | None, now: datetime, lang: Lang, cx: float, ty: float, wide: bool) -> str:
    s = FEED_D
    w = SLIP_W if not wide else 300
    x0, y0 = cx - w / 2, ty + SLIP_NECK
    band_h = 40
    v = P["vermilion"]
    paper = (
        f'<rect x="{_g(cx - 9)}" y="{_g(ty)}" width="18" height="{SLIP_NECK + 2}" fill="#f3e6cc"/>'
        f'<rect x="{_g(x0)}" y="{_g(y0)}" width="{w}" height="{SLIP_H}" rx="3" fill="url(#washi)" filter="url(#shadow)"/>'
        f'<rect x="{_g(x0)}" y="{_g(y0)}" width="{w}" height="{SLIP_H}" rx="3" fill="#fff" filter="url(#paper)"/>'
        f'<rect x="{_g(x0 + 7)}" y="{_g(y0 + 7)}" width="{w - 14}" height="{SLIP_H - 14}" rx="1.5" fill="none" stroke="{v}" stroke-opacity="0.55" stroke-width="0.9"/>'
        f'<rect x="{_g(x0 + 10)}" y="{_g(y0 + 10)}" width="{w - 20}" height="{SLIP_H - 20}" rx="1" fill="none" stroke="{v}" stroke-opacity="0.3" stroke-width="0.5"/>'
        + "".join(
            f'<rect x="{_g(x0)}" y="{_g(y0 + SLIP_H * f)}" width="{w}" height="7" fill="url(#crease)"/>' for f in (0.37, 0.7)
        )
        + f'<rect x="{_g(x0 + 10)}" y="{_g(y0 + 10)}" width="{w - 20}" height="{band_h}" fill="url(#band)"/>'
        f'<rect x="{_g(x0 + 10)}" y="{_g(y0 + 10 + band_h - 2.5)}" width="{w - 20}" height="1" fill="{P["moon-a"]}" opacity="0.6"/>'
    )
    by = y0 + 10 + band_h / 2
    if kind == "empty":
        head = icon("bell", cx - 11, by - 11, 22, P["moon-a"])
        lines = wrap(L("feed_empty", lang), s["empty"], w - 44)
        lh = s["empty"] * 1.45
        cy = y0 + 10 + band_h + (SLIP_H - 20 - band_h) / 2
        y = cy - lh * (len(lines) - 1) / 2 + s["empty"] * 0.35
        body = "".join(
            f'<text x="{_g(cx)}" y="{_g(y + k * lh)}" text-anchor="middle" {SERIF} font-size="{s["empty"]}" font-weight="700" '
            f'fill="{P["ink-a"]}">{esc(t)}</text>'
            for k, t in enumerate(lines)
        )
        return paper + head + body + _stamp(x0 + w - 32, y0 + SLIP_H - 32, 17, 0)
    verb = L(f"verb_{kind}", lang)
    vw = text_width(verb, s["verb"], weight=700, letter_spacing=1)
    ix = cx - (vw + 26) / 2
    head = icon(VERB_ICON[kind], ix, by - 9, 18, P["moon-a"]) + (
        f'<text x="{_g(ix + 26)}" y="{_g(by + s["verb"] * 0.35)}" {SERIF} font-size="{s["verb"]}" font-weight="700" '
        f'fill="{P["moon-a"]}" letter-spacing="1">{esc(verb)}</text>'
    )
    per_line = int((w - 36) // (0.6 * s["repo"]))
    lines = _repo_lines(repo, per_line, 3)
    lh = s["repo"] * 1.32
    area_top, area_bot = y0 + 10 + band_h + 8, y0 + SLIP_H - 58
    y = (area_top + area_bot) / 2 - lh * (len(lines) - 1) / 2 + s["repo"] * 0.36
    body = "".join(
        f'<text x="{_g(cx)}" y="{_g(y + k * lh)}" text-anchor="middle" {MONO} '
        + (
            f'font-size="{s["owner"]}" fill="#8a6a48">'
            if own
            else f'font-size="{s["repo"]}" font-weight="700" fill="{P["ink-a"]}">'
        )
        + f"{esc(t)}</text>"
        for k, (t, own) in enumerate(lines)
    )
    foot_y = y0 + SLIP_H - 46
    foot = (
        f'<path d="M{_g(cx - 50)},{_g(foot_y)} h100" stroke="{v}" stroke-opacity="0.45" stroke-width="0.8"/>'
        f'<path d="M{_g(cx)},{_g(foot_y - 3)} l3,3 l-3,3 l-3,-3 z" fill="{v}"/>'
        f'<text x="{_g(cx)}" y="{_g(y0 + SLIP_H - 22)}" text-anchor="middle" {SERIF} font-size="{s["ago"]}" font-weight="700" '
        f'fill="{P["ink-red"]}">{esc(ago(at, now, lang))}</text>'
    )
    return paper + head + body + foot + _stamp(x0 + w - 30, y0 + SLIP_H - 31, 15, i)


def _slip_phone(i: int, kind: str, repo: str, at: datetime | None, now: datetime, lang: Lang, x0: float, y0: float) -> str:
    s = FEED_P
    w, h = PSLIP_W, PSLIP_H
    v = P["vermilion"]
    paper = (
        f'<rect x="{_g(x0)}" y="{_g(y0)}" width="{w}" height="{h}" rx="3" fill="url(#washi)" filter="url(#shadow)"/>'
        f'<rect x="{_g(x0)}" y="{_g(y0)}" width="{w}" height="{h}" rx="3" fill="#fff" filter="url(#paper)"/>'
        f'<rect x="{_g(x0 + 6)}" y="{_g(y0 + 6)}" width="{w - 12}" height="{h - 12}" rx="1.5" fill="none" stroke="{v}" stroke-opacity="0.55" stroke-width="0.9"/>'
        f'<rect x="{_g(x0 + 9)}" y="{_g(y0 + 9)}" width="{PBAND}" height="{h - 18}" fill="url(#bandV)"/>'
        f'<rect x="{_g(x0 + 9 + PBAND - 2.5)}" y="{_g(y0 + 9)}" width="1" height="{h - 18}" fill="{P["moon-a"]}" opacity="0.6"/>'
    )
    bx = x0 + 9 + PBAND / 2
    tx = x0 + 9 + PBAND + 20
    if kind == "empty":
        head = icon("bell", bx - 15, y0 + h / 2 - 15, 30, P["moon-a"])
        lines = wrap(L("feed_empty", lang), s["empty"], w - PBAND - 40 - 50)
        lh = s["empty"] * 1.35
        y = y0 + h / 2 - lh * (len(lines) - 1) / 2 + s["empty"] * 0.35
        body = "".join(
            f'<text x="{_g(tx)}" y="{_g(y + k * lh)}" {SERIF} font-size="{s["empty"]}" font-weight="700" fill="{P["ink-a"]}">{esc(t)}</text>'
            for k, t in enumerate(lines)
        )
        return paper + head + body + _stamp(x0 + w - 36, y0 + h / 2, 19, 0)
    verb = L(f"verb_{kind}", lang)
    head = icon(VERB_ICON[kind], bx - 12, y0 + 22, 24, P["moon-a"]) + (
        f'<text x="{_g(bx)}" y="{_g(y0 + 76)}" text-anchor="middle" {SERIF} font-size="{s["verb"]}" font-weight="700" '
        f'fill="{P["moon-a"]}" letter-spacing="0.5">{esc(verb)}</text>'
    )
    per_line = int((x0 + w - 14 - tx) // (0.6 * s["repo"]))
    lines = _repo_lines(repo, per_line, 2)
    if len(lines) == 2 and lines[0][1] and len(lines[0][0]) + len(lines[1][0]) <= per_line:
        repo_svg = (
            f'<text x="{_g(tx)}" y="{_g(y0 + 46)}" {MONO} font-size="{s["repo"]}">'
            f'<tspan fill="#8a6a48">{esc(lines[0][0])}</tspan>'
            f'<tspan font-weight="700" fill="{P["ink-a"]}">{esc(lines[1][0])}</tspan></text>'
        )
        ago_y = y0 + 82
    else:
        repo_svg = "".join(
            f'<text x="{_g(tx)}" y="{_g(y0 + 40 + k * 24)}" {MONO} font-size="{s["repo"]}"'
            + (' fill="#8a6a48">' if own else f' font-weight="700" fill="{P["ink-a"]}">')
            + f"{esc(t)}</text>"
            for k, (t, own) in enumerate(lines)
        )
        ago_y = y0 + 40 + len(lines) * 24 + 14
    foot = (
        f'<path d="M{_g(tx)},{_g(ago_y - 7)} l3.5,-3.5 l3.5,3.5 l-3.5,3.5 z" fill="{v}"/>'
        f'<text x="{_g(tx + 14)}" y="{_g(ago_y)}" {SERIF} font-size="{s["ago"]}" font-weight="700" fill="{P["ink-red"]}">'
        f"{esc(ago(at, now, lang))}</text>"
    )
    return paper + head + repo_svg + foot + _stamp(x0 + w - 34, y0 + h - 34, 17, i)


def render_feed(events: list[Event], now: datetime, lang: Lang, layout: Layout, fonts, recent_repos=()) -> str:
    items = _feed_items(list(events), now, list(recent_repos))
    slips: list[tuple[str, str, datetime | None]] = list(items) or [("empty", "", None)]
    title = L("feed_title", lang)
    if layout == "desktop":
        s = FEED_D
        W = s["w"]
        widths = [SLIP_W if k != "empty" else 300 for k, _, _ in slips]
        total = sum(widths) + SLIP_GAP * (len(slips) - 1)
        x = (W - total) / 2
        H = s["rope_y"] + 30 + SLIP_NECK + SLIP_H + 30
        rope_top = s["rope_y"]
        parts = []
        tassels = []
        for i, ((kind, repo, at), w) in enumerate(zip(slips, widths)):
            cx = x + w / 2
            ry = rope_top + rope_y(W, cx)
            slip = _slip_desktop(i, kind, repo, at, now, lang, cx, ry + 6, kind == "empty")
            parts.append(
                f'<g class="slip"><g class="drop" style="animation-delay:{_g(0.3 + i * 0.18)}s">'
                f'<g class="slipsway" style="animation-delay:-{_g(i * 1.3)}s">{slip}</g></g>'
                f"{_knot(cx, ry)}</g>"
            )
            if i < len(slips) - 1:
                tassels.append((x + w + SLIP_GAP / 2) / W)
            x += w + SLIP_GAP
        edge = [0.04, 0.96]
        head = section_heading(title, W / 2, s["head_y"], 30, 20)
        rope_svg = f'<g transform="translate(0,{rope_top})">{rope(W, tuple(edge + tassels))}</g>'
        scene = (
            _stars(W, H, 40, 21)
            + f'<rect y="{_g(H * 0.5)}" width="{W}" height="{_g(H * 0.5)}" fill="url(#mist)"/>'
            + _petals(W, H, 7, 8)
            + head
            + rope_svg
            + "".join(parts)
        )
        return _card(W, H, scene, title=title, css=FEED_CSS, defs=_feed_defs(W, H), fonts=fonts)

    s = FEED_P
    W = s["w"]
    x0 = (W - PSLIP_W) / 2
    rope_top = s["rope_y"]
    first = rope_top + 40
    H = first + len(slips) * PSLIP_H + (len(slips) - 1) * PSLIP_GAP + 34
    cords_x = (x0 + 70, x0 + PSLIP_W - 70)
    parts = []
    y = first
    for i, (kind, repo, at) in enumerate(slips):
        # red cords up to the rope (first slip) or the slip above
        if i == 0:
            cords = "".join(
                f'<path d="M{_g(cx)},{_g(rope_top + rope_y(W, cx))} L{_g(cx)},{_g(y + 4)}" stroke="{P["vermilion"]}" stroke-width="2.4"/>'
                f'<circle cx="{_g(cx)}" cy="{_g(rope_top + rope_y(W, cx))}" r="3.6" fill="{P["vermilion"]}"/>'
                for cx in cords_x
            )
        else:
            cords = "".join(
                f'<path d="M{_g(cx)},{_g(y - PSLIP_GAP - 4)} L{_g(cx)},{_g(y + 4)}" stroke="{P["vermilion"]}" stroke-width="2.4"/>'
                f'<circle cx="{_g(cx)}" cy="{_g(y - PSLIP_GAP / 2)}" r="3" fill="{P["vermilion"]}"/>'
                for cx in cords_x
            )
        slip = _slip_phone(i, kind, repo, at, now, lang, x0, y)
        eyelets = "".join(
            f'<circle cx="{_g(cx)}" cy="{_g(y + 4)}" r="2.6" fill="{P["ink-a"]}" stroke="{P["vermilion"]}" stroke-width="1.2"/>'
            + (
                f'<circle cx="{_g(cx)}" cy="{_g(y + PSLIP_H - 4)}" r="2.6" fill="{P["ink-a"]}" stroke="{P["vermilion"]}" stroke-width="1.2"/>'
                if i < len(slips) - 1
                else ""
            )
            for cx in cords_x
        )
        parts.append(
            f'<g class="slip"><g class="drop" style="animation-delay:{_g(0.3 + i * 0.18)}s">{cords}{slip}{eyelets}</g></g>'
        )
        y += PSLIP_H + PSLIP_GAP
    head = section_heading(title, W / 2, s["head_y"], 32, 21, rule=70)
    rope_svg = f'<g transform="translate(0,{rope_top})">{rope(W, (0.05, 0.5, 0.95))}</g>'
    chain = f'<g class="chain" style="transform-origin:{_g(W / 2)}px {rope_top + 20}px">{"".join(parts)}</g>'
    scene = (
        _stars(W, H, 40, 22)
        + f'<rect y="{_g(H * 0.5)}" width="{W}" height="{_g(H * 0.5)}" fill="url(#mist)"/>'
        + _petals(W, H, 6, 9)
        + head
        + rope_svg
        + chain
    )
    return _card(W, H, scene, title=title, css=FEED_CSS, defs=_feed_defs(W, H), fonts=fonts)


# ---------------------------------------------------------------- stat plaques


STAT_ACCENT = {
    "contrib": P["vermilion"],
    "streak": P["lantern-glow-b"],
    "stars": P["lantern-gold"],
    "followers": P["sakura-b"],
}
STAT_INDEX = {"contrib": 0, "streak": 1, "stars": 2, "followers": 3}
STAT_CSS = """
.flame{transform-box:fill-box;transform-origin:50% 100%;animation:flame 2.2s ease-in-out infinite}
@keyframes flame{0%,100%{transform:scale(1,1) skewX(0)}30%{transform:scale(.95,1.06) skewX(-3deg)}60%{transform:scale(1.04,.96) skewX(2deg)}}
.glint{transform-box:fill-box;transform-origin:center;animation:glint 5s ease-in-out infinite}
@keyframes glint{0%,62%,100%{transform:scale(0) rotate(0deg);opacity:0}72%{transform:scale(1) rotate(45deg);opacity:1}84%{transform:scale(0) rotate(90deg);opacity:0}}
.thread{stroke-dasharray:3 4;animation:dash 1.8s linear infinite}
"""


def _em_contrib() -> str:
    """A single glowing gate on a path of light."""
    return (
        f'<ellipse cy="27" rx="34" ry="5" fill="{P["lantern-glow-a"]}" opacity="0.25"/>'
        '<g transform="scale(0.22)">'
        '<use href="#torii" xlink:href="#torii" y="-120" filter="url(#glow)" class="toriiGlow"/>'
        '<use href="#torii" xlink:href="#torii" y="-120"/></g>'
    )


def _em_streak() -> str:
    return (
        '<radialGradient id="flameG" cx="0.5" cy="0.75" r="0.75"><stop offset="0" stop-color="#fff4dc"/>'
        f'<stop offset="0.35" stop-color="{P["lantern-gold"]}"/><stop offset="0.75" stop-color="{P["lantern-glow-b"]}"/>'
        f'<stop offset="1" stop-color="{P["vermilion"]}"/></radialGradient>'
        f'<circle cy="4" r="30" fill="url(#lanternGlow)" class="lglow"/>'
        '<g class="flame"><path d="M0,30 C-20,28 -24,8 -12,-6 C-8,-12 -6,-20 -2,-30 C2,-18 14,-14 16,-2 C22,10 18,28 0,30 Z" fill="url(#flameG)"/>'
        '<path d="M0,26 C-9,25 -11,14 -5,6 C-3,2 -1,-4 1,-10 C4,-2 10,2 10,10 C11,20 7,26 0,26 Z" fill="#fff4dc" opacity="0.85"/></g>'
    )


def _em_stars() -> str:
    return (
        f'<circle r="30" fill="url(#lanternGlow)" class="lglow" opacity="0.8"/>'
        + icon("star", -22, -24, 44, P["lantern-gold"])
        + '<path class="glint" d="M18,-24 l1.6,-6 l1.6,6 l6,1.6 l-6,1.6 l-1.6,6 l-1.6,-6 l-6,-1.6 z" fill="#fff"/>'
        + '<path class="glint" style="animation-delay:-2.4s" d="M-22,14 l1.2,-4.5 l1.2,4.5 l4.5,1.2 l-4.5,1.2 l-1.2,4.5 l-1.2,-4.5 l-4.5,-1.2 z" fill="#fff"/>'
    )


def _em_followers() -> str:
    gold = P["lantern-gold"]

    def person(x: float, s: float, op: float) -> str:
        return (
            f'<g transform="translate({x},0) scale({s})" opacity="{op}"><circle cy="-12" r="8" fill="{gold}"/>'
            f'<path d="M-14,20 C-14,4 -8,-1 0,-1 C8,-1 14,4 14,20 Z" fill="{gold}"/></g>'
        )

    return (
        person(-15, 1.0, 1) + person(15, 1.0, 0.85)
        + f'<path class="thread" d="M-6,8 C-2,22 2,22 6,8" fill="none" stroke="{P["vermilion"]}" stroke-width="2.2" stroke-linecap="round"/>'
        + f'<path d="M-6,8 C-2,22 2,22 6,8" fill="none" stroke="{P["vermilion"]}" stroke-opacity="0.35" stroke-width="2.2"/>'
    )


EMBLEMS = {"contrib": _em_contrib, "streak": _em_streak, "stars": _em_stars, "followers": _em_followers}


def _stat_text(kind: StatKind, data: Data, lang: Lang) -> tuple[str, str, str, str]:
    """(title, number, unit, sub line)"""
    if kind == "contrib":
        return L("stat_contrib", lang), fmt(data.total_year), "", L("stat_contrib_sub", lang)
    if kind == "streak":
        cur, longest = streaks(data.days)
        unit = L("stat_streak_unit_one" if cur == 1 else "stat_streak_unit", lang)
        return L("stat_streak", lang), fmt(cur), unit, L("stat_streak_sub", lang).format(n=fmt(longest))
    if kind == "stars":
        return L("stat_stars", lang), fmt(data.stars), "", L("stat_stars_sub", lang).format(n=fmt(data.public_repos))
    return L("stat_followers", lang), fmt(data.followers), "", L("stat_followers_sub", lang)


def render_stat(kind: StatKind, data: Data, lang: Lang, fonts) -> str:
    i = STAT_INDEX[kind]
    W, H = ach.W, ach.H
    cx = W / 2
    v = P["vermilion"]
    BL, BR, BT, BB = ach.BL, ach.BR, ach.BT, ach.BB
    top = ach.ROPE_DY + 6 + 40 * (ach.CORD_X[0] / W) * (1 - ach.CORD_X[0] / W)
    cords = (
        f'<path d="M{ach.CORD_X[0]},{_g(top)} L{ach.CORD_X[0] - 6},{ach.ROOF_T + 2} M{ach.CORD_X[1]},{_g(top)} L{ach.CORD_X[1] + 6},{ach.ROOF_T + 2}" '
        f'stroke="{v}" stroke-width="2.4" fill="none" stroke-linecap="round"/>'
        + "".join(f'<circle cx="{x}" cy="{_g(top)}" r="3.4" fill="{v}"/>' for x in ach.CORD_X)
    )
    RT, RB = ach.ROOF_T, ach.ROOF_B
    roof = (
        f'<path d="M{BL - 12},{RT - 3} Q{cx},{RT + 4} {BR + 12},{RT - 3} L{BR + 6},{RB} L{BL - 6},{RB} Z" '
        f'fill="url(#roof)" stroke="{P["ink-a"]}" stroke-width="1"/>'
        f'<path d="M{BL - 8},{RT + 1} Q{cx},{RT + 7} {BR + 8},{RT + 1}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.35" stroke-width="1"/>'
        + "".join(
            f'<circle cx="{x - (6 if x < cx else -6)}" cy="{RT + 2}" r="2.6" fill="{P["ink-a"]}" stroke="{v}" stroke-width="1.2"/>'
            for x in ach.CORD_X
        )
    )
    board = (
        f'<rect x="{BL + 2.5}" y="{BT + 3.5}" width="{BR - BL}" height="{BB - BT}" rx="5" fill="{ach.EDGE}"/>'
        f'<rect x="{BL}" y="{BT}" width="{BR - BL}" height="{BB - BT}" rx="5" fill="url(#wood)" stroke="{ach.EDGE}" stroke-width="2"/>'
        '<use href="#grain" xlink:href="#grain"/>'
        f'<rect x="{BL + 6}" y="{BT + 6}" width="{BR - BL - 12}" height="{BB - BT - 12}" rx="3" fill="none" '
        f'stroke="{P["moon-b"]}" stroke-opacity="0.3" stroke-width="1.1"/>'
        f'<g clip-path="url(#boardClip)"><g transform="rotate(16 {cx} {(BT + BB) / 2})">'
        f'<rect class="sheen" x="0" y="-40" width="70" height="240" fill="url(#sheenG)" style="animation-delay:{-1.7 * i:g}s"/></g></g>'
        + ach._corners()
    )
    wx, wy = ach.WIN_C
    R = ach.WIN_R
    window = (
        f'<g transform="translate({wx},{wy})">'
        f'<circle r="{R + 3}" fill="{P["ink-a"]}" opacity="0.35"/>'
        f'<circle r="{R}" fill="url(#lacquer)" stroke="{P["lantern-gold"]}" stroke-opacity="0.8" stroke-width="1.8"/>'
        f'<circle r="{R - 4}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.25" stroke-width="0.8"/>'
        f'<circle r="{R - 6}" fill="url(#halo)" class="halo" style="animation-delay:{-0.9 * i:g}s"/>'
        f'<g clip-path="url(#win)">{EMBLEMS[kind]()}</g></g>'
    )
    title, number, unit, sub = _stat_text(kind, data, lang)
    tx = ach.TEXT_X
    num_size = 46.0
    while num_size > 30 and text_width(number, num_size, weight=700) + (
        text_width(" " + unit, 20, weight=700) if unit else 0
    ) > ach.TEXT_W:
        num_size -= 2
    title_size = 17.0
    while title_size > 14 and text_width(title, title_size, weight=700, letter_spacing=0.5) > ach.TEXT_W:
        title_size -= 0.5
    sub_size = 15.0
    while sub_size > 14 and text_width(sub, sub_size) > ach.TEXT_W:
        sub_size -= 0.5
    unit_svg = (
        f'<tspan dx="6" font-size="20" fill="{P["ink-b"]}">{esc(unit)}</tspan>' if unit else ""
    )
    text = (
        f'<g filter="url(#carve)">'
        f'<text x="{tx}" y="90" {SERIF} font-size="{_g(title_size)}" font-weight="700" fill="{P["ink-a"]}" letter-spacing="0.5">{esc(title)}</text>'
        f'<path d="M{tx + 4},101 l4,-4 l4,4 l-4,4 z" fill="{STAT_ACCENT[kind] if kind != "stars" else P["ink-red"]}" stroke="{P["ink-a"]}" stroke-opacity="0.4" stroke-width="0.6"/>'
        f'<rect x="{tx + 14}" y="100.4" width="150" height="1.2" fill="url(#divider)"/>'
        f'<text class="rise d1" x="{tx}" y="146" {SERIF} font-size="{_g(num_size)}" font-weight="700" fill="{P["ink-red"]}">{esc(number)}{unit_svg}</text>'
        f'<text x="{tx}" y="169" {SERIF} font-size="{_g(sub_size)}" fill="{P["ink-b"]}">{esc(sub)}</text>'
        "</g>"
    )
    pivot = f"transform-box:view-box;transform-origin:{_g(cx)}px 14px"
    body = (
        '<g clip-path="url(#card)">'
        + ach._scene_back(i)
        + f'<g class="sway" style="{pivot};animation-delay:{ach.SWAY_DELAYS[i % len(ach.SWAY_DELAYS)]:g}s">'
        + f'<g filter="url(#hang)">{cords}{board}{roof}</g>'
        + window
        + text
        + "</g></g>"
        + f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="15.25" fill="none" stroke="url(#frame)" stroke-width="1.5"/>'
    )
    full_title = f"{title} {number}{(' ' + unit) if unit else ''} · {sub}"
    svg = document(W, H, body, title=full_title, css=MOTION_CSS + BASE_CSS + STAT_CSS, defs=ach._defs(STAT_ACCENT[kind]))
    return embed_fonts(svg, fonts)


# ---------------------------------------------------------------- language ensō (円相)


ENSO_C = (205.0, 196.0)
ENSO_R = 92.0
ENSO_START = 118.0  # degrees, clockwise from +x: the brush lands at lower left
ENSO_SWEEP = 334.0
ENSO_GAP = 2.4
OTHER_COLOR = P["text-soft-b"]

ENSO_CSS = """
.paint{stroke-dasharray:100 100;stroke-dashoffset:100;animation:paint 2.6s cubic-bezier(.45,.05,.3,1) .3s both}
@keyframes paint{to{stroke-dashoffset:0}}
.inkglow{animation:breathe 5s ease-in-out infinite}
"""


def _mix(hex_color: str, to: str, t: float) -> str:
    a = [int(hex_color.lstrip("#")[k : k + 2], 16) for k in (0, 2, 4)]
    b = [int(to.lstrip("#")[k : k + 2], 16) for k in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def _brush_width(u: float) -> float:
    """Brush width along the stroke, u in 0..1: a heavy landing, a steady body with a
    slight wobble, and a dry tapering lift-off."""
    land = 7 * math.exp(-((u / 0.05) ** 2))
    body = 20 + 2.2 * math.sin(u * 17) + 1.4 * math.sin(u * 41 + 1)
    taper = 1.0 if u < 0.8 else max(0.12, 1 - ((u - 0.8) / 0.2) ** 1.4)
    return (body + land) * taper


def _arc_band(a0: float, a1: float, u0: float, u1: float) -> str:
    """Filled brush band between angles a0..a1 (degrees) whose width follows
    _brush_width over the stroke fraction u0..u1."""
    cx, cy = ENSO_C
    steps = max(2, int(abs(a1 - a0) / 2) + 1)
    outer, inner = [], []
    for k in range(steps + 1):
        f = k / steps
        a = math.radians(a0 + (a1 - a0) * f)
        u = u0 + (u1 - u0) * f
        hw = _brush_width(u) / 2
        wob = 1.6 * math.sin(u * 23)
        outer.append((cx + (ENSO_R + hw + wob * 0.3) * math.cos(a), cy + (ENSO_R + hw + wob * 0.3) * math.sin(a)))
        inner.append((cx + (ENSO_R - hw) * math.cos(a), cy + (ENSO_R - hw) * math.sin(a)))
    pts = outer + inner[::-1]
    return "M" + " L".join(f"{_g(x)},{_g(y)}" for x, y in pts) + " Z"


def _pct(p: float) -> str:
    if p >= 10:
        return f"{p:.0f}%"
    if p >= 0.1:
        return f"{p:.1f}%"
    return "<0.1%"


def _enso_parts(data: Data, lang: Lang) -> list[tuple[str, float, str]]:
    """(name, percent, colour): top 5 languages and the rest as 'other'."""
    total = sum(b for _, b, _ in data.languages)
    if total <= 0:
        return []
    out = [(n, 100 * b / total, c) for n, b, c in data.languages[:5]]
    rest = sum(b for _, b, _ in data.languages[5:])
    if rest > 0:
        out.append((L("other", lang), 100 * rest / total, OTHER_COLOR))
    return out


def render_enso(data: Data, lang: Lang, fonts) -> str:
    W = H = 410
    parts = _enso_parts(data, lang)
    cx, cy = ENSO_C
    min_sweep = 3.0
    usable = ENSO_SWEEP - ENSO_GAP * max(0, len(parts) - 1)
    raw = [max(min_sweep, usable * p / 100) for _, p, _ in parts]
    scale = usable / sum(raw) if raw else 1
    sweeps = [s * scale for s in raw]

    arcs = []
    a = ENSO_START
    u = 0.0
    for k, ((name, p, color), sw) in enumerate(zip(parts, sweeps)):
        du = sw / ENSO_SWEEP
        fill = _mix(color, P["moon-a"], 0.28) if color != OTHER_COLOR else color
        arcs.append(f'<path class="arc" d="{_arc_band(a, a + sw, u, u + du)}" fill="{fill}"/>')
        a += sw + ENSO_GAP
        u += du + ENSO_GAP / ENSO_SWEEP
    # bristle streaks over the paint (dry brush)
    streaks = "".join(
        f'<path d="{_streak(off)}" fill="none" stroke="{P["night-0"]}" stroke-opacity="{op}" stroke-width="{sw}" stroke-dasharray="{dash}"/>'
        for off, op, sw, dash in ((-5, 0.35, 1.1, "40 6 22 9"), (3, 0.28, 0.9, "18 7 50 5"), (7, 0.22, 0.8, "60 12 14 6"))
    )
    # reveal mask: one thick stroke following the brush direction
    ma0 = math.radians(ENSO_START)
    ma1 = math.radians(ENSO_START + ENSO_SWEEP)
    mask_path = (
        f"M{_g(cx + ENSO_R * math.cos(ma0))},{_g(cy + ENSO_R * math.sin(ma0))} "
        f"A{ENSO_R},{ENSO_R} 0 1 1 {_g(cx + ENSO_R * math.cos(ma1))},{_g(cy + ENSO_R * math.sin(ma1))}"
    )
    mask = (
        f'<mask id="reveal" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<path class="paint" d="{mask_path}" pathLength="100" fill="none" stroke="#fff" stroke-width="56" stroke-linecap="round"/></mask>'
    )
    halo = (
        f'<circle cx="{_g(cx)}" cy="{_g(cy)}" r="{_g(ENSO_R + 26)}" fill="url(#ensoHalo)" class="inkglow"/>'
        f'<circle cx="{_g(cx)}" cy="{_g(cy)}" r="{_g(ENSO_R)}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.08" stroke-width="24"/>'
    )
    ink = f'<g mask="url(#reveal)"><g filter="url(#brush)">{"".join(arcs)}{streaks}</g></g>'

    # centre: the top language
    if parts:
        name, p, color = parts[0]
        centre = (
            f'<g class="rise d2"><text x="{_g(cx)}" y="{_g(cy + 6)}" text-anchor="middle" {SERIF} font-size="40" font-weight="700" '
            f'fill="url(#headInk)">{esc(_pct(p))}</text>'
            f'<text x="{_g(cx)}" y="{_g(cy + 32)}" text-anchor="middle" {SERIF} font-size="17" fill="{P["text-soft-a"]}">{esc(_fit_w(name, 17, 130))}</text></g>'
        )
    else:
        centre = (
            f'<text x="{_g(cx)}" y="{_g(cy + 6)}" text-anchor="middle" {SERIF} font-size="16" fill="{P["text-soft-a"]}">'
            f'{esc(L("enso_empty", lang))}</text>'
        )

    # legend: two columns, three rows
    legend = []
    col_x = (34, 222)
    col_w = 156
    for k, (name, p, color) in enumerate(parts):
        lx, ly = col_x[k % 2], 336 + (k // 2) * 28
        sw = _mix(color, P["moon-a"], 0.28) if color != OTHER_COLOR else color
        pct = _pct(p)
        pw = text_width(pct, 15, mono=True)
        legend.append(
            f'<g class="rise" style="animation-delay:{_g(1.2 + k * 0.15)}s">'
            f'<path d="M{lx},{ly - 5} q5,-7 12,-3 q4,3 -1,7 q-7,4 -11,-4 z" fill="{sw}"/>'
            f'<text x="{lx + 20}" y="{ly}" {SERIF} font-size="15" fill="{P["moon-a"]}">{esc(_fit_w(name, 15, col_w - 28 - pw))}</text>'
            f'<text x="{lx + col_w}" y="{ly}" text-anchor="end" {MONO} font-size="15" fill="{P["text-soft-a"]}">{esc(pct)}</text></g>'
        )
    head = section_heading(L("enso_title", lang), W / 2, 42, 22, 15, rule=56)
    note = (
        f'<text x="{W / 2}" y="68" text-anchor="middle" {SERIF} font-size="14" fill="{P["text-soft-b"]}">'
        f'{esc(L("enso_note", lang))}</text>'
    )
    scene = (
        _stars(W, H, 26, 31)
        + _petals(W, H, 4, 12)
        + head
        + note
        + halo
        + ink
        + centre
        + f'<path d="M40,306 H370" stroke="{P["vermilion"]}" stroke-opacity="0.3" stroke-width="1" stroke-dasharray="2 4"/>'
        + "".join(legend)
    )
    defs = _defs(W, H) + mask + (
        f'<radialGradient id="ensoHalo" cx="0.5" cy="0.5" r="0.5"><stop offset="0.55" stop-color="{P["lantern-glow-a"]}" stop-opacity="0"/>'
        f'<stop offset="0.8" stop-color="{P["lantern-glow-a"]}" stop-opacity="0.16"/>'
        f'<stop offset="1" stop-color="{P["lantern-glow-a"]}" stop-opacity="0"/></radialGradient>'
        '<filter id="brush" x="-10%" y="-10%" width="120%" height="120%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.045 0.06" numOctaves="3" seed="3" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="5" xChannelSelector="R" yChannelSelector="G"/></filter>'
    )
    title = f"{L('enso_title', lang)} · " + ", ".join(f"{n} {_pct(p)}" for n, p, _ in parts)
    return _card(W, H, scene, title=title, css=ENSO_CSS, defs=defs, fonts=fonts)


def _streak(off: float) -> str:
    cx, cy = ENSO_C
    r = ENSO_R + off
    a0 = math.radians(ENSO_START + 4)
    a1 = math.radians(ENSO_START + ENSO_SWEEP - 6)
    return (
        f"M{_g(cx + r * math.cos(a0))},{_g(cy + r * math.sin(a0))} "
        f"A{_g(r)},{_g(r)} 0 1 1 {_g(cx + r * math.cos(a1))},{_g(cy + r * math.sin(a1))}"
    )


def _fit_w(text: str, size: float, width: float) -> str:
    """text, shortened with an ellipsis until it fits `width` at `size`."""
    if text_width(text, size) <= width:
        return text
    n = len(text)
    while n > 2 and text_width(fit(text, n), size) > width:
        n -= 1
    return fit(text, n)


# ---------------------------------------------------------------- shrine hours (moon dial)


BUCKETS = ("asa", "hiru", "yu", "yoru")
SPANS = {"asa": (5, 11), "hiru": (11, 17), "yu": (17, 21), "yoru": (21, 29)}
BUCKET_COLOR = {
    "asa": P["sakura-b"],
    "hiru": P["lantern-gold"],
    "yu": P["vermilion"],
    "yoru": P["circuit-cyan"],
}
DIAL_C = (205.0, 196.0)
MOON_R = 57.0
RING_IN = 68.0
PETAL_MIN, PETAL_MAX = 12.0, 50.0

HOURS_CSS = """
.petal{transform-box:view-box;animation:bloom 1.2s cubic-bezier(.2,.8,.2,1) both}
@keyframes bloom{from{transform:scale(.6);opacity:0}to{transform:none;opacity:1}}
.orbit{transform-box:view-box;animation:orbit 24s linear infinite}
@keyframes orbit{to{transform:rotate(360deg)}}
"""


def _hour_angle(h: float) -> float:
    """Degrees clockwise from +x: noon at the top, 18 h right, midnight bottom, 6 h left."""
    return -90 + (h - 12) * 15


def _sector(a0: float, a1: float, r0: float, r1: float) -> str:
    cx, cy = DIAL_C
    p = lambda a, r: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))  # noqa: E731
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p(a0, r0), p(a0, r1), p(a1, r1), p(a1, r0)
    large = 1 if a1 - a0 > 180 else 0
    return (
        f"M{_g(x0)},{_g(y0)} L{_g(x1)},{_g(y1)} A{_g(r1)},{_g(r1)} 0 {large} 1 {_g(x2)},{_g(y2)} "
        f"L{_g(x3)},{_g(y3)} A{_g(r0)},{_g(r0)} 0 {large} 0 {_g(x0)},{_g(y0)} Z"
    )


def render_hours(data: Data, lang: Lang, fonts) -> str:
    W = H = 410
    cx, cy = DIAL_C
    counts = hour_buckets(data.commit_times)
    total = sum(counts.values())
    top = max(1, max(counts.values()))
    petals_svg, labels = [], []
    ranges = L("hour_ranges", lang).split(",")
    kanji = L("hour_kanji", lang)
    for k, b in enumerate(BUCKETS):
        h0, h1 = SPANS[b]
        a0, a1 = _hour_angle(h0) + 1.2, _hour_angle(h1) - 1.2
        c = counts[b]
        length = PETAL_MIN + (PETAL_MAX - PETAL_MIN) * c / top
        col = BUCKET_COLOR[b]
        petals_svg.append(
            f'<g class="petal" style="transform-origin:{_g(cx)}px {_g(cy)}px;animation-delay:{_g(0.3 + k * 0.2)}s">'
            f'<path d="{_sector(a0, a1, RING_IN, RING_IN + PETAL_MAX)}" fill="{col}" opacity="0.07"/>'
            f'<path d="{_sector(a0, a1, RING_IN, RING_IN + length)}" fill="url(#pg-{b})"/>'
            f'<path d="{_sector(a0, a1, RING_IN + length - 2.5, RING_IN + length)}" fill="{col}"/></g>'
        )
        # legend column
        lx = 52 + k * 102
        word = L(f"hour_{b}", lang)
        sub = ranges[k] if lang == "jp" else word
        labels.append(
            f'<g class="rise" style="animation-delay:{_g(1 + k * 0.15)}s">'
            f'<circle cx="{lx}" cy="{344}" r="15" fill="{col}"/>'
            f'<circle cx="{lx}" cy="{344}" r="12.5" fill="none" stroke="{P["night-0"]}" stroke-opacity="0.45" stroke-width="0.8"/>'
            f'<text x="{lx}" y="{350}" text-anchor="middle" {SERIF} font-size="17" font-weight="700" fill="{P["night-0"]}">{esc(kanji[k])}</text>'
            f'<text x="{lx + 22}" y="{351}" {SERIF} font-size="19" font-weight="700" fill="{P["moon-a"]}">{esc(fmt(c))}</text>'
            f'<text x="{lx - 15}" y="{378}" {SERIF} font-size="14" fill="{P["text-soft-a"]}">{esc(sub)}</text></g>'
        )
    # 24 hour ticks on the ring, the four bucket edges longer
    edges = {5, 11, 17, 21}
    ticks = "".join(
        (lambda a, r0, r1: f'<path d="M{_g(cx + r0 * math.cos(a))},{_g(cy + r0 * math.sin(a))} L{_g(cx + r1 * math.cos(a))},{_g(cy + r1 * math.sin(a))}"/>')(
            math.radians(_hour_angle(hh)), RING_IN - (7 if hh in edges else 4), RING_IN - 1
        )
        for hh in range(24)
    )
    dial = (
        f'<circle cx="{_g(cx)}" cy="{_g(cy)}" r="{_g(RING_IN + PETAL_MAX + 10)}" fill="none" stroke="{P["text-soft-b"]}" stroke-opacity="0.18" stroke-dasharray="1 5"/>'
        f'<circle cx="{_g(cx)}" cy="{_g(cy)}" r="{_g(RING_IN - 1)}" fill="none" stroke="{P["lantern-gold"]}" stroke-opacity="0.35"/>'
        f'<g stroke="{P["lantern-gold"]}" stroke-opacity="0.55" stroke-width="1.2">{ticks}</g>'
    )
    moon = (
        f'<circle cx="{_g(cx)}" cy="{_g(cy)}" r="{_g(MOON_R + 30)}" fill="url(#moonGlow)" class="toriiGlow"/>'
        f'<circle cx="{_g(cx)}" cy="{_g(cy)}" r="{_g(MOON_R)}" fill="url(#moonFace)"/>'
        f'<g fill="#e6cfa4" opacity="0.35"><circle cx="{_g(cx - 26)}" cy="{_g(cy - 30)}" r="7"/>'
        f'<circle cx="{_g(cx + 30)}" cy="{_g(cy - 20)}" r="4.5"/><circle cx="{_g(cx + 22)}" cy="{_g(cy + 34)}" r="6"/>'
        f'<circle cx="{_g(cx - 34)}" cy="{_g(cy + 22)}" r="3.5"/></g>'
        f'<text x="{_g(cx)}" y="{_g(cy + 1)}" text-anchor="middle" {SERIF} font-size="36" font-weight="700" fill="{P["ink-red"]}">{esc(fmt(total))}</text>'
        f'<text x="{_g(cx)}" y="{_g(cy + 20)}" text-anchor="middle" {SERIF} font-size="14" fill="{P["ink-a"]}">{esc(L("public_commits", lang))}</text>'
        f'<text x="{_g(cx)}" y="{_g(cy + 37)}" text-anchor="middle" {SERIF} font-size="14" fill="{P["ink-b"]}" opacity="0.75">{esc(L("hours_note", lang))}</text>'
    )
    orbit = (
        f'<g class="orbit" style="transform-origin:{_g(cx)}px {_g(cy)}px">'
        f'<circle cx="{_g(cx)}" cy="{_g(cy - RING_IN - PETAL_MAX - 10)}" r="7" fill="url(#orb)"/>'
        f'<circle cx="{_g(cx)}" cy="{_g(cy - RING_IN - PETAL_MAX - 10)}" r="1.8" fill="#fff4dc"/></g>'
    )
    head = section_heading(L("hours_title", lang), W / 2, 42, 22, 15, rule=56)
    grads = "".join(
        f'<radialGradient id="pg-{b}" gradientUnits="userSpaceOnUse" cx="{_g(cx)}" cy="{_g(cy)}" r="{_g(RING_IN + PETAL_MAX)}">'
        f'<stop offset="{_g(RING_IN / (RING_IN + PETAL_MAX))}" stop-color="{BUCKET_COLOR[b]}" stop-opacity="0.25"/>'
        f'<stop offset="1" stop-color="{BUCKET_COLOR[b]}" stop-opacity="0.85"/></radialGradient>'
        for b in BUCKETS
    )
    defs = _defs(W, H) + grads + (
        f'<radialGradient id="moonFace" cx="0.4" cy="0.35" r="0.75"><stop offset="0" stop-color="#fffaf0"/>'
        f'<stop offset="0.7" stop-color="{P["moon-a"]}"/><stop offset="1" stop-color="{P["moon-b"]}"/></radialGradient>'
    )
    scene = (
        _stars(W, H, 28, 41)
        + _petals(W, H, 4, 14)
        + head
        + dial
        + "".join(petals_svg)
        + orbit
        + moon
        + f'<path d="M40,316 H370" stroke="{P["vermilion"]}" stroke-opacity="0.3" stroke-width="1" stroke-dasharray="2 4"/>'
        + "".join(labels)
    )
    title = f"{L('hours_title', lang)} · {L('public_commits', lang)} " + ", ".join(
        f"{L(f'hour_{b}', lang)} {counts[b]}" for b in BUCKETS
    )
    return _card(W, H, scene, title=title, css=HOURS_CSS, defs=defs, fonts=fonts)
