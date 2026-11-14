"""Shared text normalization for the graders."""

import re
import unicodedata

_PUNCTUATION = str.maketrans(
    {'’': "'", '‘': "'", '“': '"', '”': '"', '–': '-', '—': '-'}
)


def fold(text: str) -> str:
    """Casefold, strip accents, unify typographic punctuation, collapse whitespace."""
    decomposed = unicodedata.normalize('NFKD', text.translate(_PUNCTUATION).casefold())
    plain = ''.join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', plain).strip()


def contains_phrase(folded_text: str, phrase: str) -> bool:
    """Whole-word match of a phrase against already folded text."""
    return (
        re.search(rf'(?<!\w){re.escape(fold(phrase))}(?!\w)', folded_text) is not None
    )


def sentences(text: str) -> list[str]:
    """Split on sentence-final punctuation followed by space, and on line breaks."""
    parts = re.split(r'(?<=[.!?])\s+|\n+', text)
    return [part for part in parts if part.strip()]


# Citation markers: [1], [1,2], [1, 3], [1-3] (also en dash).
MARKER = r'\[\d+(?:\s*[,–-]\s*\d+)*\]'


def expand_marker(marker: str) -> set[int]:
    """Expand ``[1,3]`` or ``[1-3]`` to the numbers they cite; a reversed range yields 0."""
    numbers: set[int] = set()
    for part in marker.strip('[]').split(','):
        bounds = [int(n) for n in re.split(r'[–-]', part)]
        if len(bounds) == 1:
            numbers.add(bounds[0])
        elif bounds[0] <= bounds[1] and bounds[1] - bounds[0] <= 100:
            numbers.update(range(bounds[0], bounds[1] + 1))
        else:
            numbers.add(0)  # invalid range: never a real source number
    return numbers
