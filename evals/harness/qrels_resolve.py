"""Merge two independent label files into ``qrels.jsonl`` and report agreement.

Input rows (JSONL, one per query and candidate key): ``{"query_id", "key", "relevance"}``
with relevance in 0, 1, 2. Labeller A and labeller B label independently over the same
(query, key) pairs; wherever they agree the label stands, and every disagreement needs a
row in the resolution file (the third labeller, optionally with a ``rationale``). The
output ``qrels.jsonl`` holds one resolved row per pair; the stats file holds the raw
agreement rate and Cohen's kappa (unweighted, three levels, and binary relevant/not).

Usage: ``uv run python -m evals.harness.qrels_resolve --a A.jsonl --b B.jsonl
--resolution C.jsonl --out evals/retrieval/qrels.jsonl --stats stats.json``
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from app.domain.portfolio_paths import EVIDENCE_KEY_PATTERN

LEVELS = (0, 1, 2)
_KEY = re.compile(EVIDENCE_KEY_PATTERN)

Pair = tuple[str, str]


class QrelsError(ValueError):
    """Label files are inconsistent; the message lists every problem."""


def read_labels(path: Path) -> dict[Pair, int]:
    labels: dict[Pair, int] = {}
    problems: list[str] = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        where = f'{path}:{number}'
        try:
            row = json.loads(line)
            pair = (str(row['query_id']), str(row['key']))
            level = row['relevance']
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            problems.append(f'{where}: unreadable row ({error})')
            continue
        if isinstance(level, bool) or level not in LEVELS:
            problems.append(f'{where}: relevance must be 0, 1 or 2, got {level!r}')
            continue
        if not _KEY.fullmatch(pair[1]):
            problems.append(f'{where}: invalid evidence key {pair[1]!r}')
            continue
        if pair in labels:
            problems.append(f'{where}: duplicate label for {pair[0]} {pair[1]}')
            continue
        labels[pair] = level
    if problems:
        raise QrelsError('\n'.join(problems))
    return labels


def cohen_kappa(first: list[int], second: list[int]) -> float:
    """Unweighted Cohen's kappa; 1.0 when both labellers use one identical label."""
    if len(first) != len(second):
        raise ValueError('label lists must have the same length')
    total = len(first)
    if total == 0:
        raise ValueError('no labels to compare')
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / total
    count_a = Counter(first)
    count_b = Counter(second)
    expected = sum(count_a[c] * count_b[c] for c in set(count_a) | set(count_b)) / (
        total * total
    )
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return (observed - expected) / (1 - expected)


def resolve(
    labels_a: dict[Pair, int],
    labels_b: dict[Pair, int],
    resolution: dict[Pair, int],
) -> tuple[dict[Pair, int], dict[str, Any]]:
    """Return the resolved labels and the agreement statistics."""
    problems: list[str] = []
    only_a = sorted(set(labels_a) - set(labels_b))
    only_b = sorted(set(labels_b) - set(labels_a))
    if only_a:
        problems.append(f'{len(only_a)} pairs only labelled by A, e.g. {only_a[:3]}')
    if only_b:
        problems.append(f'{len(only_b)} pairs only labelled by B, e.g. {only_b[:3]}')
    pairs = sorted(set(labels_a) & set(labels_b))
    disagreements = [p for p in pairs if labels_a[p] != labels_b[p]]
    unresolved = [p for p in disagreements if p not in resolution]
    if unresolved:
        problems.append(
            f'{len(unresolved)} disagreements without a resolution, e.g. {unresolved[:3]}'
        )
    stray = sorted(set(resolution) - set(disagreements))
    if stray:
        problems.append(
            f'{len(stray)} resolution rows for pairs without a disagreement, e.g. {stray[:3]}'
        )
    if problems:
        raise QrelsError('\n'.join(problems))
    if not pairs:
        raise QrelsError('no labelled pairs')
    resolved = {p: resolution.get(p, labels_a[p]) for p in pairs}
    first = [labels_a[p] for p in pairs]
    second = [labels_b[p] for p in pairs]
    agreed = len(pairs) - len(disagreements)
    stats: dict[str, Any] = {
        'pairs': len(pairs),
        'queries': len({q for q, _ in pairs}),
        'agreed': agreed,
        'disagreements': len(disagreements),
        'agreement_rate': round(agreed / len(pairs), 4),
        'cohen_kappa': round(cohen_kappa(first, second), 4),
        'cohen_kappa_binary': round(
            cohen_kappa([int(a > 0) for a in first], [int(b > 0) for b in second]), 4
        ),
        'labels_a': dict(sorted(Counter(first).items())),
        'labels_b': dict(sorted(Counter(second).items())),
        'resolved': dict(sorted(Counter(resolved.values()).items())),
    }
    return resolved, stats


def dump_qrels(resolved: dict[Pair, int]) -> str:
    return ''.join(
        json.dumps({'query_id': q, 'key': k, 'relevance': level}, ensure_ascii=False)
        + '\n'
        for (q, k), level in sorted(resolved.items())
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--a', type=Path, required=True)
    parser.add_argument('--b', type=Path, required=True)
    parser.add_argument('--resolution', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--stats', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        resolution = read_labels(args.resolution) if args.resolution else {}
        resolved, stats = resolve(read_labels(args.a), read_labels(args.b), resolution)
    except QrelsError as error:
        print(error, file=sys.stderr)
        return 1
    args.out.write_text(dump_qrels(resolved), encoding='utf-8')
    args.stats.write_text(
        json.dumps(stats, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
