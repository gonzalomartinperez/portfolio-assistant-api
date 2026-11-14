"""Frozen public corpus snapshot: manifest integrity and stable identity (ADR016)."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.adapters.portfolio.indexing import manifest_at_commit, snapshot_source
from scripts import refresh_corpus

ROOT = Path('evals/corpus')
PINNED = '1acbe54906c88398652aebb8eae0c217fd0d8821'


def manifest() -> dict:
    return json.loads((ROOT / 'manifest.json').read_text())


def test_manifest_hashes_match_the_committed_files():
    data = manifest()
    assert data['repository'] == 'gonzalomartinperez/portfolio'
    assert data['commit'] == PINNED
    for item in data['files']:
        content = (ROOT / item['path']).read_bytes()
        assert hashlib.sha256(content).hexdigest() == item['sha256']
        assert len(content) == item['bytes']


def test_snapshot_id_is_derived_from_sorted_path_hashes():
    data = manifest()
    pairs = sorted((item['path'], item['sha256']) for item in data['files'])
    digest = hashlib.sha256(json.dumps(pairs, separators=(',', ':')).encode())
    assert data['corpus_snapshot_id'] == 'corpus-' + digest.hexdigest()[:12]
    shuffled = list(reversed(data['files']))
    assert refresh_corpus.snapshot_id(shuffled) == data['corpus_snapshot_id']


def test_check_passes_and_detects_tampering(tmp_path):
    assert refresh_corpus.main(['--check']) == 0
    copy = tmp_path / 'corpus'
    shutil.copytree(ROOT, copy)
    target = copy / manifest()['files'][0]['path']
    target.write_bytes(target.read_bytes() + b'x')
    (copy / 'extra.md').write_text('unlisted')
    problems = refresh_corpus.verify(copy)
    assert f'changed: {manifest()["files"][0]["path"]}' in problems
    assert 'unlisted: extra.md' in problems


def test_canonical_keys_cover_both_locales_and_all_topics():
    keys = {item['key'] for item in manifest()['files']}
    for locale in ('en', 'es'):
        for topic in ('profile', 'experience', 'projects', 'education'):
            assert f'{locale}/{topic}' in keys


def test_snapshot_source_matches_git_object_ids():
    commit, files, read = snapshot_source(ROOT)
    assert commit == PINNED
    assert [path for path, _ in files] == sorted(
        item['path'] for item in manifest()['files']
    )
    for path, blob_sha in files:
        assert (
            hashlib.sha1(
                b'blob %d\0' % len(read(blob_sha)) + read(blob_sha)
            ).hexdigest()
            == blob_sha
        )
        assert (ROOT / path).read_bytes() == read(blob_sha)


def test_snapshot_source_rejects_a_modified_file(tmp_path):
    copy = tmp_path / 'corpus'
    shutil.copytree(ROOT, copy)
    target = copy / manifest()['files'][0]['path']
    target.write_bytes(target.read_bytes() + b'x')
    with pytest.raises(ValueError, match='does not match its manifest'):
        snapshot_source(copy)


def test_manifest_at_commit_is_still_importable_for_git_mode():
    assert callable(manifest_at_commit)
