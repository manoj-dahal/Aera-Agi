# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Generate the AERA brand assets.

    python -m tools.brand                     # writes to assets/brand
    python -m tools.brand --out somewhere/
    python -m tools.brand --install-icons     # also copy icons for the packager
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .generate import generate_all, make_svg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.brand",
        description="Generate the AERA banner, icons and social card.",
    )
    parser.add_argument("--out", default="assets/brand", help="output directory")
    parser.add_argument(
        "--install-icons",
        action="store_true",
        help="copy icon.ico and icon.icns into installer/ for the packaged build",
    )
    parser.add_argument(
        "--emit-svg",
        nargs="?",
        type=int,
        const=64,
        metavar="PX",
        help="print the mark as inline SVG (for the plain HTML shells) and exit",
    )
    args = parser.parse_args(argv)

    if args.emit_svg is not None:
        # Arcs are illegible much below 48px, matching make_icon()'s ladder.
        print(make_svg(args.emit_svg, arcs=args.emit_svg >= 48))
        return 0

    out = Path(args.out)
    written = generate_all(out)

    print(f"\nGenerated in {out}/\n")
    total = 0
    for label, path, (w, h) in written:
        kb = path.stat().st_size / 1024
        total += kb
        print(f"  {label:<22} {path.name:<20} {w}x{h:<6} {kb:7.1f} KB")
    print(f"\n  {len(written)} files, {total / 1024:.2f} MB\n")

    if args.install_icons:
        installer = Path("installer")
        installer.mkdir(exist_ok=True)
        for name in ("icon.ico", "icon.icns"):
            source = out / "icons" / name
            if source.is_file():
                shutil.copy(source, installer / name)
                print(f"  installed installer/{name}")
            else:
                print(f"  skipped {name} (not generated)", file=sys.stderr)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
