"""Approved public profile paths and index identity across the source transition."""

import re
from typing import Literal

PROFILE_PATH_PATTERN = (
    r'^(?:src/)?content/(en|es)/(profile|experience|projects|education)\.ts$'
)
_PROFILE = re.compile(PROFILE_PATH_PATTERN)
_TOPICS = ('profile', 'experience', 'projects', 'education')
EVIDENCE_KEY_PATTERN = (
    r'^(en|es)/(profile|experience|projects|education)(?:#([a-z0-9]+(?:-[a-z0-9]+)*))?$'
)
_EVIDENCE_KEY = re.compile(EVIDENCE_KEY_PATTERN)


def profile_parts(path: str) -> tuple[Literal['en', 'es'], str] | None:
    match = _PROFILE.fullmatch(path)
    if match is None:
        return None
    return ('en' if match[1] == 'en' else 'es', match[2])


def profile_paths(locale: str, topic: str) -> tuple[str, str]:
    if locale not in ('en', 'es') or topic not in _TOPICS:
        raise ValueError('unsupported public profile path')
    return f'content/{locale}/{topic}.ts', f'src/content/{locale}/{topic}.ts'


def canonical_key(path: str, entity: str | None = None) -> str:
    """Return the layout-neutral evidence key for a public corpus path.

    Approved profile files map to ``<locale>/<topic>`` whether they live under
    ``content/`` or the legacy ``src/content/`` root, so citations, qrels and
    graders compare keys instead of physical paths. Other approved paths are
    already layout-stable and are returned unchanged. An optional entity slug is
    appended as ``#<entity>`` for profile keys only.

    Raises:
        ValueError: If an entity is given for a non-profile path or is not a
            lowercase kebab-case slug.
    """
    parts = profile_parts(path)
    if parts is None:
        if entity is not None:
            raise ValueError('entity keys require an approved profile path')
        return path
    key = f'{parts[0]}/{parts[1]}'
    if entity is None:
        return key
    if _EVIDENCE_KEY.fullmatch(f'{key}#{entity}') is None:
        raise ValueError('invalid evidence entity slug')
    return f'{key}#{entity}'


def key_paths(key: str) -> tuple[str, str]:
    """Return the physical paths, current layout first, that an evidence key covers."""
    match = _EVIDENCE_KEY.fullmatch(key)
    if match is None:
        raise ValueError('invalid evidence key')
    return profile_paths(match[1], match[2])


def corpus_version(commit: str, provider: str) -> str:
    if not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('invalid public source revision')
    if provider == 'fixture':
        return commit + '-v8'
    if provider == 'openai':
        return commit + '-semantic-v9'
    raise ValueError('unsupported embedding provider')
