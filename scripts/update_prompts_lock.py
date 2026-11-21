"""Regenerate src/portfolio_assistant/prompts/prompts.lock deliberately; --check fails on drift."""

import sys
from pathlib import Path

from portfolio_assistant.adapters.prompts import LOCK, prompt_files
from portfolio_assistant.domain.prompts import lock_text

ROOT = Path(__file__).resolve().parents[1] / "src/portfolio_assistant/prompts"


def main(argv: list[str]) -> int:
    expected = lock_text(prompt_files(ROOT))
    lock = ROOT / LOCK
    if argv == ["--check"]:
        if lock.read_text(encoding="utf-8") == expected:
            return 0
        print("prompts.lock is stale; review the prompt change, then run --write")
        return 1
    if argv == ["--write"]:
        lock.write_text(expected, encoding="utf-8")
        return 0
    print("usage: python -m scripts.update_prompts_lock --check|--write")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
