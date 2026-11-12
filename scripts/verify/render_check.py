"""Render check: load a README page in Chromium and report broken images.

Usage: python scripts/verify/render_check.py URL --out DIR
On GitHub pages images inside article.markdown-body are checked (via
data-canonical-src); for other pages (file://) all <img> elements are used.
Exit 1 if any image is broken.
"""
import argparse
import json
import sys
from pathlib import Path

WIDTHS = {1280: 900, 390: 844}
SCHEMES = ("light", "dark")

JS = """() => {
  const art = document.querySelector('article.markdown-body');
  const imgs = [...(art ? art.querySelectorAll('img') : document.querySelectorAll('img'))];
  return imgs.map((im) => ({
    ok: im.complete && im.naturalWidth > 0,
    src: (art && im.getAttribute('data-canonical-src')) || im.getAttribute('src'),
  }));
}"""


def check(url, out, wait_ms=6000):
    from playwright.sync_api import sync_playwright

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    broken_total = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height in WIDTHS.items():
            for scheme in SCHEMES:
                ctx = browser.new_context(
                    viewport={"width": width, "height": height}, color_scheme=scheme
                )
                page = ctx.new_page()
                page.goto(url, wait_until="networkidle", timeout=90000)
                h = page.evaluate("document.body.scrollHeight")
                for y in range(0, h + height, 600):
                    page.evaluate(f"window.scrollTo(0,{y})")
                    page.wait_for_timeout(250)
                page.wait_for_timeout(wait_ms)
                imgs = page.evaluate(JS)
                bad = [i["src"] for i in imgs if not i["ok"]]
                broken_total += len(bad)
                print(f"{width}-{scheme}: BROKEN {len(bad)}/{len(imgs)}")
                for s in bad:
                    print(f"  {s}")
                page.screenshot(path=str(out / f"{width}-{scheme}.png"), full_page=True)
                ctx.close()
        browser.close()
    return broken_total


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", required=True)
    ap.add_argument("--wait-ms", type=int, default=6000)
    a = ap.parse_args(argv)
    return 1 if check(a.url, a.out, a.wait_ms) else 0


if __name__ == "__main__":
    sys.exit(main())
