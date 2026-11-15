"""Final selection of cited evidence."""

from dataclasses import asdict
from typing import TYPE_CHECKING

from app.application.contracts import Evidence

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from app.application.knowledge import Chunk

LIMIT = 5


def select_evidence(
    ranked: Sequence[str], eligible: Mapping[str, Chunk], commit: str
) -> tuple[Evidence, ...]:
    """Convert the first ranked chunks to evidence with pinned commit provenance."""
    return tuple(
        Evidence(
            **{k: v for k, v in asdict(eligible[key]).items() if k != "content_hash"},
            commit_sha=commit,
        )
        for key in ranked[:LIMIT]
    )
