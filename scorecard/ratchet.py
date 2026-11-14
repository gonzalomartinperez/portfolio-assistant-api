"""Ratchet files: per-metric direction, regression check and tighten-only rewrite."""

import json
from pathlib import Path

DIRECTIONS = ('lower', 'higher')


def load_ratchets(directory: Path) -> dict[Path, dict]:
    return {p: json.loads(p.read_text()) for p in sorted(directory.glob('*.json'))}


def limit(entry: dict, root: Path) -> float | None:
    """Return the ratchet value, resolving a `pointer` into another JSON file."""
    pointer = entry.get('pointer')
    if pointer:
        data = json.loads((root / pointer['file']).read_text())
        return data.get(pointer['key'])
    return entry.get('value')


def worse(direction: str, current: float, bound: float) -> bool:
    return current > bound if direction == 'lower' else current < bound


def check(current: dict, directory: Path, root: Path) -> list[dict]:
    rows = []
    for ratchets in load_ratchets(directory).values():
        for key, entry in ratchets['metrics'].items():
            bound = limit(entry, root)
            value = current.get('metrics', {}).get(key, {}).get('value')
            if bound is None:
                status = 'unseeded'
            elif value is None:
                status = 'unmet'
            elif worse(entry['direction'], value, bound):
                status = 'regressed'
            else:
                status = 'ok'
            rows.append(
                {
                    'metric': key,
                    'direction': entry['direction'],
                    'ratchet': bound,
                    'current': value,
                    'status': status,
                }
            )
    return rows


def format_table(rows: list[dict]) -> str:
    lines = [f'{"metric":38} {"dir":6} {"ratchet":>12} {"current":>12}  status']
    for r in rows:
        lines.append(
            f'{r["metric"]:38} {r["direction"]:6} {r["ratchet"]!s:>12} '
            f'{r["current"]!s:>12}  {r["status"]}'
        )
    return '\n'.join(lines)


def tighten(current: dict, directory: Path, root: Path) -> list[str]:
    """Rewrite ratchets only where the measured value is better or newly seeded."""
    changes = []
    for path, ratchets in load_ratchets(directory).items():
        changed = False
        for key, entry in ratchets['metrics'].items():
            if 'pointer' in entry:
                continue  # owned by the file it points to
            value = current.get('metrics', {}).get(key, {}).get('value')
            bound = entry.get('value')
            if value is None or (
                bound is not None and not worse(entry['direction'], bound, value)
            ):
                continue
            entry['value'] = value
            changes.append(f'{key}: {bound} -> {value}')
            changed = True
        if changed:
            path.write_text(json.dumps(ratchets, indent=2) + '\n')
    return changes
