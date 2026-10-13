"""Optional public technical context, separate from career evidence and authority."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.web_policy import WebTopic, approved_web_url, technical_topic


@dataclass(frozen=True)
class WebReference:
    title: str
    url: str


@dataclass(frozen=True)
class WebSupplement:
    topic: str
    text: str
    references: tuple[WebReference, ...]


class WebSearch(Protocol):
    async def search(self, topic: WebTopic) -> WebSupplement | None:
        """Read one fixed public query; no visitor data, actions or automatic retry."""
        ...


async def supplement(
    question: str, evidence: str, search: WebSearch | None
) -> WebSupplement | None:
    topic = technical_topic(question, evidence) if search else None
    if not topic or not search:
        return None
    result = await search.search(topic)
    if (
        not result
        or result.topic != topic.name
        or not 1 <= len(result.text) <= 6000
        or not 1 <= len(result.references) <= 4
        or any(
            not 1 <= len(ref.title) <= 160 or not approved_web_url(ref.url, topic)
            for ref in result.references
        )
    ):
        return None
    return result
