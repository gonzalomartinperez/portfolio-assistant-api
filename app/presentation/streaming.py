"""Explicit generator closure for both ASGI disconnect and send-failure paths."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import cast

import anyio
from starlette.responses import Content, StreamingResponse
from starlette.types import Receive, Scope, Send


class ClosingStreamingResponse(StreamingResponse):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            # Starlette's ASGI 2.4 send-error branch does not close the iterator.
            # Shield only bounded cleanup, never continued model generation.
            with anyio.move_on_after(10, shield=True):
                # Starlette types body_iterator as AsyncIterable; ours is always an async generator.
                async with aclosing(cast(AsyncGenerator[Content], self.body_iterator)):
                    pass


async def heartbeat(stream: AsyncGenerator[str], interval: float = 15) -> AsyncGenerator[str]:
    """Emit SSE comments while upstream is silent; comments do not consume sequence IDs."""
    pending: asyncio.Task[str] | None = None
    try:
        async with aclosing(stream):
            while True:
                pending = asyncio.create_task(anext(stream))
                try:
                    while not pending.done():
                        done, _ = await asyncio.wait({pending}, timeout=interval)
                        if not done:
                            yield ": keep-alive\n\n"
                    try:
                        yield pending.result()
                    except StopAsyncIteration:
                        return
                finally:
                    if not pending.done():
                        pending.cancel()
                        await asyncio.gather(pending, return_exceptions=True)
    finally:
        if pending and not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
