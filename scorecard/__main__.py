"""Command line: collect, check and tighten."""

import argparse
import json
import sys
from pathlib import Path

from scorecard.collect import collect
from scorecard.ratchet import check, format_table, tighten


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m scorecard')
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('collect', help='aggregate artifacts into scorecard.json')
    c.add_argument('--artifacts', type=Path, default=Path('artifacts'))
    c.add_argument('--out', type=Path, default=Path('artifacts/scorecard.json'))
    c.add_argument('--root', type=Path, default=Path('.'))
    for name in ('check', 'tighten'):
        p = sub.add_parser(name)
        p.add_argument('--current', type=Path, required=True)
        p.add_argument('--ratchets', type=Path, default=Path('scorecard/ratchets'))
        p.add_argument('--root', type=Path, default=Path('.'))
        if name == 'check':
            p.add_argument('--strict', action='store_true', help='unmet also fails')
    args = parser.parse_args(argv)
    if args.command == 'collect':
        result = collect(args.artifacts, args.root)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        print(f'wrote {args.out}')
        return 0
    current = load(args.current)
    if args.command == 'check':
        rows = check(current, args.ratchets, args.root)
        print(format_table(rows))
        bad = {'regressed', 'unmet'} if args.strict else {'regressed'}
        return 1 if any(r['status'] in bad for r in rows) else 0
    for line in tighten(current, args.ratchets, args.root):
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
