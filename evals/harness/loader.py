"""Load and validate JSONL eval items with file:line diagnostics."""

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from evals.harness.items import Item, SealedItem, normalized_question


class ItemLoadError(ValueError):
    """One or more lines are invalid; the message lists every problem."""


def load_items(path: Path, *, sealed: bool = False) -> list[Item]:
    """Load and validate; ``sealed`` yields items whose repr is redacted."""
    model = SealedItem if sealed else Item
    items: list[Item] = []
    errors: list[str] = []
    ids: dict[str, int] = {}
    questions: dict[str, tuple[int, str]] = {}
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        where = f'{path}:{number}'
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f'{where}: invalid JSON ({error.msg})')
            continue
        label = raw.get('id', '?') if isinstance(raw, dict) else '?'
        try:
            item = model.model_validate(raw)
        except ValidationError as error:
            for problem in error.errors(include_input=False):
                field = '.'.join(str(part) for part in problem['loc']) or 'item'
                errors.append(f'{where}: item {label}: {field}: {problem["msg"]}')
            continue
        if item.id in ids:
            errors.append(
                f'{where}: item {item.id}: duplicate id (first at line {ids[item.id]})'
            )
            continue
        ids[item.id] = number
        question = normalized_question(item)
        if question in questions:
            first, other = questions[question]
            errors.append(
                f'{where}: item {item.id}: duplicate question of {other} (line {first})'
            )
            continue
        questions[question] = (number, item.id)
        items.append(item)
    if errors:
        raise ItemLoadError('\n'.join(errors))
    return items


@dataclass(frozen=True)
class SealedAggregate:
    """The only view of the sealed holdout (assistant-quality.md section 6.2): numbers."""

    sha256: str
    total: int
    by_part: dict[str, int]
    by_locale: dict[str, int]


def sealed_aggregate(path: Path) -> SealedAggregate:
    """Validate the sealed file and return counts and its hash; never the items or their ids."""
    items = load_items(path, sealed=True)
    return SealedAggregate(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        total=len(items),
        by_part=dict(sorted(Counter(i.strata[0] for i in items).items())),
        by_locale=dict(sorted(Counter(i.locale for i in items).items())),
    )
