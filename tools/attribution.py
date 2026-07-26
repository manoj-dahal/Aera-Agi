# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Stamp every source file with authorship and contact details.

Run with ``python tools/attribution.py`` to apply, ``--check`` to verify.

Placing a header is not simply prepending text. Four things make it easy to
corrupt a file, and each one is handled explicitly below:

*Python puts the module docstring first.* A comment block above it is legal,
but a *string literal* above it is not -- the docstring stops being
``__doc__`` and becomes a discarded expression. Headers therefore go above
the docstring as ``#`` comments, never inside it.

*Markdown has no comment syntax.* An HTML comment works and renders as
nothing, but it must not sit above a level-one heading, or some renderers
treat the file as untitled. It goes at the foot instead.

*Some files must start with an exact byte.* A shebang, an encoding
declaration, a JSON opening brace, a YAML document marker. Shebangs and
encoding lines keep position and the header slots in after them; JSON has no
comment syntax at all and is skipped rather than broken.

*Generated files are rewritten on every build.* Stamping them wastes the
effort and produces a diff nobody asked for. They are excluded by path.

The header is idempotent: it is keyed by a marker string, so running this
twice does not produce two headers, and changing the wording updates the
existing block rather than stacking a second one underneath.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AUTHOR = "Manoj Dahal"
EMAIL = "info@manoj-dahal.com.np"
PROJECT = "AERA — Artificial Enhanced Reasoning Assistant"
YEAR = "2026"

#: The line that identifies a block as ours. Used to find and replace an
#: existing header rather than adding a second one.
MARKER = f"MADE By {AUTHOR}"

#: Directories that are generated, vendored, or not ours to stamp.
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov", "coverage",
    ".egg-info", "storage", "logs", "cache", "temp",
    # The built interface is copied here by vite; the sources are stamped.
    "ui-react",
}

#: Individual files that are generated at build time. Stamping them is undone
#: on the next build, so the generator is stamped instead.
EXCLUDED_FILES = {
    "interface/index.html",
    "interface/src/styles/globals.css",
    "interface/package-lock.json",
}

#: Files that carry the attribution in their own body, where a comment header
#: would be redundant or wrong. LICENSE states the copyright holder and
#: contact in the licence text itself; a "# MADE By" line above "MIT License"
#: would be noise.
SELF_ATTRIBUTING = {"LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE"}

#: Binary and data formats where a comment would corrupt the file. JSON is
#: here because the format has no comment syntax at all -- a "//" line makes
#: package.json unparseable and npm refuses to run.
SKIP_SUFFIXES = {
    ".json", ".png", ".jpg", ".jpeg", ".ico", ".icns", ".svg", ".wav",
    ".mp3", ".glb", ".gltf", ".zip", ".lock", ".txt", ".onnx",
}


def _hash_header() -> str:
    """Header for languages that comment with ``#``."""
    return "\n".join(
        [
            f"# {MARKER}",
            f"# Copyright (c) {YEAR} {AUTHOR}. All rights reserved.",
            f"# Contact: {EMAIL}",
            f"# {PROJECT}",
        ]
    )


def _slash_header() -> str:
    """Header for languages that comment with ``//``."""
    return "\n".join(
        [
            "/*",
            f" * {MARKER}",
            f" * Copyright (c) {YEAR} {AUTHOR}. All rights reserved.",
            f" * Contact: {EMAIL}",
            f" * {PROJECT}",
            " */",
        ]
    )


def _html_footer() -> str:
    """Footer for Markdown. HTML comments render as nothing."""
    return "\n".join(
        [
            "<!--",
            f"{MARKER}",
            f"Copyright (c) {YEAR} {AUTHOR}. All rights reserved.",
            f"Contact: {EMAIL}",
            f"{PROJECT}",
            "-->",
        ]
    )


def _visible_markdown_footer() -> str:
    """A rendered attribution line, for documents a reader actually opens."""
    return (
        f"---\n\n"
        f"**{MARKER}** · Copyright © {YEAR} {AUTHOR}. All rights reserved.\n"
        f"Contact: [{EMAIL}](mailto:{EMAIL})\n"
    )


HASH_SUFFIXES = {".py", ".yaml", ".yml", ".toml", ".spec", ".sh", ".cfg", ".ini"}

#: Files with no extension that still take a ``#`` comment. Matched by name,
#: because ``Path.suffix`` is empty for all of them and they would otherwise
#: fall through unstamped.
HASH_NAMES = {"Dockerfile", ".gitignore", ".dockerignore", ".env.example", "Makefile"}
SLASH_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".css", ".scss"}


