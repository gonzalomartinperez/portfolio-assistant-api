"""Exercise actual redacted scanning in a disposable Git repository, never real keys."""

import subprocess
import sys
from pathlib import Path

SCANNER = Path(__file__).resolve().parents[1] / 'scripts/scan_secrets.py'


def test_scanner_checks_ignored_tracked_deleted_and_unmerged_history(tmp_path):
    marker = 'gh' + 'p_' + 'SyntheticOnly' * 4

    def git(*args):
        subprocess.run(['git', *args], cwd=tmp_path, check=True, capture_output=True)

    def scan():
        return subprocess.run(
            [sys.executable, str(SCANNER)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    def rejected():
        result = scan()
        assert result.returncode == 1
        assert 'github_token' in result.stdout
        assert marker not in result.stdout + result.stderr

    git('init', '--initial-branch=fixture')
    git('config', 'user.name', 'Synthetic fixture')
    git('config', 'user.email', 'fixture@example.test')
    (tmp_path / 'README.md').write_text('Synthetic fixture\n')
    git('add', 'README.md')
    git('commit', '-m', 'fixture: baseline')
    assert scan().returncode == 0
    (tmp_path / '.gitignore').write_text('ignored.txt\n')
    (tmp_path / 'ignored.txt').write_text(marker)
    git('add', '--force', 'ignored.txt')
    rejected()
    git('commit', '-m', 'fixture: synthetic marker')
    git('rm', 'ignored.txt')
    git('commit', '-m', 'fixture: remove marker')
    rejected()
    git('branch', 'unmerged-marker')
    git('switch', '--orphan', 'clean-fixture')
    (tmp_path / 'README.md').write_text('Clean fixture\n')
    git('add', 'README.md')
    git('commit', '-m', 'fixture: clean unrelated branch')
    rejected()
