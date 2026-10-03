"""Offline detection; low-accuracy mode bounds memory without a provider call."""

import re
from functools import lru_cache

from lingua import Language, LanguageDetectorBuilder

from app.application.language import Locale


@lru_cache(maxsize=1)
def detector():
    return LanguageDetectorBuilder.from_all_languages().with_low_accuracy_mode().build()


class LocalLanguageDetector:
    def supported(self, text: str) -> Locale | None:
        cleaned = re.sub(r'https?://\S+|`[^`]*`', '', text)
        if len(re.findall(r'[^\W\d_]+', cleaned)) < 3:
            return None
        confidence = detector().compute_language_confidence_values(cleaned)
        if len(confidence) < 2 or confidence[0].value - confidence[1].value < 0.15:
            return None
        if confidence[0].language == Language.ENGLISH:
            return 'en'
        if confidence[0].language == Language.SPANISH:
            return 'es'
        return None
