import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("Pragma", "no-cache")
        return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request identifiers and latency metrics to structured logs."""

    def __init__(self, app):
        super().__init__(app)
        self.logger = structlog.get_logger("request")

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()
        response: Response | None = None

        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            user_id = getattr(request.state, "user_id", None)
            self.logger.info(
                "request_complete",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=getattr(response, "status_code", None),
                duration_ms=round(duration_ms, 2),
                client_ip=request.client.host if request.client else None,
                user_id=user_id,
            )

            if response:
                response.headers.setdefault("X-Request-ID", request_id)
