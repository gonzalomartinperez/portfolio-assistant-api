"""M4-1: strict mypy covers the whole application package, not a file list."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_mypy_is_strict_over_the_whole_app_package():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["mypy"]
    assert config["strict"] is True
    assert "app" in config["files"]
    assert not [entry for entry in config["files"] if entry.startswith("app/")]
