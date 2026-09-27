"""Bound request bytes before JSON parsing; public errors never echo input."""

import json
import logging
import time
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import Rejected

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
    @app.exception_handler(Rejected)
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
        started = time.perf_counter()
        if (
            request.method in ('POST', 'PATCH', 'DELETE')
            and request.headers.get('origin') not in origins
        ):
            response = error(request, 'origin_denied', 403, 'Origin denied')
        else:
            try:
                response = await call_next(request)
            except Exception:
                response = error(request, 'dependency_unavailable', 503)
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
    def __init__(self, app, maximum: int = 32768):
        self.app = app
        self.maximum = maximum

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
        while True:
            message = await receive()
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