def is_excluded(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    if relative in EXCLUDED_FILES:
        return True
    if path.name in SELF_ATTRIBUTING:
        # Still checked below for the author's name, just not comment-stamped.
        return True
    if path.suffix in SKIP_SUFFIXES:
        return True
    return any(part in EXCLUDED_DIRS for part in path.parts)


def tracked_files() -> list[Path]:
    """Every file git knows about, so untracked scratch work is left alone."""
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return [ROOT / name for name in out if (ROOT / name).is_file()]


def _strip_existing(text: str, kind: str) -> str:
    """Remove a header this script added previously.

    Keyed by the marker, so re-running updates in place. Without this, every
    run would stack another copy on top.
    """
    if MARKER not in text:
        return text

    if kind == "hash":
        pattern = re.compile(
            rf"^# {re.escape(MARKER)}\n(?:#.*\n)*\n?", re.MULTILINE
        )
    elif kind == "slash":
        pattern = re.compile(
            rf"/\*\n(?: \*.*\n)*? \* {re.escape(MARKER)}\n(?: \*.*\n)* \*/\n\n?"
        )
    else:
        pattern = re.compile(
            rf"\n*(?:---\n\n)?(?:\*\*)?{re.escape(MARKER)}(?:\*\*)?[^\n]*\n"
            rf"(?:Contact:[^\n]*\n)?|<!--\n{re.escape(MARKER)}\n(?:.*\n)*?-->\n?"
        )
    return pattern.sub("", text)


def _python_insert_point(text: str) -> int:
    """Index after any shebang and encoding declaration.

    A header above either of those breaks them: the kernel reads the shebang
    from byte zero, and PEP 263 only looks at the first two lines.
    """
    lines = text.splitlines(keepends=True)
    index = 0
    if lines and lines[0].startswith("#!"):
        index = 1
    if len(lines) > index and re.match(r"#.*coding[:=]", lines[index]):
        index += 1
    return sum(len(line) for line in lines[:index])


def stamp(path: Path) -> bool:
    """Add or refresh the header. True when the file changed."""
    original = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in original
    text = original.replace("\r\n", "\n")

    suffix = path.suffix
    if suffix in HASH_SUFFIXES or path.name in HASH_NAMES:
        text = _strip_existing(text, "hash")
        cut = _python_insert_point(text)
        head, body = text[:cut], text[cut:]
        updated = f"{head}{_hash_header()}\n\n{body.lstrip(chr(10))}"
    elif suffix in SLASH_SUFFIXES:
        text = _strip_existing(text, "slash")
        updated = f"{_slash_header()}\n\n{text.lstrip(chr(10))}"
    elif suffix in {".md", ".html"}:
        text = _strip_existing(text, "md").rstrip() + "\n"
        # Visible for documentation a person reads; an HTML comment would be
        # invisible in exactly the place attribution is wanted.
        footer = _visible_markdown_footer() if suffix == ".md" else _html_footer()
        updated = f"{text}\n{footer}"
    else:
        return False

    if crlf:
        updated = updated.replace("\n", "\r\n")

    if updated.encode("utf-8") == original.encode("utf-8"):
        return False
    path.write_bytes(updated.encode("utf-8"))
    return True


def update_metadata() -> list[str]:
    """Put the author and contact in the package manifests too.

    A header in every file is invisible to anyone installing the package;
    these are the fields a tool reads.
    """
    changed: list[str] = []

    pyproject = ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    replacement = f'authors = [{{ name = "{AUTHOR}", email = "{EMAIL}" }}]'
    if replacement not in text:
        text = re.sub(r"^authors = \[.*\]$", replacement, text, flags=re.MULTILINE)
        pyproject.write_text(text, encoding="utf-8")
        changed.append("pyproject.toml")

    package = ROOT / "interface" / "package.json"
    data = json.loads(package.read_text(encoding="utf-8"))
    author = {"name": AUTHOR, "email": EMAIL}
    if data.get("author") != author:
        # Rebuilt in a stable order so the diff is the fields, not a reshuffle.
        ordered: dict[str, object] = {}
        for key in ("name", "version", "private", "type"):
            if key in data:
                ordered[key] = data.pop(key)
        ordered["author"] = author
        ordered["license"] = data.pop("license", "MIT")
        ordered.update(data)
        package.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")
        changed.append("interface/package.json")

    return changed


def write_license() -> bool:
    """A LICENSE file, because the manifests claim MIT and none existed."""
    target = ROOT / "LICENSE"
    body = f"""MIT License

Copyright (c) {YEAR} {AUTHOR} <{EMAIL}>

{PROJECT}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    if target.is_file() and target.read_text(encoding="utf-8") == body:
        return False
    target.write_text(body, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report files that would change, without writing",
    )
    args = parser.parse_args()

    candidates = [p for p in tracked_files() if not is_excluded(p)]

    if args.check:
        missing = [
            str(p.relative_to(ROOT))
            for p in candidates
            if MARKER not in p.read_bytes().decode("utf-8", "replace")
        ]
        # The licence carries the attribution as prose rather than a header.
        for name in sorted(SELF_ATTRIBUTING):
            path = ROOT / name
            if path.is_file():
                body = path.read_text(encoding="utf-8")
                if AUTHOR not in body or EMAIL not in body:
                    missing.append(f"{name} (must name the author and contact)")
        if missing:
            print(f"{len(missing)} files are not attributed:")
            for name in missing[:20]:
                print(f"  {name}")
            return 1
        print(f"all {len(candidates)} files are attributed")
        return 0

    changed = [p for p in candidates if stamp(p)]
    meta = update_metadata()
    licensed = write_license()

    print(f"stamped {len(changed)} of {len(candidates)} files")
    for name in meta:
        print(f"updated {name}")
    if licensed:
        print("wrote LICENSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
