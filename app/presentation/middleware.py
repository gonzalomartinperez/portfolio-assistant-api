"""Bound request bytes before JSON parsing; public errors never echo input."""

import asyncio
import json
import logging
import time
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.request_context import request_id
from app.domain.errors import RejectedError

log = logging.getLogger('portfolio_assistant')


def error(request: Request, code: str, status: int, message: str | None = None):
    return JSONResponse(
        status_code=status,
        content={
            'code': code,
            'message': message or code.replace('_', ' '),
            'request_id': request.state.request_id,
        },
    )


def install(app, origins):
    @app.exception_handler(RejectedError)
    async def rejected(request, exc):
        return error(request, exc.code, exc.status)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(request, str(exc.detail), exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return error(request, 'invalid_request', 422, 'Invalid request')

    @app.middleware('http')
    async def guard(request: Request, call_next):
        request.state.request_id = uuid4().hex
        request_id.set(request.state.request_id)
        started = time.perf_counter()
        if (
            request.method in ('POST', 'PATCH', 'DELETE')
            and request.headers.get('origin') not in origins
        ):
            response = error(request, 'origin_denied', 403, 'Origin denied')
        else:
            try:
                response = await call_next(request)
            except Exception:  # noqa: BLE001 - Public HTTP fault boundary: translate unexpected failures without leaking details.
                response = error(request, 'dependency_unavailable', 503)
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-transform'
            response.headers['Pragma'] = 'no-cache'
        response.headers['X-Request-ID'] = request.state.request_id
        vary = response.headers.get('Vary', '')
        if 'Origin' not in vary:
            response.headers['Vary'] = ', '.join(filter(None, (vary, 'Origin')))
        route = request.scope.get('route')
        log.info(
            json.dumps(
                {
                    'request_id': request.state.request_id,
                    'operation': route.name if route else 'unmatched',
                    'status': response.status_code,
                    'duration_ms': round((time.perf_counter() - started) * 1000, 1),
                }
            )
        )
        return response


class BodyLimit:
    def __init__(self, app, maximum: int = 32768, timeout: float = 10):
        self.app = app
        self.maximum = maximum
        self.timeout = timeout

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in (
            'POST',
            'PATCH',
            'DELETE',
        ):
            await self.app(scope, receive, send)
            return
        # Bounded buffering also covers chunked requests and lying Content-Length.
        chunks = []
        size = 0
        deadline = asyncio.get_running_loop().time() + self.timeout
        while True:
            try:
                async with asyncio.timeout_at(deadline):
                    message = await receive()
            except TimeoutError:
                identifier = uuid4().hex
                response = JSONResponse(
                    {
                        'code': 'request_timeout',
                        'message': 'Request timed out',
                        'request_id': identifier,
                    },
                    status_code=408,
                    headers={'X-Request-ID': identifier, 'Cache-Control': 'no-store'},
                )
                await response(scope, receive, send)
                return
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body', b''))
            if size > self.maximum:
                request_id = uuid4().hex
                response = JSONResponse(
                    {
                        'code': 'invalid_request',
                        'message': 'Invalid request',
                        'request_id': request_id,
                    },
                    status_code=422,
                    headers={'X-Request-ID': request_id},
                )
                await response(scope, receive, send)
                return
            chunks.append(message)
            if not message.get('more_body', False):
                break

        async def buffered():
            return chunks.pop(0) if chunks else await receive()

        await self.app(scope, buffered, send)
