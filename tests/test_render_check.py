import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parent.parent
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99="
    b"\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.mark.slow
def test_render_check_flags_broken_image(tmp_path):
    (tmp_path / "ok.png").write_bytes(PNG)
    page = tmp_path / "p.html"
    page.write_text('<img src="ok.png"><img src="missing.png">')
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify/render_check.py"), page.as_uri(),
         "--out", str(tmp_path / "out"), "--wait-ms", "200"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if "Executable doesn't exist" in r.stderr:
        pytest.skip("chromium not installed")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "BROKEN 1/2" in r.stdout
    assert (tmp_path / "out" / "390-dark.png").exists()
