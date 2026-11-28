"""Download an open-licence image once, resize to a web size, keep a checksum. HTTP/1.1 via curl (museum CDNs reset HTTP/2)."""
# ruff: noqa: E501, E402
from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def fetch(url: str, dest: Path, max_side: int = 1280, quality: int = 82, tries: int = 3) -> dict | None:
    """-> {"w","h","bytes","sha256"} of the saved JPEG, or None if the source did not deliver an image."""
    if dest.exists() and dest.stat().st_size > 2000:
        with Image.open(dest) as im:
            return {"w": im.width, "h": im.height, "bytes": dest.stat().st_size, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}
    dest.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(tries):
        with tempfile.NamedTemporaryFile(suffix=".img") as tmp:
            r = subprocess.run(["curl", "-s", "--http1.1", "-L", "-m", "90", "-o", tmp.name, "-w", "%{http_code}", url],
                               capture_output=True, text=True)
            if r.stdout.strip() != "200":
                continue
            try:
                with Image.open(tmp.name) as im:
                    im = im.convert("RGB")
                    im.thumbnail((max_side, max_side), Image.LANCZOS)
                    im.save(dest, "JPEG", quality=quality, optimize=True, progressive=True)
            except Exception:
                continue
            return {"w": im.width, "h": im.height, "bytes": dest.stat().st_size, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}
    return None
