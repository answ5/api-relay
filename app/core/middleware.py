"""FastAPI middleware for API key authentication."""

from __future__ import annotations

import json
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.auth import authenticate_key


def _openai_error(message: str, code: str = "authentication_error") -> JSONResponse:
    """Return an OpenAI-compatible error response."""
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "message": message,
                "type": code,
                "param": None,
                "code": code,
            }
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates Bearer API keys on every request.

    Skips authentication for:
      - /health
      - /api/admin/* (uses JWT/session auth instead)
      - /docs, /openapi.json, /redoc (FastAPI built-in)

    On success, sets:
      - request.state.user_id
      - request.state.token_id
      - request.state.models (list of allowed models, or None for all)

    On failure, returns 401 with OpenAI-compatible error body.
    """

    def __init__(
        self,
        app: FastAPI,
        *,
        exclude_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._exclude_paths = exclude_paths or {
            "/health",
            "/favicon.ico",
        }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path

        # Skip auth for excluded paths and admin routes
        if self._should_skip(path):
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _openai_error(
                "You didn't provide an API key. You need to provide your API key in an "
                "Authorization header using Bearer auth.",
                "authentication_error",
            )

        raw_key = auth_header[len("Bearer ") :].strip()
        if not raw_key:
            return _openai_error(
                "You didn't provide an API key. You need to provide your API key in an "
                "Authorization header using Bearer auth.",
                "authentication_error",
            )

        # Authenticate the key
        token_data = await authenticate_key(raw_key)
        if token_data is None:
            return _openai_error(
                "Incorrect API key provided. You can find your API key at your dashboard.",
                "authentication_error",
            )

        # Set request state
        request.state.user_id = token_data["user_id"]
        request.state.token_id = token_data["token_id"]

        # Parse models -- stored as JSON string or null
        models_raw = token_data.get("models")
        if models_raw:
            try:
                request.state.models = json.loads(models_raw)
            except (json.JSONDecodeError, TypeError):
                request.state.models = None
        else:
            request.state.models = None

        # Pass through upstream
        response: Response = await call_next(request)
        return response

    @staticmethod
    def _should_skip(path: str) -> bool:
        """Determine whether a path should skip API key authentication."""
        # FastAPI built-in docs
        if path in {"/docs", "/redoc", "/openapi.json", "/favicon.ico"}:
            return True
        # Admin routes use JWT session auth
        if path.startswith("/api/admin/"):
            return True
        # Health check
        if path == "/health":
            return True
        # Frontend static assets and SPA routes
        if path.startswith("/assets/"):
            return True
        if path in {"/", "/index.html"}:
            return True
        return False
