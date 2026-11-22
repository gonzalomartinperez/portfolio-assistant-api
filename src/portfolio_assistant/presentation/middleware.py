"""Bound request bytes before JSON parsing; public errors never echo input."""

import asyncio
import json
import logging
import time
from collections.abc import Collection
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from portfolio_assistant.application.request_context import request_id
from portfolio_assistant.domain.errors import RejectedError
from portfolio_assistant.presentation import problems

log = logging.getLogger("portfolio_assistant")


def error(request: Request, code: str, status: int) -> JSONResponse:
    return problems.response(
        code, status, request.state.request_id, request.headers.get("accept", "")
    )


def install(app: FastAPI, origins: Collection[str]) -> None:
    @app.exception_handler(RejectedError)
    async def rejected(request: Request, exc: RejectedError) -> JSONResponse:
        return error(request, exc.code, exc.status)

    # Starlette's base class also covers router 404/405, which the FastAPI subclass misses.
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        response = error(request, str(exc.detail), exc.status_code)
        for name, value in (exc.headers or {}).items():  # keeps Allow on 405
            response.headers.setdefault(name, value)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(request, "invalid_request", 422)

    @app.middleware("http")
    async def guard(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = uuid4().hex
        request_id.set(request.state.request_id)
        started = time.perf_counter()
        if (
            request.method in ("POST", "PATCH", "DELETE")
            and request.headers.get("origin") not in origins
        ):
            response: Response = error(request, "origin_denied", 403)
        else:
            try:
                response = await call_next(request)
            except Exception:  # noqa: BLE001 - Public HTTP fault boundary: translate unexpected failures without leaking details.
                response = error(request, "dependency_unavailable", 503)
        if request.url.path.startswith(("/api/", "/internal/")):
            response.headers["Cache-Control"] = "no-store, no-transform"
            response.headers["Pragma"] = "no-cache"
        response.headers["X-Request-ID"] = request.state.request_id
        vary = response.headers.get("Vary", "")
        if "Origin" not in vary:
            response.headers["Vary"] = ", ".join(filter(None, (vary, "Origin")))
        route = request.scope.get("route")
        log.info(
            json.dumps(
                {
                    "request_id": request.state.request_id,
                    "operation": route.name if route else "unmatched",
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )
        )
        return response


def accept(scope: Scope) -> str:
    return next(
        (value.decode("latin-1") for name, value in scope.get("headers", []) if name == b"accept"),
        "",
    )


class BodyLimit:
    def __init__(self, app: ASGIApp, maximum: int = 32768, timeout: float = 10) -> None:
        self.app = app
        self.maximum = maximum
        self.timeout = timeout

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in (
            "POST",
            "PATCH",
            "DELETE",
        ):
            await self.app(scope, receive, send)
            return
        # Bounded buffering also covers chunked requests and lying Content-Length.
        maximum = (
            min(self.maximum, 1024)
            if scope.get("path") == "/api/v1/analytics/events"
            else self.maximum
        )
        chunks: list[Message] = []
        size = 0
        deadline = asyncio.get_running_loop().time() + self.timeout
        while True:
            try:
                async with asyncio.timeout_at(deadline):
                    message = await receive()
            except TimeoutError:
                identifier = uuid4().hex
                response = problems.response("request_timeout", 408, identifier, accept(scope))
                response.headers["X-Request-ID"] = identifier
                response.headers["Cache-Control"] = "no-store"
                await response(scope, receive, send)
                return
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > maximum:
                request_id = uuid4().hex
                response = problems.response("invalid_request", 422, request_id, accept(scope))
                response.headers["X-Request-ID"] = request_id
                await response(scope, receive, send)
                return
            chunks.append(message)
            if not message.get("more_body", False):
                break

        async def buffered() -> Message:
            return chunks.pop(0) if chunks else await receive()

        await self.app(scope, buffered, send)
