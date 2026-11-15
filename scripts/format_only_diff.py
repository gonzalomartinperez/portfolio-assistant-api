"""Prove that a pull request changes the given paths only by `ruff format` output.

The diff-coverage gate counts every changed line, so a mechanical formatting pull request would
need tests for lines whose behavior did not change. This check lets CI skip diff-cover only when
that is provable: every changed Python file under the given paths existed at the base and equals
`ruff format` applied to its base content with the head configuration. Any added, deleted or
renamed file, any non-Python file, or any other byte of difference makes it fail, so diff-cover
runs as usual.

Usage: python -m scripts.format_only_diff --base origin/develop app
Exit 0: format-only. Exit 1: not format-only (or nothing changed). Exit 2: git or ruff error.
"""

import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence

type Formatter = Callable[[str, bytes], bytes]


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def ruff_format(path: str, source: bytes) -> bytes:
    """Format source as ruff would format the file at path with the repository configuration."""
    return subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--stdin-filename", path, "-"],
        input=source,
        check=True,
        capture_output=True,
    ).stdout


def changed(base: str, paths: Sequence[str]) -> list[tuple[str, str]]:
    """Return (status, path) for files that differ between the merge base and HEAD.

    A modification keeps status M only when both sides are regular non-executable files
    (mode 100644); mode changes, symlinks and submodules are reported as status X.
    """
    out = git("diff", "--raw", "--no-renames", "--no-abbrev", f"{base}...HEAD", "--", *paths)
    rows = []
    for line in out.decode().splitlines():
        meta, _, path = line.partition("\t")
        old_mode, new_mode, _old, _new, status = meta.lstrip(":").split()
        if status == "M" and not old_mode == new_mode == "100644":
            status = "X"
        rows.append((status, path))
    return rows


def format_only(
    rows: Sequence[tuple[str, str]],
    base_content: Callable[[str], bytes],
    head_content: Callable[[str], bytes],
    formatter: Formatter,
) -> list[str]:
    """Return the reasons the change set is not format-only (empty list means format-only)."""
    if not rows:
        return ["no changed files under the given paths"]
    reasons = []
    for status, path in rows:
        if status != "M":
            reasons.append(f"{path}: status {status} is not a plain modification")
        elif not path.endswith(".py"):
            reasons.append(f"{path}: not a Python file")
        elif formatter(path, base_content(path)) != head_content(path):
            reasons.append(f"{path}: differs from ruff format of the base version")
    return reasons


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, help="base ref, for example origin/develop")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    try:
        merge_base = git("merge-base", args.base, "HEAD").decode().strip()
        reasons = format_only(
            changed(merge_base, args.paths),
            lambda path: git("show", f"{merge_base}:{path}"),
            lambda path: git("show", f"HEAD:{path}"),
            ruff_format,
        )
    except subprocess.CalledProcessError as error:
        print(f"format-only check failed to run: {error}", file=sys.stderr)
        return 2
    for reason in reasons:
        print(reason)
    if reasons:
        return 1
    print("format-only: every changed file is ruff format output of its base version")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
