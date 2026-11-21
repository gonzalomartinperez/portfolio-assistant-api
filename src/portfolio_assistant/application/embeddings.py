"""Embedding capability and wire-independent vector identity."""

from typing import Protocol


class Embeddings(Protocol):
    provider: str
    model: str
    dimensions: int

    def encode(self, text: str, purpose: str) -> tuple[float, ...]:
        """Encode bounded public text after reserving cost; never retry billed work."""
        ...

    async def query(self, text: str) -> tuple[float, ...]:
        """Encode visitor input with cancellable I/O; it is never added to public knowledge."""
        ...
