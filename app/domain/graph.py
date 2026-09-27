"""Conservative extraction of explicit public TypeScript fields, never model facts."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Fact:
    subject_kind: str
    subject: str
    predicate: str
    object_kind: str
    object: str
    start_line: int
    end_line: int


def facts(path: str, content: str) -> tuple[Fact, ...]:
    result: list[Fact] = []
    if path.endswith('/projects.ts'):
        blocks = list(re.finditer(r'slug:\s*"([^"\n]+)"', content))[:20]
        kind, name_field = 'Project', 'name'
    elif path.endswith('/experience.ts'):
        blocks = list(re.finditer(r'slug:\s*"([^"\n]+)"', content))[:20]
        kind, name_field = 'Role', 'company'
    elif path.endswith('/education.ts'):
        match = re.search(
            r'qualification:\s*"([^"\n]+)"[\s\S]{0,200}?institution:\s*"([^"\n]+)"',
            content,
        )
        if match:
            start = content[: match.start()].count('\n') + 1
            end = content[: match.end()].count('\n') + 1
            return (
                Fact(
                    'Education',
                    match[1],
                    'AT_INSTITUTION',
                    'Institution',
                    match[2],
                    start,
                    end,
                ),
            )
        return ()
    else:
        return ()
    for index, match in enumerate(blocks):
        offset = match.start()
        block = content[
            offset : blocks[index + 1].start()
            if index + 1 < len(blocks)
            else len(content)
        ]
        name = re.search(rf'{name_field}:\s*"([^"\n]+)"', block)
        if not name:
            continue
        subject = name[1]
        stack = re.search(r'stack:\s*technologyNames\(\[([\s\S]*?)\]\)', block)
        if stack:
            for technology in re.finditer(r'"([^"\n]+)"', stack[1]):
                start = content[: offset + name.start()].count('\n') + 1
                end = (
                    content[: offset + stack.start(1) + technology.end()].count('\n')
                    + 1
                )
                result.append(
                    Fact(kind, subject, 'USES', 'Technology', technology[1], start, end)
                )
        contributions = re.search(r'contributions:\s*\[([\s\S]*?)\]', block)
        if contributions:
            for contribution in list(re.finditer(r'"([^"\n]+)"', contributions[1]))[
                :20
            ]:
                start = content[: offset + name.start()].count('\n') + 1
                end = (
                    content[
                        : offset + contributions.start(1) + contribution.end()
                    ].count('\n')
                    + 1
                )
                result.append(
                    Fact(
                        kind,
                        subject,
                        'CONTRIBUTED',
                        'Contribution',
                        contribution[1],
                        start,
                        end,
                    )
                )
        if kind == 'Project':
            # Identity evidence exists even when a reviewed source has no stack.
            start = content[: offset + name.start()].count('\n') + 1
            result.append(
                Fact(
                    kind, subject, 'DOCUMENTED_IN', 'PublicDocument', path, start, start
                )
            )
    return tuple(result)
