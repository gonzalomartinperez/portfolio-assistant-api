"""Answer policy shared by orchestration adapters."""

from collections.abc import AsyncGenerator
from contextlib import aclosing

from app.application.contracts import (
    Accounting,
    AnswerCommand,
    Evidence,
    GenerationFailedError,
    Provider,
    Usage,
)


def context(sources: tuple[Evidence, ...]) -> str:
    return '\n'.join(
        f'PUBLIC SOURCE {s.path} lines {s.start_line}-{s.end_line}:\n{s.content[:6000]}'
        for s in sources[:5]
    )[:22000]


async def generate(
    command: AnswerCommand,
    sources: tuple[Evidence, ...],
    provider: Provider,
    accounting: Accounting | None,
    max_characters: int = 12000,
) -> AsyncGenerator[str]:
    if accounting and sources:
        await accounting.reserve(command.run_id)
    count = 0
    async with aclosing(
        provider.stream(command.question, context(sources), command.locale)
    ) as stream:
        async for item in stream:
            if isinstance(item, Usage):
                if accounting and sources:
                    await accounting.settle(command.run_id, item)
                continue
            count += len(item)
            if count > max_characters:
                raise GenerationFailedError('output_limit')
            yield item
