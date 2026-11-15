"""Measure skill activation with a router model; local tool, never run in CI.

For every skill, each query in `evals/triggers.json` is sent to a router model in a
clean context (a fresh `claude -p --model haiku` process in an empty directory, no tools,
no repository instructions). The prompt lists every skill's `name: description` and the
query; the model answers with the one skill it would load, or `none`. A positive query
passes when the fraction of runs that pick the skill is at least 0.5, a negative query
when that fraction is below 0.5. Calls use the owner's Claude subscription, never an API
key. Standard library only.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
THRESHOLD = 0.5
SPLITS = ("train", "validation")
ERROR = "<error>"
PROVIDER_SWITCHES = frozenset(
    {"CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"}
)
ROUTER_SYSTEM = "You are a skill router. Follow the instructions in the user message exactly."
ROUTER_COMMAND = (
    "claude",
    "-p",
    "--model",
    "haiku",
    "--max-turns",
    "1",
    "--tools",
    "",
    "--disable-slash-commands",
    "--no-session-persistence",
    "--setting-sources",
    "",
    "--system-prompt",
    ROUTER_SYSTEM,
)


def scalar(value: str) -> str:
    """Decode one single-line YAML scalar (double-quoted, single-quoted or plain)."""
    value = value.strip()
    if value.startswith('"'):
        return str(json.loads(value))
    if value.startswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def read_skill(path: Path) -> tuple[str, str]:
    """Return `(name, description)` from a SKILL.md with single-line frontmatter values."""
    front = re.match(r"\A---\n(.*?)\n---\n", path.read_text(), re.DOTALL)
    if front is None:
        raise ValueError(f"{path}: missing frontmatter")
    fields = dict(re.findall(r"^(name|description):[ \t]*(.+)$", front[1], re.MULTILINE))
    if set(fields) != {"name", "description"}:
        raise ValueError(f"{path}: name and description must be single-line values")
    return scalar(fields["name"]), scalar(fields["description"])


def load_catalog(root: Path = SKILLS) -> dict[str, str]:
    """Map every skill name to its description, sorted by name."""
    pairs = (read_skill(folder / "SKILL.md") for folder in sorted(root.iterdir()))
    return dict(sorted(pairs))


def build_prompt(catalog: dict[str, str], query: str) -> str:
    """Build the router prompt: every skill, the request, and the answer format."""
    listing = "\n".join(f"- {name}: {text}" for name, text in catalog.items())
    return (
        "An agent has these skills. Each entry is `name: description`.\n\n"
        f"{listing}\n\n"
        "A user sends the request below in a fresh session. Decide which single skill "
        "you would load to handle it. Use the descriptions only. Answer with the exact "
        "skill name and nothing else, or `none` if no skill applies.\n\n"
        f"Request: {query}\n"
    )


def parse_answer(answer: str, names: list[str]) -> str:
    """Return the skill name the model chose, or `none` (also for unknown answers)."""
    text = answer.strip().lower()
    pattern = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    found = re.search(rf"(?<![a-z0-9-])({pattern}|none)(?![a-z0-9-])", text)
    return found[1] if found else "none"


def fraction(picks: list[str], skill: str) -> float | None:
    """Fraction of valid runs that picked the skill; failed calls are excluded, none valid is None."""
    valid = [pick for pick in picks if pick != ERROR]
    return sum(pick == skill for pick in valid) / len(valid) if valid else None


def judge(should_trigger: bool, share: float) -> bool:
    """Positive passes at 0.5 or more, negative below 0.5."""
    return (share >= THRESHOLD) == should_trigger


def summarize(rows: list[dict]) -> dict:
    """Confusion counts and precision, recall, accuracy for one set of scored queries.

    Queries whose every router call failed have no fraction; they are counted in `errored` and
    left out of every ratio instead of being scored as "not triggered".
    """
    errored = sum(r["triggered_fraction"] is None for r in rows)
    rows = [r for r in rows if r["triggered_fraction"] is not None]
    tp = sum(r["should_trigger"] and r["triggered_fraction"] >= THRESHOLD for r in rows)
    fn = sum(r["should_trigger"] and r["triggered_fraction"] < THRESHOLD for r in rows)
    fp = sum(not r["should_trigger"] and r["triggered_fraction"] >= THRESHOLD for r in rows)
    tn = sum(not r["should_trigger"] and r["triggered_fraction"] < THRESHOLD for r in rows)
    ratio = lambda top, bottom: round(top / bottom, 4) if bottom else None
    return {
        "queries": len(rows),
        "errored": errored,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "accuracy": ratio(tp + tn, len(rows)),
    }


def score_skill(skill: str, queries: list[dict], picks: dict[str, list[str]]) -> dict:
    """Score every query of one skill and summarize per split."""
    rows = []
    for item in queries:
        runs = picks[item["query"]]
        share = fraction(runs, skill)
        rows.append(
            {
                "query": item["query"],
                "split": item["split"],
                "should_trigger": item["should_trigger"],
                "triggered_fraction": None if share is None else round(share, 4),
                "picks": runs,
                "errors": runs.count(ERROR),
                "passed": None if share is None else judge(item["should_trigger"], share),
            }
        )
    return {
        "errors": sum(r["errors"] for r in rows),
        "splits": {s: summarize([r for r in rows if r["split"] == s]) for s in SPLITS},
        "queries": rows,
    }


def overall(skills: dict[str, dict], split: str) -> dict:
    """Pool the counts of every skill for one split."""
    pooled = [
        {
            "should_trigger": row["should_trigger"],
            "triggered_fraction": row["triggered_fraction"],
        }
        for entry in skills.values()
        for row in entry["queries"]
        if row["split"] == split
    ]
    return summarize(pooled)


def merge(existing: dict | None, fresh: dict) -> dict:
    """Merge a new run into an earlier file: keep each skill's `first`, replace `final`."""
    skills: dict[str, dict] = {}
    previous = (existing or {}).get("skills", {})
    for name, entry in fresh["skills"].items():
        first = previous[name]["first"] if name in previous else entry["final"]
        skills[name] = {"first": first, "final": entry["final"]}
    for name, entry in previous.items():
        skills.setdefault(name, entry)
    return {**fresh, "skills": dict(sorted(skills.items()))}


