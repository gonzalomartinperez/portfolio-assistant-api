"""Portfolio TypeScript source-format patterns used by retrieval, kept in one place."""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.application.knowledge import Chunk

_COMPANY = re.compile(r'company:\s*"([^"\n]+)"')
_ENTITY = re.compile(r'(?:slug|name):\s*"([^"\n]+)"')
_NAME = re.compile(r'name:\s*"([^"\n]+)"')
_STARTED_ON = re.compile(r'startedOn:\s*"(\d{4}-\d{2}-\d{2})"')


def is_profile_file(path: str) -> bool:
    """Identify a profile document by its path suffix."""
    return path.endswith("/profile.ts")


def is_experience_file(path: str) -> bool:
    """Identify an experience document by its path suffix."""
    return path.endswith("/experience.ts")


def is_education_file(path: str) -> bool:
    """Identify an education document by its path suffix."""
    return path.endswith("/education.ts")


def is_profile_head(chunk: Chunk) -> bool:
    """Check whether a chunk starts a profile document."""
    return is_profile_file(chunk.path) and chunk.start_line == 1


def is_education_head(chunk: Chunk) -> bool:
    """Check whether a chunk starts an education document."""
    return is_education_file(chunk.path) and chunk.start_line == 1


def has_language_entries(content: str) -> bool:
    """Check for a language field in the source text."""
    return "language:" in content


def has_contributions(content: str) -> bool:
    """Check for a contributions field in the source text."""
    return "contributions:" in content


def has_metric_entry(content: str) -> bool:
    """Check for both qualifier and value fields in the source text."""
    return "qualifier:" in content and "value:" in content


def has_started_on(content: str) -> bool:
    """Check for a role start-date field in the source text."""
    return "startedOn:" in content


def company_names(content: str) -> list[str]:
    """Extract quoted company fields in source order."""
    return _COMPANY.findall(content)


def first_company(content: str) -> re.Match[str] | None:
    """Find the first quoted company field, retaining its source span."""
    return _COMPANY.search(content)


def entity_names(content: str) -> list[str]:
    """Extract quoted slug and name fields in source order."""
    return _ENTITY.findall(content)


def declared_names(content: str) -> list[str]:
    """Extract quoted name fields in source order."""
    return _NAME.findall(content)


def role_text(content: str, company: re.Match[str], following: str | None) -> str:
    """Text of one role entry: after its company, through the adjacent chunk, up to the next."""
    text = content[company.end() :]
    if following is not None:
        text += "\n" + following
    return text.split("company:", 1)[0]


def role_start_date(text: str) -> str | None:
    """Return the first ISO-shaped role start date, if present."""
    match = _STARTED_ON.search(text)
    return match[1] if match else None
