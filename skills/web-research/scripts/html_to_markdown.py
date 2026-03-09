#!/usr/bin/env python3
"""Convert HTML from stdin to Markdown using html2text."""

import sys
from pathlib import Path

VENDOR_PYLIB = Path(__file__).resolve().parents[1] / "vendor" / "pylib"
if VENDOR_PYLIB.exists() and str(VENDOR_PYLIB) not in sys.path:
    sys.path.insert(0, str(VENDOR_PYLIB))

import html2text


def main() -> int:
    html = sys.stdin.read()
    if not html.strip():
        print("ERROR: empty html on stdin", file=sys.stderr)
        return 1

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0
    print(h.handle(html).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
