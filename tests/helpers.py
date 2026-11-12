import re
import subprocess

from scripts.shrine.svg import font_sizes


def assert_valid_svg(svg: str) -> None:
    r = subprocess.run(
        ["xmllint", "--noout", "-"], input=svg.encode(), capture_output=True
    )
    assert r.returncode == 0, r.stderr.decode()


def assert_min_text(svg: str, rendered_width: int, min_px: float = 12.0) -> None:
    m = re.search(r'viewBox="[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+[\d.]+"', svg)
    assert m, "no viewBox"
    vb_w = float(m.group(1))
    for size, deco in font_sizes(svg):
        if deco:
            continue
        px = size * rendered_width / vb_w
        assert px >= min_px, f"text {size} renders at {px:.1f}px < {min_px}px"


def assert_no_external(svg: str) -> None:
    for bad in ('href="http', "href='http", "@import", "url(http", "url('http", 'url("http'):
        assert bad not in svg, f"external reference: {bad}"


def assert_under(svg: str, kb: int = 500) -> None:
    size = len(svg.encode())
    assert size <= kb * 1024, f"{size} bytes > {kb} KB"
