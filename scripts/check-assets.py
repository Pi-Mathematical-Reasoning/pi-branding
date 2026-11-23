#!/usr/bin/env python3
"""Check that every published asset exists at its fixed path with its expected shape.

    python3 scripts/check-assets.py

Every Pi repository links to these paths on `main`, so moving, renaming or
resizing one breaks READMEs and profiles elsewhere. Standard library only.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# path: (width, height, maximum size in bytes, why the limit exists)
ASSETS = {
    "assets/logo/pi-logo.png": (1024, 1024, None, None),
    # GitHub App logos must be under 1 MB.
    "assets/avatar/pi-avatar.png": (1024, 1024, 1_000_000, "GitHub App logos must be under 1 MB"),
    # Shown at the top of every README, so kept small.
    "assets/banner/pi-readme-banner.png": (1280, 320, 500_000, "the banner loads on every README"),
    # GitHub rejects social preview images of 1 MB or more.
    "assets/social/pi-social-preview.png": (1280, 640, 1_000_000, "GitHub social previews must be under 1 MB"),
}


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise ValueError("not a PNG file")
    return struct.unpack(">II", header[16:24])


def main() -> int:
    failures = []
    for relative, (width, height, max_bytes, reason) in ASSETS.items():
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"{relative}: missing. Published paths are never moved or removed.")
            continue
        try:
            actual = png_size(path)
        except ValueError as error:
            failures.append(f"{relative}: {error}")
            continue
        if actual != (width, height):
            failures.append(f"{relative}: is {actual[0]}x{actual[1]}, expected {width}x{height}")
        size = path.stat().st_size
        if max_bytes is not None and size > max_bytes:
            failures.append(f"{relative}: is {size} bytes, over {max_bytes} ({reason})")
        if not failures or not failures[-1].startswith(relative):
            print(f"  ok  {relative}  {actual[0]}x{actual[1]}  {size // 1024} KiB")

    for failure in failures:
        print(f"  FAIL  {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
