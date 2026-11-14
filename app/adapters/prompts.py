"""Load the git-versioned prompt files and verify them against prompts.lock."""

from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable
from types import MappingProxyType

from app.domain.prompts import PromptSpec, verify_lock

LOCK = 'prompts.lock'


def prompt_files(root: Traversable) -> dict[str, bytes]:
    return {
        item.name: item.read_bytes()
        for item in root.iterdir()
        if item.name.endswith('.md')
    }


def load_prompts(root: Traversable | None = None) -> dict[str, PromptSpec]:
    root = root or files('app') / 'prompts'
    return verify_lock(prompt_files(root), (root / LOCK).read_text(encoding='utf-8'))


@cache
def default_prompts() -> Mapping[str, PromptSpec]:
    return MappingProxyType(load_prompts())
