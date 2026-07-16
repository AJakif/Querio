#!/usr/bin/env python3
"""Verify Markdown artifacts include writer-haiku provenance markers.

Usage:
  python .claude/scripts/verify_writer_provenance.py path/to/file.md [more files...]
  python .claude/scripts/verify_writer_provenance.py --staged
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

MARKER = "<!-- written-by: writer-haiku | model: haiku -->"


def staged_markdown_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--staged", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    files: list[Path] = []
    for line in result.stdout.splitlines():
        rel = line.strip()
        if rel.endswith(".md"):
            files.append(Path(rel))
    return files


def has_marker(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    for line in content.splitlines():
        if line.strip() == MARKER:
            return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate writer-haiku provenance markers in Markdown artifacts."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Markdown files to verify.",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Verify staged Markdown files from git diff --staged.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths: list[Path] = []

    if args.staged:
        paths.extend(staged_markdown_files())

    for raw in args.paths:
        if raw.endswith(".md"):
            paths.append(Path(raw))

    # Keep order stable but unique.
    unique_paths = list(dict.fromkeys(paths))

    if not unique_paths:
        print("No Markdown files to verify.")
        return 0

    failures: list[Path] = []
    for path in unique_paths:
        if has_marker(path):
            print(f"OK   {path}")
        else:
            print(f"MISS {path}")
            failures.append(path)

    if failures:
        print(
            "\nMissing marker:\n"
            f"{MARKER}\n"
            "Add this near the top of each Markdown artifact written by writer-haiku."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
