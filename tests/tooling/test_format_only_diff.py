"""The diff-cover exemption applies only to provable formatter-only changes."""

import subprocess
import tomllib
from pathlib import Path

from scripts.format_only_diff import format_only, main, ruff_format

BASE = {"src/portfolio_assistant/a.py": b"x = 'a'\n", "src/portfolio_assistant/b.py": b"y=1\n"}


def fmt(_path: str, source: bytes) -> bytes:
    return source.replace(b"'", b'"').replace(b"y=1", b"y = 1")


def run(rows, head):
    return format_only(rows, BASE.__getitem__, head.__getitem__, fmt)


def test_formatter_output_is_format_only():
    head = {
        "src/portfolio_assistant/a.py": b'x = "a"\n',
        "src/portfolio_assistant/b.py": b"y = 1\n",
    }
    assert (
        run([("M", "src/portfolio_assistant/a.py"), ("M", "src/portfolio_assistant/b.py")], head)
        == []
    )


def test_any_other_byte_is_not_format_only():
    head = {"src/portfolio_assistant/a.py": b'x = "b"\n'}
    assert run([("M", "src/portfolio_assistant/a.py")], head) == [
        "src/portfolio_assistant/a.py: differs from ruff format of the base version"
    ]


def test_added_deleted_and_non_python_files_are_not_format_only():
    reasons = run(
        [
            ("A", "src/portfolio_assistant/new.py"),
            ("D", "src/portfolio_assistant/a.py"),
            ("M", "src/portfolio_assistant/data.json"),
        ],
        {},
    )
    assert reasons == [
        "src/portfolio_assistant/new.py: status A is not a plain modification",
        "src/portfolio_assistant/a.py: status D is not a plain modification",
        "src/portfolio_assistant/data.json: not a Python file",
    ]


def test_an_empty_change_set_is_not_format_only():
    assert run([], {}) == ["no changed files under the given paths"]


def test_ruff_format_uses_the_repository_configuration():
    config = tomllib.loads(Path("pyproject.toml").read_text())
    quote = '"' if config["tool"]["ruff"]["format"]["quote-style"] == "double" else "'"
    other = "'" if quote == '"' else '"'
    source = f"x = {other}a{other}\n".encode()
    assert ruff_format("src/portfolio_assistant/x.py", source) == f"x = {quote}a{quote}\n".encode()


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_main_against_a_real_repository(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "src/portfolio_assistant").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")
    source = repo / "src/portfolio_assistant" / "m.py"
    source.write_text("x=1\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "switch", "-q", "-c", "feature")
    source.write_text("x = 1\n")
    _git(repo, "commit", "-q", "-am", "format")
    monkeypatch.chdir(repo)
    assert main(["--base", "main", "src/portfolio_assistant"]) == 0
    source.write_text("x = 2\n")
    _git(repo, "commit", "-q", "-am", "logic")
    assert main(["--base", "main", "src/portfolio_assistant"]) == 1


def test_main_fails_closed_on_errors_and_mode_changes(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "src/portfolio_assistant").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")
    source = repo / "src/portfolio_assistant" / "m.py"
    source.write_text("x=1\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    monkeypatch.chdir(repo)
    assert main(["--base", "no-such-ref", "src/portfolio_assistant"]) == 2
    _git(repo, "switch", "-q", "-c", "feature")
    source.write_text("x = 1\n")
    source.chmod(0o755)
    _git(repo, "commit", "-q", "-am", "format and chmod")
    assert main(["--base", "main", "src/portfolio_assistant"]) == 1
