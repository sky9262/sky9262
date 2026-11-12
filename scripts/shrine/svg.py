"""SVG primitives for the Night Shrine cards (stdlib only)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .palette import PALETTE as P

NS = "http://www.w3.org/2000/svg"


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


MOTION_CSS = """
.pf{transform-box:fill-box;transform-origin:center;animation:fall linear infinite}
@keyframes fall{0%{transform:translate(0,-40px) rotate(0deg);opacity:0}8%{opacity:.95}90%{opacity:.95}100%{transform:translate(-180px,440px) rotate(620deg);opacity:0}}
.flow{stroke-dasharray:4 22;animation:dash 1.8s linear infinite}
@keyframes dash{to{stroke-dashoffset:-26}}
.node{animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
.lglow{animation:flicker 3s ease-in-out infinite}
@keyframes flicker{0%,100%{opacity:.75}40%{opacity:1}55%{opacity:.6}70%{opacity:.95}}
.toriiGlow{animation:breathe 5s ease-in-out infinite}
@keyframes breathe{0%,100%{opacity:.35}50%{opacity:.7}}
.rise{animation:rise 1.4s ease-out both}
.d1{animation-delay:.2s}.d2{animation-delay:.5s}.d3{animation-delay:.8s}.d4{animation-delay:1.1s}
@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.cursor{animation:blink 1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.sway{transform-box:fill-box;transform-origin:50% 0;animation:sway 5s ease-in-out infinite}
@keyframes sway{0%,100%{transform:rotate(-1.4deg)}50%{transform:rotate(1.4deg)}}
"""

# Gradients/filters/symbols referenced by the primitives; always emitted by document().
SHARED_DEFS = f"""<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P['night-0']}"/><stop offset="0.6" stop-color="{P['night-1']}"/><stop offset="1" stop-color="{P['night-2']}"/></linearGradient>
<radialGradient id="moonGlow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{P['moon-b']}" stop-opacity="0.55"/><stop offset="1" stop-color="{P['moon-b']}" stop-opacity="0"/></radialGradient>
<radialGradient id="lanternGlow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{P['lantern-glow-a']}" stop-opacity="0.9"/><stop offset="1" stop-color="{P['lantern-glow-b']}" stop-opacity="0"/></radialGradient>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<g id="torii"><rect x="-122" y="16" width="244" height="12" fill="{P['vermilion']}"/><rect x="-9" y="28" width="18" height="36" fill="{P['vermilion']}"/><rect x="-118" y="64" width="236" height="14" fill="{P['vermilion']}"/><path d="M-94,28 L-78,28 L-76,232 L-100,232 Z" fill="{P['vermilion']}"/><path d="M94,28 L78,28 L76,232 L100,232 Z" fill="{P['vermilion']}"/><rect x="-104" y="222" width="32" height="16" fill="{P['sumi-b']}"/><rect x="72" y="222" width="32" height="16" fill="{P['sumi-b']}"/><path d="M-140,-6 Q0,16 140,-6 L132,12 Q0,30 -132,12 Z" fill="{P['sumi-a']}"/></g>"""


def document(
    width: int,
    height: int,
    body: str,
    *,
    title: str,
    css: str = "",
    defs: str = "",
) -> str:
    return (
        f'<svg xmlns="{NS}" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img">'
        f"<title>{esc(title)}</title>"
        f"<defs>{SHARED_DEFS}{defs}</defs>"
        f"<style>{css}</style>"
        f"{body}</svg>"
    )


def night_bg(w: int, h: int, rx: int = 16) -> str:
    return f'<rect width="{w}" height="{h}" rx="{rx}" fill="url(#sky)"/>'


def petal_def() -> str:
    return (
        f'<radialGradient id="petal" cx="0.4" cy="0.35" r="0.8"><stop offset="0" stop-color="{P["sakura-a"]}"/>'
        f'<stop offset="1" stop-color="{P["sakura-b"]}"/></radialGradient>'
        '<path id="pt" d="M0,-6 C5,-11 11,-4 7,2 C5,6 1,7 0,5 C-1,7 -5,6 -7,2 C-11,-4 -5,-11 0,-6 Z" fill="url(#petal)"/>'
    )


def _num(v: float) -> str:
    return f"{v:g}"


def petals(spec: list[tuple[float, float, float, float]]) -> str:
    out = []
    for x, scale, dur, delay in spec:
        out.append(
            f'<g transform="translate({_num(x)},0) scale({_num(scale)})">'
            f'<use href="#pt" xlink:href="#pt" class="pf" '
            f'style="animation-duration:{_num(dur)}s;animation-delay:{_num(delay)}s"/></g>'
        )
    return "<g>" + "".join(out) + "</g>"


def torii(x: float, y: float, scale: float = 1.0, glow: bool = True) -> str:
    g = (
        '<use href="#torii" xlink:href="#torii" filter="url(#glow)" class="toriiGlow"/>'
        if glow
        else ""
    )
    return (
        f'<g transform="translate({_num(x)},{_num(y)}) scale({_num(scale)})">'
        f'{g}<use href="#torii" xlink:href="#torii"/></g>'
    )


def lantern(x: float, y: float, delay_s: float = 0) -> str:
    st = f' style="animation-delay:{_num(delay_s)}s"' if delay_s else ""
    stone = "#3b3550"
    return (
        f'<g transform="translate({_num(x)},{_num(y)})">'
        f'<circle cx="0" cy="18" r="34" fill="url(#lanternGlow)" class="lglow"{st}/>'
        f'<rect x="-14" y="0" width="28" height="8" fill="{stone}"/>'
        f'<rect x="-10" y="8" width="20" height="22" fill="{P["lantern-gold"]}" class="lglow"{st}/>'
        f'<rect x="-16" y="30" width="32" height="6" fill="{stone}"/>'
        f'<rect x="-5" y="36" width="10" height="24" fill="{stone}"/></g>'
    )


def rope_y(width: float, x: float) -> float:
    """Height of the rope's centre line at x (the curve drawn by rope())."""
    f = x / width
    return 6 + 40 * f * (1 - f)


def rope(width: int, tassels: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8)) -> str:
    """Shimenawa: a sagging twisted rope with paper shide tassels at the given fractions."""
    mid = width / 2
    path = f"M0,6 Q{_num(mid)},26 {width},6"
    tassels_svg = "".join(
        f'<path d="M{_num(x)},{_num(y)} l-4,8 l5,4 l-4,8 l5,4" fill="none" stroke="{P["moon-a"]}" stroke-width="2"/>'
        for x, y in ((width * f, round(rope_y(width, width * f) + 2, 2)) for f in tassels)
    )
    return (
        f'<g class="rope"><path d="{path}" fill="none" stroke="#d8c08a" stroke-width="7" stroke-linecap="round"/>'
        f'<path d="{path}" fill="none" stroke="{P["wood-grain"]}" stroke-width="7" stroke-linecap="round" stroke-dasharray="3 6"/>'
        f"{tassels_svg}</g>"
    )