def router_env(environ: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for the router CLI without any Anthropic API credential or endpoint override.

    Dropping every `ANTHROPIC_*` variable (API key, auth token, base URL) and the third-party
    provider switches leaves only the logged-in subscription, so a stray key can never be billed.
    """
    source = os.environ if environ is None else environ
    return {
        name: value
        for name, value in source.items()
        if not name.startswith("ANTHROPIC_") and name not in PROVIDER_SWITCHES
    }


def ask_router(prompt: str, timeout: int = 180, attempts: int = 2) -> str:
    """Send one prompt to a fresh router process in an empty directory; ERROR when every attempt fails."""
    for _ in range(attempts):
        with tempfile.TemporaryDirectory() as empty:
            try:
                done = subprocess.run(
                    ROUTER_COMMAND,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    cwd=empty,
                    env=router_env(),
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                continue
        if done.returncode == 0 and done.stdout.strip():
            return done.stdout
    return ERROR


def load_queries(skill: str, root: Path = SKILLS) -> tuple[list[dict], int]:
    """Read one skill's trigger queries and its runs_per_query."""
    data = json.loads((root / skill / "evals" / "triggers.json").read_text())
    if data["skill"] != skill:
        raise ValueError(f"{skill}: triggers.json names {data['skill']}")
    return data["queries"], int(data["runs_per_query"])


def run(args: argparse.Namespace) -> dict:
    catalog = load_catalog()
    names = list(catalog)
    chosen = args.skills or names
    unknown = sorted(set(chosen) - set(names))
    if unknown:
        raise SystemExit(f"unknown skills: {', '.join(unknown)}")
    wanted = SPLITS if args.split == "all" else (args.split,)
    jobs: list[tuple[str, str, int]] = []
    queries: dict[str, list[dict]] = {}
    for skill in chosen:
        items, runs = load_queries(skill)
        queries[skill] = [i for i in items if i["split"] in wanted]
        jobs += [(skill, i["query"], n) for i in queries[skill] for n in range(args.runs or runs)]
    if args.dry_run:
        first = queries[chosen[0]][0]["query"]
        print(build_prompt(catalog, first))
        print(f"[dry run] {len(jobs)} router calls for {len(chosen)} skills")
        raise SystemExit(0)

    def call(job: tuple[str, str, int]) -> str:
        raw = ask_router(build_prompt(catalog, job[1]))
        return ERROR if raw == ERROR else parse_answer(raw, names)

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        answers = list(pool.map(call, jobs))
    picks: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for (skill, query, _), answer in zip(jobs, answers, strict=True):
        picks[skill][query].append(answer)
    skills = {}
    for skill in chosen:
        scored = score_skill(skill, queries[skill], picks[skill])
        digest = hashlib.sha256(catalog[skill].encode()).hexdigest()[:12]
        scored["description_sha256"] = digest
        skills[skill] = {"final": scored}
    return {
        "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "router_model": "haiku via claude -p (subscription, no API key)",
        "split": args.split,
        "runs_override": args.runs,
        "threshold": THRESHOLD,
        "errors": sum(entry["final"]["errors"] for entry in skills.values()),
        "skills": skills,
    }


def table(results: dict, split: str = "validation") -> str:
    """Markdown table of first and final numbers for one split."""
    fmt = lambda value: "n/a" if value is None else f"{value:.2f}"
    lines = [
        "| Skill | First acc | Final acc | Precision | Recall | Queries |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, entry in results["skills"].items():
        first = entry["first"]["splits"][split]
        final = entry["final"]["splits"][split]
        lines.append(
            f"| `{name}` | {fmt(first['accuracy'])} | {fmt(final['accuracy'])} | "
            f"{fmt(final['precision'])} | {fmt(final['recall'])} | {final['queries']} |"
        )
    first_all = overall({n: e["first"] for n, e in results["skills"].items()}, split)
    final_all = overall({n: e["final"] for n, e in results["skills"].items()}, split)
    lines.append(
        f"| **overall** | {fmt(first_all['accuracy'])} | {fmt(final_all['accuracy'])} | "
        f"{fmt(final_all['precision'])} | {fmt(final_all['recall'])} | "
        f"{final_all['queries']} |"
    )
    return "\n".join(lines) + "\n"


def finish(fresh: dict, out: Path) -> dict:
    """Merge with an existing file, add overall numbers and write the JSON."""
    existing = json.loads(out.read_text()) if out.exists() else None
    for entry in fresh["skills"].values():
        entry["first"] = entry["final"]
    merged = merge(existing, fresh)
    for label in ("first", "final"):
        merged[f"overall_{label}"] = {
            s: overall({n: e[label] for n, e in merged["skills"].items()}, s) for s in SPLITS
        }
    merged["errors_in_file"] = sum(
        entry["final"].get("errors", 0) for entry in merged["skills"].values()
    )
    out.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", nargs="+", help="subset of skill names")
    parser.add_argument("--split", choices=(*SPLITS, "all"), default="validation")
    parser.add_argument("--runs", type=int, help="override runs_per_query")
    parser.add_argument("--jobs", type=int, default=4, help="parallel router calls")
    parser.add_argument("--out", type=Path, help="JSON result path (merged if present)")
    parser.add_argument("--markdown", type=Path, help="write the validation table")
    parser.add_argument("--dry-run", action="store_true", help="print one prompt only")
    args = parser.parse_args(argv)
    if not args.dry_run and args.out is None:
        parser.error("--out is required unless --dry-run")
    result = run(args)
    merged = finish(result, args.out)
    print(table(merged))
    if args.markdown:
        args.markdown.write_text(table(merged))
    if result["errors"]:
        print(
            f"error: {result['errors']} router calls failed; they are excluded from the "
            "fractions and the run is not valid evidence until they are re-run",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
