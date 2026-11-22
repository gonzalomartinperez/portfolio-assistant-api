"""Render the README results table from a scorecard snapshot.

Reads a scorecard JSON (the format written by ``python -m scorecard collect``) and
rewrites the block between ``<!-- results:start -->`` and ``<!-- results:end -->`` in
README.md. Every number comes from the scorecard or from a committed baseline file;
a metric the snapshot did not measure renders as "not measured in this snapshot".

    uv run python -m scripts.readme_results --write   # update README.md
    uv run python -m scripts.readme_results --check   # exit 1 when README.md drifted
"""

import argparse
import json
import sys
from pathlib import Path

START = "<!-- results:start -->"
END = "<!-- results:end -->"
UNMEASURED = "not measured in this snapshot"
SNAPSHOT_GLOB = "docs/evidence/scorecard-*.json"
MIB = 1024 * 1024


def latest_snapshot(root: Path) -> Path:
    """Return the newest committed dated scorecard snapshot."""
    snapshots = sorted(root.glob(SNAPSHOT_GLOB))
    if not snapshots:
        raise FileNotFoundError(f"no scorecard snapshot matches {SNAPSHOT_GLOB}")
    return snapshots[-1]


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except OSError, ValueError:
        return None


def measured(scorecard: dict, key: str):
    """Return a metric value, or None when the snapshot did not measure it."""
    entry = scorecard.get("metrics", {}).get(key)
    if not isinstance(entry, dict) or entry.get("status") != "ok":
        return None
    return entry.get("value")


def count(value) -> str:
    return f"{int(value):,}"


def tests_result(scorecard: dict) -> str | None:
    total = measured(scorecard, "tests.unit.total")
    failures = measured(scorecard, "tests.unit.failures")
    skipped = measured(scorecard, "tests.unit.skipped")
    if total is None or failures is None:
        return None
    result = f"{count(total)} tests, {count(failures)} failed"
    return result if skipped is None else f"{result}, {count(skipped)} skipped"


def image_result(scorecard: dict) -> str | None:
    api = measured(scorecard, "image.api_bytes")
    worker = measured(scorecard, "image.worker_bytes")
    if api is None or worker is None:
        return None
    return f"API {api / MIB:.0f} MiB, worker {worker / MIB:.0f} MiB"


def metric_rows(scorecard: dict) -> list[tuple[str, str | None, str]]:
    """Rows backed by the scorecard: (check, result or None, metric key)."""

    def fmt(key: str, template: str) -> str | None:
        value = measured(scorecard, key)
        return None if value is None else template.format(value)

    return [
        (
            "Lint (ruff)",
            fmt("static.ruff_findings", "{:g} findings"),
            "static.ruff_findings",
        ),
        (
            "Types (mypy)",
            fmt("static.mypy_errors", "{:g} errors"),
            "static.mypy_errors",
        ),
        (
            "Types (mypy --strict src)",
            fmt("static.mypy_strict_app_errors", "{:g} errors"),
            "static.mypy_strict_app_errors",
        ),
        ("Offline tests", tests_result(scorecard), "tests.unit.total"),
        (
            "Branch coverage (offline lane)",
            fmt("coverage.branch_rate", "{:.1%}"),
            "coverage.branch_rate",
        ),
        (
            "Integration tests",
            fmt("tests.integration.total", "{:g} tests"),
            "tests.integration.total",
        ),
        (
            "Golden replay pass rate",
            fmt("eval.golden_pass_rate", "{:.1%}"),
            "eval.golden_pass_rate",
        ),
        ("Mutation score", fmt("mutation.score", "{:g}%"), "mutation.score"),
        ("Image size", image_result(scorecard), "image.api_bytes"),
    ]


def baseline_rows(root: Path) -> list[tuple[str, str, str]]:
    """Rows read from committed baseline files: (check, result, repository path)."""
    rows = []
    golden_path = "evals/golden/manifest.json"
    golden = read_json(root / golden_path)
    if isinstance(golden, dict) and "item_count" in golden:
        locales = golden.get("counts", {}).get("locales", {})
        detail = ", ".join(f"{name.upper()} {n}" for name, n in locales.items())
        suffix = f" ({detail})" if detail else ""
        rows.append(("Golden set size", f"{golden['item_count']} items{suffix}", golden_path))
    attacks_path = "evals/attacks/manifest.json"
    attacks = read_json(root / attacks_path)
    if isinstance(attacks, dict) and "item_count" in attacks:
        rows.append(("Attack pack size", f"{attacks['item_count']} items", attacks_path))
    retrieval_path = "evals/baselines/retrieval.json"
    retrieval = read_json(root / retrieval_path)
    try:
        hybrid = retrieval["strategies"]["hybrid"]["overall"]["recall@5"]
        scored = retrieval["queries"]["scored"]
    except KeyError, TypeError:
        hybrid = scored = None
    if hybrid is not None:
        rows.append(
            (
                "Retrieval Recall@5 (hybrid baseline)",
                f"{hybrid:.3f} over {scored} scored queries",
                retrieval_path,
            )
        )
    return rows


def render_table(scorecard: dict, root: Path, snapshot: str) -> str:
    """Render the Markdown table; ``snapshot`` is the repository-relative scorecard path."""
    lines = [
        f"Generated by `scripts/readme_results.py` from [`{Path(snapshot).name}`]({snapshot}).",
        "",
        "| Check | Result | Source |",
        "|---|---|---|",
    ]
    for check, result, key in metric_rows(scorecard):
        lines.append(f"| {check} | {result or UNMEASURED} | [`{key}`]({snapshot}) |")
    for check, result, path in baseline_rows(root):
        lines.append(f"| {check} | {result} | [`{path}`]({path}) |")
    return "\n".join(lines)


def replace_block(readme: str, table: str) -> str:
    start, end = readme.find(START), readme.find(END)
    if start < 0 or end < start:
        raise ValueError(f"README must contain {START} before {END}")
    return f"{readme[: start + len(START)]}\n{table}\n{readme[end:]}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="update the README block")
    mode.add_argument("--check", action="store_true", help="exit 1 when the block drifted")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--readme", type=Path, default=None)
    parser.add_argument("--scorecard", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root
    readme_path = args.readme or root / "README.md"
    try:
        scorecard_path = args.scorecard or latest_snapshot(root)
        scorecard = json.loads(scorecard_path.read_text())
        try:
            snapshot = scorecard_path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            snapshot = scorecard_path.as_posix()
        current = readme_path.read_text()
        expected = replace_block(current, render_table(scorecard, root, snapshot))
    except (OSError, ValueError) as error:
        print(f"readme_results: {error}", file=sys.stderr)
        return 2
    if expected == current:
        print("README results table is current.")
        return 0
    if args.write:
        readme_path.write_text(expected)
        print(f"Updated {readme_path}.")
        return 0
    print(
        "README results table drifted; run `uv run python -m scripts.readme_results --write`.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
