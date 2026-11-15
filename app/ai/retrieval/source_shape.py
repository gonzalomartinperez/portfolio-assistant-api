"""Portfolio TypeScript source-format patterns used by retrieval, kept in one place."""

import re

from app.application.knowledge import Chunk

_COMPANY = re.compile(r'company:\s*"([^"\n]+)"')
_ENTITY = re.compile(r'(?:slug|name):\s*"([^"\n]+)"')
_NAME = re.compile(r'name:\s*"([^"\n]+)"')
_STARTED_ON = re.compile(r'startedOn:\s*"(\d{4}-\d{2}-\d{2})"')


def is_profile_file(path: str) -> bool:
    return path.endswith("/profile.ts")


def is_experience_file(path: str) -> bool:
    return path.endswith("/experience.ts")


def is_education_file(path: str) -> bool:
    return path.endswith("/education.ts")


def is_profile_head(chunk: Chunk) -> bool:
    return is_profile_file(chunk.path) and chunk.start_line == 1


def is_education_head(chunk: Chunk) -> bool:
    return is_education_file(chunk.path) and chunk.start_line == 1


def has_language_entries(content: str) -> bool:
    return "language:" in content


def has_contributions(content: str) -> bool:
    return "contributions:" in content


def has_metric_entry(content: str) -> bool:
    return "qualifier:" in content and "value:" in content


def has_started_on(content: str) -> bool:
    return "startedOn:" in content


def company_names(content: str) -> list[str]:
    return _COMPANY.findall(content)


def first_company(content: str) -> re.Match[str] | None:
    return _COMPANY.search(content)


def entity_names(content: str) -> list[str]:
    return _ENTITY.findall(content)


def declared_names(content: str) -> list[str]:
    return _NAME.findall(content)


def role_text(content: str, company: re.Match[str], following: str | None) -> str:
    """Text of one role entry: after its company, through the adjacent chunk, up to the next."""
    text = content[company.end() :]
    if following is not None:
        text += "\n" + following
    return text.split("company:", 1)[0]


def role_start_date(text: str) -> str | None:
    match = _STARTED_ON.search(text)
    return match[1] if match else None
