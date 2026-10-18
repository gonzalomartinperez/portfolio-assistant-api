"""Strict optional portfolio projection: approved facts, not executable source content."""

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PublicText(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    en: str = Field(min_length=1, max_length=8000)
    es: str = Field(min_length=1, max_length=8000)


class PublicMetric(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    value: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=100)
    qualifier: PublicText
    baseline: PublicText | None = None


class PublicFact(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str = Field(pattern=r'^[a-z0-9][a-z0-9-]{0,79}$')
    subject: PublicText
    topic: Literal[
        'profile', 'experience', 'projects', 'education', 'achievement', 'personal'
    ]
    text: PublicText
    verified_on: date
    source_path: str = Field(
        pattern=r'^src/content/(en|es)/(profile|experience|projects|education)\.ts$'
    )
    start_line: int = Field(ge=1, le=10000)
    end_line: int = Field(ge=1, le=10000)
    technologies: list[str] = Field(default_factory=list, max_length=30)
    attribution: Literal['personal', 'team', 'context']
    metric: PublicMetric | None = None

    @model_validator(mode='after')
    def valid_span(self):
        if len(self.model_dump_json().encode('utf-8')) > 7000:
            raise ValueError('public fact exceeds embedding input bound')
        if self.end_line < self.start_line:
            raise ValueError('invalid source span')
        if any(
            not re.fullmatch(r'[\w .+#/-]{1,80}', technology)
            for technology in self.technologies
        ):
            raise ValueError('invalid technology label')
        return self


class PersonalProfile(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    city: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=1, max_length=100)
    nationality: PublicText | None = None
    age: int | None = Field(default=None, ge=18, le=120)
    age_as_of: date | None = None

    @model_validator(mode='after')
    def age_is_dated(self):
        if (self.age is None) != (self.age_as_of is None):
            raise ValueError('age requires its reference date')
        return self


class PublicProjection(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: Literal['1']
    facts: list[PublicFact] = Field(min_length=1, max_length=300)
    personal: PersonalProfile | None = None

    @model_validator(mode='after')
    def unique_facts(self):
        if len({fact.id for fact in self.facts}) != len(self.facts):
            raise ValueError('duplicate public fact identity')
        return self


def graph_facts(projection: PublicProjection, documents: dict[str, str]):
    from app.domain.graph import Fact

    result = {}
    for fact in projection.facts:
        source = documents.get(fact.source_path)
        if source is None or fact.end_line > len(source.splitlines()):
            raise ValueError('public fact must reference a committed approved span')
        kind = {
            'projects': 'Project',
            'experience': 'Role',
            'education': 'Education',
        }.get(fact.topic, 'Person')
        edges = [
            Fact(
                kind,
                fact.subject.en,
                'CONTRIBUTED' if fact.attribution == 'personal' else 'DOCUMENTED_IN',
                'Contribution' if fact.attribution == 'personal' else 'PublicFact',
                fact.text.en,
                fact.start_line,
                fact.end_line,
            )
        ]
        edges.extend(
            Fact(
                kind,
                fact.subject.en,
                'USES',
                'Technology',
                technology,
                fact.start_line,
                fact.end_line,
            )
            for technology in fact.technologies
        )
        result.setdefault(fact.source_path, []).extend(edges)
    return result
