"""Simple in-memory rate limiter middleware."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


class RateLimiter(BaseHTTPMiddleware):
    """Limit requests per IP per minute."""

    def __init__(self, app, rpm: int | None = None):
        super().__init__(app)
        self.rpm = rpm or settings.rate_limit_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only limit POST endpoints (task submissions)
        if request.method != "POST" or "/api/tasks" not in request.url.path:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60.0

        # Clean old entries
        self._hits[ip] = [t for t in self._hits[ip] if now - t < window]

        if len(self._hits[ip]) >= self.rpm:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded. Max {self.rpm} requests per minute.",
                    "retry_after": int(window - (now - self._hits[ip][0])),
                },
            )

        self._hits[ip].append(now)
        return await call_next(request)
