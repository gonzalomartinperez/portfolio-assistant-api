"""Approved public profile paths and index identity across the source transition."""

import re
from typing import Literal

PROFILE_PATH_PATTERN = (
    r'^(?:src/)?content/(en|es)/(profile|experience|projects|education)\.ts$'
)
_PROFILE = re.compile(PROFILE_PATH_PATTERN)


def profile_parts(path: str) -> tuple[Literal['en', 'es'], str] | None:
    match = _PROFILE.fullmatch(path)
    if match is None:
        return None
    return ('en' if match[1] == 'en' else 'es', match[2])


def profile_paths(locale: str, topic: str) -> tuple[str, str]:
    if locale not in ('en', 'es') or topic not in (
        'profile',
        'experience',
        'projects',
        'education',
    ):
        raise ValueError('unsupported public profile path')
    return f'content/{locale}/{topic}.ts', f'src/content/{locale}/{topic}.ts'


def corpus_version(commit: str, provider: str) -> str:
    if not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('invalid public source revision')
    if provider == 'fixture':
        return commit + '-v8'
    if provider == 'openai':
        return commit + '-semantic-v9'
    raise ValueError('unsupported embedding provider')
