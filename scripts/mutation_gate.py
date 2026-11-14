"""Evaluate mutmut 3.8.1 per-group results and select scoped PR source files."""

import argparse
import json
import os
import re
import subprocess
import tomllib
from collections import Counter
from datetime import date
from pathlib import Path

STATUSES = {
    'killed',
    'survived',
    'timeout',
    'no tests',
    'skipped',
    'suspicious',
    'check was interrupted by user',
    'segfault',
    'not checked',
    'caught by type check',
}


def parse_results(output: str) -> dict[str, Counter[str]]:
    """Parse `mutmut results --all true`; never credit inconclusive outcomes."""
    groups: dict[str, Counter[str]] = {}
    seen: set[str] = set()
    for line in output.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r'\s*(\S+): ([a-z ]+)\s*', line)
        if not match:
            raise ValueError(f'Invalid mutation result: {line!r}')
        name, status = match.groups()
        if status not in STATUSES or name in seen:
            raise ValueError(f'Unknown status or duplicate mutant: {name}')
        seen.add(name)
        if name.startswith('evals.harness.graders.'):
            group = 'graders'
        elif name.startswith(('app.domain.', 'app.application.', 'app.ai.')):
            group = name.split('.')[1]
        else:
            raise ValueError(f'Unscoped mutant: {name}')
        # A restricted run generates unchecked mutants outside the requested names.
        if status != 'not checked':
            groups.setdefault(group, Counter())[status] += 1
    if not groups:
        raise ValueError('No measured mutation results')
    return groups


def evaluate(
    groups: dict[str, Counter[str]],
    baseline: dict,
    today: date,
    *,
    warn: bool = False,
    enforce: bool = False,
) -> tuple[list[str], bool]:
    """Warn only within the committed grace period; --enforce always wins."""
    deadline = date.fromisoformat(baseline['warn_until'])
    if not date(2026, 11, 14) <= deadline <= date(2026, 11, 28):
        raise ValueError('Warning deadline must be within the 14-day rollout')
    advisory = not enforce and today <= deadline
    # Explicit warn documents CI intent but cannot extend the grace period.
    mode = 'WARN' if advisory else 'FAIL'
    messages = []
    failed = False
    for group, counts in sorted(groups.items()):
        spec = baseline['groups'][group]
        score = (
            100
            * (counts['killed'] + counts['caught by type check'])
            / sum(counts.values())
        )
        floor = max(60, baseline['break'], spec['ratchet'] or 0)
        shortfall = max(0.0, floor - score)
        messages.append(
            f'{group}: {score:.2f}% ({dict(counts)}); floor {floor:.2f}, '
            f'target {spec["target"]}; {mode if shortfall else "PASS"} '
            f'shortfall {shortfall:.2f}'
        )
        failed |= bool(shortfall) and not advisory
    return messages, failed


def changed_scope(paths: list[str], configured: list[str]) -> list[str]:
    """Select only existing Python source files explicitly in the mutation scope."""
    return sorted(set(paths) & set(configured))


def select_changed(base: str) -> None:
    """Narrow this disposable CI checkout before mutmut generates any mutants."""
    path = Path('pyproject.toml')
    text = path.read_text()
    configured = tomllib.loads(text)['tool']['mutmut']['paths_to_mutate']
    diff = subprocess.run(
        ['git', 'diff', '--name-only', '--diff-filter=ACMR', '-z', f'{base}...HEAD'],
        check=True,
        capture_output=True,
        text=True,
    )
    selected = changed_scope(diff.stdout.rstrip('\0').split('\0'), configured)
    if selected:
        text = re.sub(
            r'(?m)^paths_to_mutate = \[.*?\]',
            'paths_to_mutate = ' + json.dumps(selected),
            text,
            count=1,
            flags=re.DOTALL,
        )
        path.write_text(text)
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write(f'has_changes={str(bool(selected)).lower()}\n')
    print(f'Mutation scope: {selected or "no changed scoped Python files; skipped"}')


def main() -> int:
    """Read results or narrow a CI checkout, without importing mutmut."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--results', type=Path, default=Path('artifacts/mutation-results.txt')
    )
    parser.add_argument(
        '--baseline', type=Path, default=Path('tests/mutation-baseline.json')
    )
    parser.add_argument(
        '--warn', action='store_true', default=os.getenv('MUTATION_MODE') == 'warn'
    )
    parser.add_argument('--enforce', action='store_true')
    parser.add_argument('--select-changed')
    args = parser.parse_args()
    if args.select_changed:
        select_changed(args.select_changed)
        return 0
    try:
        messages, failed = evaluate(
            parse_results(args.results.read_text()),
            json.loads(args.baseline.read_text()),
            date.today(),
            warn=args.warn,
            enforce=args.enforce,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Mutation evidence invalid: {error}')
        return 1
    print('\n'.join(messages))
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
