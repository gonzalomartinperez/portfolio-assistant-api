from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Chunk:
    id: str
    title: str
    url: str
    source_type: str
    path: str
    start_line: int
    end_line: int
    content: str
    content_hash: str


@dataclass(frozen=True)
class Corpus:
    version: str
    commit: str
    chunks: tuple[Chunk, ...]
    paths: frozenset[str]
    nearest: tuple[str, ...]


class KnowledgeIndex(Protocol):
    async def candidates(self, question: str) -> Corpus | None: ...
    async def relationships(self, version: str, terms: set[str]) -> tuple[str, ...]: ...
