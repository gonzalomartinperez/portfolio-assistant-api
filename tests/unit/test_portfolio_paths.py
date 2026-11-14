"""Layout-neutral evidence keys for the approved public profile corpus (ADR 012)."""

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.portfolio_paths import (
    canonical_key,
    key_paths,
    profile_parts,
    profile_paths,
)

LOCALES = ('en', 'es')
TOPICS = ('profile', 'experience', 'projects', 'education')
SLUG = st.from_regex(r'[a-z0-9]{1,8}(?:-[a-z0-9]{1,8}){0,3}', fullmatch=True)


@pytest.mark.parametrize('locale', LOCALES)
@pytest.mark.parametrize('topic', TOPICS)
def test_both_layouts_share_one_key(locale, topic):
    current, legacy = profile_paths(locale, topic)
    assert current == f'content/{locale}/{topic}.ts'
    assert legacy == f'src/content/{locale}/{topic}.ts'
    assert canonical_key(current) == canonical_key(legacy) == f'{locale}/{topic}'


@given(st.sampled_from(LOCALES), st.sampled_from(TOPICS), st.none() | SLUG)
def test_canonical_key_round_trip(locale, topic, entity):
    paths = profile_paths(locale, topic)
    keys = {canonical_key(path, entity) for path in paths}
    assert len(keys) == 1
    key = keys.pop()
    assert key_paths(key) == paths
    assert key.split('#', 1)[0] == f'{locale}/{topic}'
    assert (entity is None) == ('#' not in key)


@given(
    st.text()
    | st.builds(
        '{}content/{}/{}.ts'.format,
        st.sampled_from(['', 'src/', 'lib/', '/']),
        st.sampled_from(LOCALES) | st.text(max_size=3),
        st.sampled_from(TOPICS) | st.text(max_size=12),
    )
)
def test_only_approved_profile_paths_change(path):
    key = canonical_key(path)
    if profile_parts(path) is None:
        assert key == path
    else:
        assert path in key_paths(key)


@pytest.mark.parametrize(
    'path',
    [
        'README.md',
        'content/pt/profile.ts',
        'content/en/gallery.ts',
        'lib/content/en/projects.ts',
        'src/content/en/projects.tsx',
        '/content/en/projects.ts',
    ],
)
def test_unapproved_paths_never_become_profile_keys(path):
    assert canonical_key(path) == path
    with pytest.raises(ValueError, match='entity keys require'):
        canonical_key(path, 'filomena')


@pytest.mark.parametrize(
    'entity', ['Filomena', 'has space', '-lead', 'trail-', 'a--b', '']
)
def test_entity_slug_must_be_lowercase_kebab(entity):
    with pytest.raises(ValueError, match='entity slug'):
        canonical_key('content/en/projects.ts', entity)


@pytest.mark.parametrize(
    'key', ['en', 'pt/profile', 'en/projects#', 'content/en/projects']
)
def test_invalid_keys_are_rejected(key):
    with pytest.raises(ValueError, match='invalid evidence key'):
        key_paths(key)


def test_retrieval_cases_use_layout_neutral_qrels():
    cases = json.loads(Path('evals/retrieval.json').read_text())
    assert len({case['id'] for case in cases}) == len(cases)
    for case in cases:
        assert 'paths' not in case, case['id']
        assert case['locale'] in LOCALES, case['id']
        for key, grade in case['qrels'].items():
            assert len(key_paths(key)) == 2, case['id']
            assert grade in (1, 2, 3), case['id']
        if case['kind'] in ('no-answer', 'ambiguity'):
            assert case['qrels'] == {}, case['id']
        else:
            assert case['qrels'] and case['contains'], case['id']
