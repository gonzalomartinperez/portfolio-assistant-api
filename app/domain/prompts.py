"""Prompt registry policy: front matter, lock verification, rendering and version ids."""

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from string import Formatter

FRONT_MATTER_KEYS = ('id', 'version', 'owner', 'last-reviewed')
PLACEHOLDERS = frozenset({'current_date', 'language'})


class PromptError(ValueError):
    """A prompt file, its lock entry or a rendering request is invalid."""


@dataclass(frozen=True)
class PromptSpec:
    id: str
    version: str
    sha256: str
    body: str


def parse_prompt(data: bytes) -> PromptSpec:
    lines = data.decode('utf-8').split('\n')
    if lines[0] != '---' or '---' not in lines[1:]:
        raise PromptError('prompt file needs front matter')
    end = lines.index('---', 1)
    meta = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(':')
        if not sep or key.strip() in meta:
            raise PromptError(f'invalid front matter line: {line!r}')
        meta[key.strip()] = value.strip()
    if set(meta) != set(FRONT_MATTER_KEYS) or not all(meta.values()):
        raise PromptError(f'front matter keys must be {FRONT_MATTER_KEYS}')
    body = ' '.join(line.strip() for line in lines[end + 1 :] if line.strip())
    return PromptSpec(
        meta['id'], meta['version'], hashlib.sha256(data).hexdigest(), body
    )


def verify_lock(files: Mapping[str, bytes], lock_text: str) -> dict[str, PromptSpec]:
    """Parse every file and require an exact, hash-matching lock entry for each."""
    locked = json.loads(lock_text)['prompts']
    if set(files) != set(locked):
        raise PromptError(
            f'prompt files and lock differ: {sorted(set(files) ^ set(locked))}'
        )
    specs = {}
    for name, data in sorted(files.items()):
        spec = parse_prompt(data)
        expected = locked[name]
        if (spec.id, spec.version, spec.sha256) != (
            expected['id'],
            expected['version'],
            expected['sha256'],
        ):
            raise PromptError(f'{name} changed without a prompts.lock update')
        specs[spec.id] = spec
    return specs


def lock_text(files: Mapping[str, bytes]) -> str:
    entries = {}
    for name, data in sorted(files.items()):
        spec = parse_prompt(data)
        entries[name] = {'id': spec.id, 'version': spec.version, 'sha256': spec.sha256}
    return json.dumps({'prompts': entries}, indent=2) + '\n'


def render(spec: PromptSpec, **values: str) -> str:
    """Fill allowlisted placeholders; unknown or unsupplied names fail."""
    names = {name for _, name, _, _ in Formatter().parse(spec.body) if name}
    if not names <= PLACEHOLDERS or names != set(values):
        raise PromptError(
            f'{spec.id}: placeholders {sorted(names)} vs {sorted(values)}'
        )
    return spec.body.format_map(values)


def prompt_version(specs: Iterable[PromptSpec]) -> str:
    """Identify the exact pieces used, e.g. ``answer@1+0123456789ab,voice-en@1+...``."""
    return ','.join(f'{s.id}@{s.version}+{s.sha256[:12]}' for s in specs)
