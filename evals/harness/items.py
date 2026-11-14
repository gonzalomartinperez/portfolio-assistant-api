"""Eval item schema (assistant-quality.md section 4), validated by pydantic and JSON Schema."""

import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.domain.portfolio_paths import EVIDENCE_KEY_PATTERN

SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'schema' / 'item.schema.json'
GRADER_NAMES = (
    'language_is',
    'citations_in_retrieved',
    'citation_urls_allowlisted',
    'numbers_grounded',
    'forbidden_claims_absent',
    'abstains',
    'required_facts_present',
    'no_canary',
    'third_person_attribution',
    'retrieval_gold_in_topk',
    'budget_respected',
)
ASSERTION_NAMES = (*GRADER_NAMES, 'citations_empty', 'citations_nonempty')
_LANGUAGE_ASSERTION = re.compile(r'language_is:(en|es)')
_EVIDENCE_KEY = re.compile(EVIDENCE_KEY_PATTERN)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Turn(Strict):
    role: Literal['user'] = 'user'
    text: Text


class Match(Strict):
    id: Annotated[str, StringConstraints(pattern=r'^[a-z0-9][a-z0-9_-]*$')]
    match: Text


class Quarantine(Strict):
    issue: Text
    owner: Text
    deadline: date


class Item(Strict):
    id: Annotated[str, StringConstraints(pattern=r'^[a-z0-9][a-z0-9-]*$')]
    schema_version: Literal['1'] = '1'
    assistant: Literal['portfolio'] = 'portfolio'
    locale: Literal['en', 'es']
    strata: Annotated[list[Text], Field(min_length=1)]
    turns: Annotated[list[Turn], Field(min_length=1)]
    expected_behavior: Literal['answer', 'abstain', 'refuse', 'clarify']
    required_facts: list[Match] = []
    forbidden_claims: list[Match] = []
    gold_evidence_ids: list[str] = []
    assertions: Annotated[list[str], Field(min_length=1)]
    judge_rubric_id: str | None = None
    provenance: Text
    reviewer: Text
    created: date
    last_verified: date
    corpus_snapshot_id: Text
    status: Literal['active', 'quarantined', 'retired'] = 'active'
    quarantine: Quarantine | None = None
    retired_reason: Text | None = None
    # Assistant-experience strata (tools, memory): permissive JSON, typed as JSON values.
    tools: dict[str, JsonValue] | None = None
    memory_fixture: dict[str, JsonValue] | None = None

    @field_validator('gold_evidence_ids')
    @classmethod
    def _canonical_keys(cls, keys: list[str]) -> list[str]:
        for key in keys:
            if _EVIDENCE_KEY.fullmatch(key) is None:
                raise ValueError(f'not a canonical evidence key: {key!r}')
        return keys

    @field_validator('assertions')
    @classmethod
    def _closed_assertions(cls, names: list[str]) -> list[str]:
        for name in names:
            if name not in ASSERTION_NAMES and not _LANGUAGE_ASSERTION.fullmatch(name):
                raise ValueError(f'unknown assertion: {name!r}')
        if len(set(names)) != len(names):
            raise ValueError('duplicate assertion')
        return names

    @model_validator(mode='after')
    def _status_fields(self) -> Self:
        if (self.status == 'quarantined') != (self.quarantine is not None):
            raise ValueError(
                'quarantine is required exactly when status is quarantined'
            )
        if (self.status == 'retired') != (self.retired_reason is not None):
            raise ValueError(
                'retired_reason is required exactly when status is retired'
            )
        return self

    @model_validator(mode='after')
    def _consistent_content(self) -> Self:
        if self.expected_behavior == 'abstain' and 'abstains' not in self.assertions:
            raise ValueError('abstain items must assert abstains')
        if (
            self.expected_behavior == 'answer'
            and 'citations_nonempty' not in self.assertions
        ):
            raise ValueError('answer items must assert citations_nonempty')
        for name in self.assertions:
            if name.startswith('language_is:') and name[-2:] != self.locale:
                raise ValueError(f'{name} contradicts locale {self.locale}')
        for label, ids in (
            ('required_facts', [f.id for f in self.required_facts]),
            ('forbidden_claims', [c.id for c in self.forbidden_claims]),
            ('gold_evidence_ids', self.gold_evidence_ids),
        ):
            if len(set(ids)) != len(ids):
                raise ValueError(f'duplicate ids in {label}')
        return self


class SealedItem(Item):
    """An item of the sealed holdout: its repr never shows the questions or answers."""

    def __repr__(self) -> str:
        return '<SealedItem redacted>'

    __str__ = __repr__

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return []


def normalized_question(item: Item) -> str:
    """Casefolded, accent-free, punctuation-free text of the scripted turns."""
    text = ' || '.join(turn.text for turn in item.turns)
    text = unicodedata.normalize('NFKD', text.casefold())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[\W_]+', ' ', text).strip()


def generate_schema() -> dict[str, object]:
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        **Item.model_json_schema(),
    }


def schema_text() -> str:
    return json.dumps(generate_schema(), indent=2, sort_keys=True) + '\n'


if __name__ == '__main__':
    SCHEMA_PATH.write_text(schema_text())
