"""Final selection of cited evidence."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict

from app.application.contracts import Evidence
from app.application.knowledge import Chunk

LIMIT = 5


def select_evidence(
    ranked: Sequence[str], eligible: Mapping[str, Chunk], commit: str
) -> tuple[Evidence, ...]:
    return tuple(
        Evidence(
            **{k: v for k, v in asdict(eligible[key]).items() if k != "content_hash"},
            commit_sha=commit,
        )
        for key in ranked[:LIMIT]
    )
