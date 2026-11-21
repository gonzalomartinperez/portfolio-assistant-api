"""Fail when branch coverage falls below the committed per-layer floors.

Reads a Cobertura ``coverage.xml`` (coverage.py, branch mode) and compares the branch
coverage of each group of source files with ``tests/coverage-floors.json``. Floors only
ratchet up: raise a value when a measured run exceeds it, never lower one.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FLOORS_PATH = Path("tests/coverage-floors.json")
# The ASGI module plus the deprecated `app` compatibility namespace (ADR 028; removed in the
# contract phase).
ENTRY_POINTS = (
    "src/portfolio_assistant/main.py",
    "src/app/__init__.py",
    "src/app/main.py",
    "src/app/migrate.py",
    "src/app/knowledge_sync.py",
    "src/app/knowledge_watch.py",
    "src/app/retention.py",
)
GROUPS = {
    "whole": lambda path: True,
    "domain": lambda path: path.startswith("src/portfolio_assistant/domain/"),
    "application": lambda path: path.startswith("src/portfolio_assistant/application/"),
    "ai": lambda path: path.startswith("src/portfolio_assistant/ai/"),
    "adapters": lambda path: path.startswith("src/portfolio_assistant/adapters/"),
    "presentation": lambda path: path.startswith("src/portfolio_assistant/presentation/"),
    "bootstrap": lambda path: path.startswith("src/portfolio_assistant/bootstrap/"),
    "entrypoints": lambda path: (
        path.startswith("src/portfolio_assistant/bootstrap/entrypoints/") or path in ENTRY_POINTS
    ),
}
CONDITION = re.compile(r"\((\d+)/(\d+)\)")


def normalize(filename: str) -> str:
    path = filename.replace("\\", "/").removeprefix("./")
    return (
        path if path.startswith("src/portfolio_assistant/") else f"src/portfolio_assistant/{path}"
    )


def branch_counts(report: Path) -> dict[str, tuple[int, int]]:
    """Return ``{path: (covered, total)}`` branch counts for each measured file."""
    counts: dict[str, tuple[int, int]] = {}
    for element in ET.parse(report).getroot().iter("class"):
        covered = total = 0
        for line in element.iter("line"):
            match = CONDITION.search(line.get("condition-coverage", ""))
            if match:
                covered += int(match.group(1))
                total += int(match.group(2))
        path = normalize(element.get("filename", ""))
        old = counts.get(path, (0, 0))
        counts[path] = (old[0] + covered, old[1] + total)
    return counts


def measure(counts: dict[str, tuple[int, int]]) -> dict[str, float]:
    measured = {}
    for name, belongs in GROUPS.items():
        selected = [value for path, value in counts.items() if belongs(path)]
        total = sum(item[1] for item in selected)
        covered = sum(item[0] for item in selected)
        measured[name] = round(100 * covered / total, 2) if total else 100.0
    return measured


def evaluate(measured: dict[str, float], floors: dict[str, float]) -> list[str]:
    failures = []
    for name, floor in floors.items():
        if name not in measured:
            failures.append(f"{name}: unknown coverage group")
        elif measured[name] < floor:
            failures.append(
                f"{name}: branch coverage {measured[name]:.2f}% is below the floor {floor:.2f}%"
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Cobertura coverage.xml")
    parser.add_argument("--floors", type=Path, default=FLOORS_PATH)
    parser.add_argument("--print", action="store_true", help="print measured values only; no gate")
    args = parser.parse_args(argv)
    counts = branch_counts(args.report)
    if not counts or not sum(total for _, total in counts.values()):
        print("FAIL coverage report has no measured files or branches", file=sys.stderr)
        return 1
    measured = measure(counts)
    if args.print:
        print(json.dumps(measured, indent=2, sort_keys=True))
        return 0
    floors = json.loads(args.floors.read_text())
    for name, floor in floors.items():
        print(f"{name}: {measured.get(name, float('nan')):.2f}% (floor {floor:.2f}%)")
    failures = evaluate(measured, floors)
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
