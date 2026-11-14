"""Frozen public corpus snapshot: manifest integrity and stable identity (ADR016)."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.adapters.portfolio.indexing import chunks, manifest_at_commit, snapshot_source
from app.bootstrap import indexing as indexing_cli
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
    commit, files, read, _size = snapshot_source(ROOT)
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


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def test_git_mode_and_snapshot_mode_agree_on_files_and_chunk_identity(tmp_path):
    repo = tmp_path / 'repo'
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns('manifest.json'))
    _git(repo, 'init', '-q')
    _git(repo, 'config', 'user.name', 'Synthetic fixture')
    _git(repo, 'config', 'user.email', 'fixture@example.test')
    _git(repo, 'config', 'commit.gpgsign', 'false')
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-qm', 'synthetic')
    commit = _git(repo, 'rev-parse', 'HEAD')
    from_git = manifest_at_commit(repo, commit)
    snap_commit, from_snapshot, _, _ = snapshot_source(ROOT)
    assert from_git == from_snapshot
    # Chunk ids and citation URLs derive from (commit, path, content), so reading the
    # same blobs through Git or through the snapshot must give identical records.
    _, _, read, _ = snapshot_source(ROOT)
    for path, blob_sha in from_snapshot:
        git_content = _git(repo, 'cat-file', 'blob', blob_sha)
        snapshot_content = read(blob_sha).decode()
        assert (
            git_content == snapshot_content.strip('\n')
            or git_content == snapshot_content
        )
        left = [
            (c['id'], c['url']) for c in chunks(path, snapshot_content, snap_commit)
        ]
        right = [
            (c['id'], c['url'])
            for c in chunks(path, (repo / path).read_text(), snap_commit)
        ]
        assert left == right
        assert left


def test_cli_snapshot_source_requires_repo(monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['knowledge_sync', '--source', 'snapshot'])
    with pytest.raises(SystemExit) as raised:
        indexing_cli.main()
    assert raised.value.code == 2
    assert '--repo' in capsys.readouterr().err