def section_heading(text: str, cx: float, y: float, size: float, sub_size: float, *, rule: float = 150) -> str:
    """A section title such as "我が道 · できること": the first part large in lantern
    gold, the second smaller in vermilion, flanked by fading vermilion rules.
    Needs the `headInk` and `ruleL`/`ruleR` gradients from heading_defs()."""
    from .metrics import text_width

    main, _, sub = text.partition(" · ")
    gap = sub_size * 0.9
    ls_main, ls_sub = size * 0.08, sub_size * 0.18
    w = text_width(main, size, weight=700, letter_spacing=ls_main)
    if sub:
        w += gap + text_width(sub, sub_size, letter_spacing=ls_sub)
    x0 = cx - w / 2
    sub_span = (
        f'<tspan dx="{_num(round(gap, 2))}" font-size="{_num(sub_size)}" font-weight="400" '
        f'fill="{P["vermilion"]}" letter-spacing="{_num(round(ls_sub, 2))}">{esc(sub)}</tspan>'
        if sub
        else ""
    )
    pad = size * 0.6
    ry = y - size * 0.32
    return (
        f'<g class="rise">'
        f'<rect x="{_num(round(x0 - pad - rule, 2))}" y="{_num(round(ry - 0.75, 2))}" width="{_num(rule)}" height="1.5" fill="url(#ruleL)"/>'
        f'<rect x="{_num(round(x0 + w + pad, 2))}" y="{_num(round(ry - 0.75, 2))}" width="{_num(rule)}" height="1.5" fill="url(#ruleR)"/>'
        f'<path d="M{_num(round(x0 - pad + 2, 2))},{_num(round(ry, 2))} l-5,-5 l-5,5 l5,5 z M{_num(round(x0 + w + pad - 2, 2))},{_num(round(ry, 2))} l5,-5 l5,5 l-5,5 z" fill="{P["vermilion"]}"/>'
        f'<text x="{_num(round(x0, 2))}" y="{_num(y)}" font-family="Shrine Serif" font-size="{_num(size)}" font-weight="700" '
        f'fill="url(#headInk)" letter-spacing="{_num(round(ls_main, 2))}">{esc(main)}{sub_span}</text></g>'
    )


