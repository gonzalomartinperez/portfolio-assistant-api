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
