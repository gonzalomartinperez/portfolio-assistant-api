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


def bounded_sources(sources: tuple[Evidence, ...]) -> tuple[Evidence, ...]:
    result = []
    remaining = 19000
    for source in sources[:5]:
        size = len(source.content) + len(source.path) + 100
        if size > remaining:
            continue
        result.append(source)
        remaining -= size
    return tuple(result)


def context(sources: tuple[Evidence, ...]) -> str:
    return '\n'.join(
        f'PUBLIC SOURCE [{index}] {source.path} lines {source.start_line}-{source.end_line}:\n{source.content}'
        for index, source in enumerate(sources[:5], 1)
    )


async def generate(
    command: AnswerCommand,
    sources: tuple[Evidence, ...],
    provider: Provider,
    accounting: Accounting | None,
    max_characters: int = 40000,
) -> AsyncGenerator[str]:
    if accounting and sources:
        await accounting.reserve(command.run_id)
    count = 0
    async with aclosing(
        provider.stream(
            command.question,
            context(sources),
            command.locale,
            command.history,
            command.context,
        )
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