def heading_defs() -> str:
    return (
        f'<linearGradient id="headInk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["moon-a"]}"/>'
        f'<stop offset="1" stop-color="{P["lantern-gold"]}"/></linearGradient>'
        f'<linearGradient id="ruleL" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{P["vermilion"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{P["vermilion"]}"/></linearGradient>'
        f'<linearGradient id="ruleR" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{P["vermilion"]}"/>'
        f'<stop offset="1" stop-color="{P["vermilion"]}" stop-opacity="0"/></linearGradient>'
    )


# ---------------------------------------------------------------- inspection helpers

def _parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _size_of(el: ET.Element) -> float | None:
    v = el.get("font-size")
    if v is None:
        m = re.search(r"font-size\s*:\s*([\d.]+)", el.get("style", ""))
        v = m.group(1) if m else None
    if v is None:
        return None
    m = re.match(r"\s*([\d.]+)", v)
    return float(m.group(1)) if m else None


def _has_deco(el: ET.Element) -> bool:
    return "deco" in el.get("class", "").split()


def font_sizes(svg: str) -> list[tuple[float, bool]]:
    out: list[tuple[float, bool]] = []

    def walk(el: ET.Element, size: float | None, deco: bool) -> None:
        own = _size_of(el)
        size = own if own is not None else size
        deco = deco or _has_deco(el)
        name = _local(el.tag)
        if name in ("text", "tspan") and size is not None and (
            name == "text" or own is not None
        ):
            out.append((size, deco))
        for c in el:
            walk(c, size, deco)

    walk(_parse(svg), None, False)
    return out


def unsized_text(svg: str) -> int:
    """Count non-deco <text> elements with no explicit or inherited font-size."""
    count = 0

    def walk(el: ET.Element, size: float | None, deco: bool) -> None:
        nonlocal count
        own = _size_of(el)
        size = own if own is not None else size
        deco = deco or _has_deco(el)
        if _local(el.tag) == "text" and size is None and not deco:
            count += 1
        for c in el:
            walk(c, size, deco)

    walk(_parse(svg), None, False)
    return count


def visible_strings(svg: str) -> str:
    out: list[str] = []

    def add(s: str | None) -> None:
        if s and s.strip():
            out.append(s.strip())

    def walk2(el: ET.Element) -> None:
        name = _local(el.tag)
        if name == "style":
            return
        for attr, val in el.attrib.items():
            a = _local(attr)
            if a in ("aria-label", "alt"):
                add(val)
            elif a == "href" and not val.startswith("data:"):
                add(val)
        add(el.text)
        for c in el:
            walk2(c)
            add(c.tail)

    walk2(_parse(svg))
    return "\n".join(out)


# ---------------------------------------------------------------- font embedding

def _text_nodes(svg: str) -> str:
    """Concatenated content of every <text> element (incl. tspans)."""
    return "".join("".join(el.itertext()) for el in _parse(svg).iter() if _local(el.tag) == "text")


def embed_fonts(svg: str, fonts) -> str:
    """Inject fonts.css(<visible <text> content>) into the document's <style>."""
    css = fonts.css(_text_nodes(svg))
    if "<style>" in svg:
        return svg.replace("<style>", "<style>" + css, 1)
    return svg.replace("</defs>", f"</defs><style>{css}</style>", 1)
