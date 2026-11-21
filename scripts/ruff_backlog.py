"""Count findings of the target ruff ruleset (standards.md "Lint") by rule family.

`ruff check` in CI enforces only the families already at zero findings (pyproject
`extend-select`). This tool measures the full target ruleset so the scorecard can ratchet each
remaining family's count downwards until it reaches zero and moves into `extend-select`.

Usage: python -m scripts.ruff_backlog --out artifacts/ruff-backlog.json
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path

# standards.md "Lint": the ecosystem ruleset, never ALL.
TARGET = [
    "E",
    "W",
    "F",
    "I",
    "B",
    "C4",
    "UP",
    "SIM",
    "RUF",
    "PERF",
    "PIE",
    "PT",
    "PTH",
    "TC",
    "ASYNC",
    "S",
    "T20",
    "TRY",
    "ARG",
    "FAST",
    "LOG",
    "G",
    "DTZ",
    "ERA",
    "FURB",
    "N",
    "RET",
    "D",
    "ANN",
]
IGNORE = ("E501", "TRY003", "D203", "D213")
TEST_IGNORES = ("S101", "ANN", "D", "ARG")
PATHS = ("src", "tests", "contracts", "scripts", "evals", "scorecard")


def family(code: str, families: Iterable[str] = TARGET) -> str:
    """Map a rule code to the longest target family prefix (T201 -> T20, C401 -> C4)."""
    matches = [name for name in families if code.startswith(name)]
    if matches:
        return max(matches, key=len)
    match = re.match(r"[A-Z]+", code)
    return match.group(0) if match else code


def summarize(findings: Sequence[dict[str, object]]) -> dict[str, object]:
    counts = Counter(family(str(item["code"])) for item in findings)
    return {
        "total": len(findings),
        "by_family": {name: counts.get(name, 0) for name in TARGET},
    }


def run_ruff() -> list[dict[str, object]]:
    test_ignores = ", ".join(f"'{code}'" for code in TEST_IGNORES)
    command = [
        sys.executable,
        "-m",
        "ruff",
        "check",
        *PATHS,
        "--select",
        ",".join(TARGET),
        "--ignore",
        ",".join(IGNORE),
        "--config",
        f"lint.per-file-ignores = {{'tests/**' = [{test_ignores}]}}",
        "--exit-zero",
        "--output-format",
        "json",
    ]
    out = subprocess.run(command, check=True, capture_output=True).stdout
    findings: list[dict[str, object]] = json.loads(out)
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    summary = summarize(run_ruff())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"ruff backlog: {summary['total']} findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
