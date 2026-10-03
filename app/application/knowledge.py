from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Chunk:
    """A stored public span whose provenance must be verified before generation."""

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
    """One active revision and its bounded lexical/vector candidates."""

    version: str
    commit: str
    chunks: tuple[Chunk, ...]
    paths: frozenset[str]
    nearest: tuple[str, ...]
    lexical: tuple[str, ...] = ()
    semantic: bool = False


class KnowledgeIndex(Protocol):
    """Read immutable corpus candidates and provenance-bearing relationships."""

    async def candidates(self, question: str) -> Corpus | None:
        """Read at most 500 chunks and 12 exact vector neighbors from one revision."""
        ...

    async def relationships(
        self, version: str, terms: set[str], locale: str = 'en', expand: bool = False
    ) -> tuple[str, ...]:
        """Return bounded source IDs reached through reviewed versioned graph edges."""
        ...
