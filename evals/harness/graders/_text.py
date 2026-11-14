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
