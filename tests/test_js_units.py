"""Run the plain-node unit tests of browser modules (skipped where node is not installed)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_morph_unit():
    r = subprocess.run(["node", "tests/js/morph_unit.js"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
