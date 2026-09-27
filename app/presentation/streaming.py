"""Explicit generator closure for both ASGI disconnect and send-failure paths."""

from contextlib import aclosing

import anyio
from starlette.responses import StreamingResponse


class ClosingStreamingResponse(StreamingResponse):
    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            # Starlette's ASGI 2.4 send-error branch does not close the iterator.
            # Shield only bounded cleanup, never continued model generation.
            with anyio.move_on_after(10, shield=True):
                async with aclosing(self.body_iterator):
                    pass


async def heartbeat(stream, interval: float = 15):
    """Emit SSE comments while upstream is silent; comments do not consume sequence IDs."""
    import asyncio

    pending = None
    try:
        async with aclosing(stream):
            while True:
                pending = asyncio.create_task(anext(stream))
                try:
                    while not pending.done():
                        done, _ = await asyncio.wait({pending}, timeout=interval)
                        if not done:
                            yield ': keep-alive\n\n'
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
