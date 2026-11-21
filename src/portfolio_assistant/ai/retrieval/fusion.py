"""Weighted reciprocal-rank fusion of candidate lanes."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


def fuse(
    lanes: Sequence[Sequence[str]],
    weights: Sequence[float],
    scores: Mapping[str, float],
    offset: int = 10,
) -> list[str]:
    """Rank ids by summed ``weight / (offset + index)``; ties by lexical score, then id."""
    ranks: dict[str, float] = {}
    for weight, ids in zip(weights, lanes, strict=True):
        for index, key in enumerate(ids):
            ranks[key] = ranks.get(key, 0) + weight / (offset + index)
    return sorted(ranks, key=lambda key: (-ranks[key], -scores[key], key))
