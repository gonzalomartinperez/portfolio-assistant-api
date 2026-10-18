import asyncio
import hashlib
import math
import re

from openai import APIError

from app.domain.errors import ProviderUnavailableError


def embed(text: str) -> str:
    values = [0.0] * 64
    for word in re.findall(r'[\w]+', text.lower()):
        digest = hashlib.sha256(word.encode()).digest()
        values[digest[0] % 64] += -1 if digest[1] & 1 else 1
    norm = math.sqrt(sum(value * value for value in values)) or 1
    return '[' + ','.join(str(value / norm) for value in values) + ']'


class FixtureEmbeddings:
    provider = 'fixture'
    model = 'hash64-v1'
    dimensions = 64

    def encode(self, text: str, purpose: str) -> tuple[float, ...]:
        return tuple(float(value) for value in embed(text)[1:-1].split(','))

    async def query(self, text: str) -> tuple[float, ...]:
        return self.encode(text, 'query')


class OpenAIEmbeddings:
    provider = 'openai'
    model = 'text-embedding-3-small'
    dimensions = 1536

    def __init__(self, client, accounting, async_client=None):
        self.client = client
        self.accounting = accounting
        self.async_client = async_client

    def encode(self, text: str, purpose: str) -> tuple[float, ...]:
        if not text or len(text.encode('utf-8')) > 8000:
            raise ValueError('embedding input must contain at most 8000 bytes')
        identifier = self.accounting.reserve_embedding(
            len(text.encode('utf-8')), purpose
        )
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions,
            )
        except APIError:
            raise ProviderUnavailableError('provider_unavailable') from None
        values = response.data[0].embedding if len(response.data) == 1 else []
        if len(values) != self.dimensions or any(not math.isfinite(v) for v in values):
            raise ValueError('invalid embedding response')
        self.accounting.settle_embedding(identifier, response.usage.total_tokens)
        return tuple(values)

    async def query(self, text: str) -> tuple[float, ...]:
        if self.async_client is None:
            raise RuntimeError('query embedding requires an asynchronous client')
        if not text or len(text.encode('utf-8')) > 8000:
            raise ValueError('embedding input must contain at most 8000 bytes')
        identifier = await asyncio.to_thread(
            self.accounting.reserve_embedding, len(text.encode('utf-8')), 'query'
        )
        try:
            response = await self.async_client.embeddings.create(
                model=self.model, input=text, dimensions=self.dimensions
            )
        except APIError:
            raise ProviderUnavailableError('provider_unavailable') from None
        values = response.data[0].embedding if len(response.data) == 1 else []
        if len(values) != self.dimensions or any(
            not math.isfinite(value) for value in values
        ):
            raise ValueError('invalid embedding response')
        await asyncio.to_thread(
            self.accounting.settle_embedding, identifier, response.usage.total_tokens
        )
        return tuple(values)


def vector(values: tuple[float, ...]) -> str:
    if any(not math.isfinite(value) for value in values):
        raise ValueError('vector must be finite')
    return '[' + ','.join(str(value) for value in values) + ']'
