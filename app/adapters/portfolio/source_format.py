"""Conservative extraction of explicit public TypeScript fields, never model facts."""

import re
from typing import TYPE_CHECKING

from app.domain.graph import Fact

if TYPE_CHECKING:
    from collections.abc import Mapping

_SLUG_SOURCES = {"/projects.ts": ("Project", "name"), "/experience.ts": ("Role", "company")}


def facts(path: str, content: str) -> tuple[Fact, ...]:
    for suffix, (kind, name_field) in _SLUG_SOURCES.items():
        if path.endswith(suffix):
            blocks = list(re.finditer(r'slug:\s*"([^"\n]+)"', content))[:20]
            return _record_facts(path, content, blocks, kind, name_field)
    if path.endswith("/education.ts"):
        return _education_facts(content)
    return ()


def _line(content: str, end: int) -> int:
    return content[:end].count("\n") + 1


def _education_facts(content: str) -> tuple[Fact, ...]:
    match = re.search(
        r'qualification:\s*"([^"\n]+)"[\s\S]{0,200}?institution:\s*"([^"\n]+)"',
        content,
    )
    if not match:
        return ()
    start = _line(content, match.start())
    end = _line(content, match.end())
    return (Fact("Education", match[1], "AT_INSTITUTION", "Institution", match[2], start, end),)


def _record_facts(
    path: str, content: str, blocks: list[re.Match[str]], kind: str, name_field: str
) -> tuple[Fact, ...]:
    result: list[Fact] = []
    for index, match in enumerate(blocks):
        offset = match.start()
        block = content[
            offset : blocks[index + 1].start() if index + 1 < len(blocks) else len(content)
        ]
        name = re.search(rf'{name_field}:\s*"([^"\n]+)"', block)
        if not name:
            continue
        subject = name[1]
        start = _line(content, offset + name.start())
        result.extend(_stack_facts(content, block, offset, kind, subject, start))
        result.extend(_contribution_facts(content, block, offset, kind, subject, start))
        if kind == "Project":
            # Identity evidence exists even when a reviewed source has no stack.
            result.append(
                Fact(kind, subject, "DOCUMENTED_IN", "PublicDocument", path, start, start)
            )
    return tuple(result)


def _stack_facts(
    content: str, block: str, offset: int, kind: str, subject: str, start: int
) -> list[Fact]:
    stack = re.search(r"stack:\s*technologyNames\(\[([\s\S]*?)\]\)", block)
    if not stack:
        return []
    return [
        Fact(
            kind,
            subject,
            "USES",
            "Technology",
            technology[1],
            start,
            _line(content, offset + stack.start(1) + technology.end()),
        )
        for technology in re.finditer(r'"([^"\n]+)"', stack[1])
    ]


def _contribution_facts(
    content: str, block: str, offset: int, kind: str, subject: str, start: int
) -> list[Fact]:
    contributions = re.search(r"contributions:\s*\[([\s\S]*?)\]", block)
    if not contributions:
        return []
    return [
        Fact(
            kind,
            subject,
            "CONTRIBUTED",
            "Contribution",
            contribution[1],
            start,
            _line(content, offset + contributions.start(1) + contribution.end()),
        )
        for contribution in list(re.finditer(r'"([^"\n]+)"', contributions[1]))[:20]
    ]


def facts_for(documents: Mapping[str, str]) -> dict[str, tuple[Fact, ...]]:
    return {path: facts(path, content) for path, content in documents.items()}
