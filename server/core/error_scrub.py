"""Keep internal error text out of 500 responses in production.

Many handlers raise HTTPException(500, detail=str(e)) or f"...{e}". That text
can carry hostnames, SQL, file paths or library internals. In production a 500
now returns a plain message with the request's reference id; the original
detail goes to the log under the same id so support can still find it.

Only plain-string 500 details are replaced. Structured (dict) details are
deliberate API contracts, and 502/503 messages describe an upstream outage.
Outside production nothing changes, so local debugging keeps the real text.
"""
import logging
import os
import uuid

from fastapi import Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

GENERIC_500 = "Something went wrong on our side. Please try again."


def _is_production() -> bool:
    return (
        os.getenv("ENVIRONMENT", "").lower() == "production"
        or os.getenv("NODE_ENV", "").lower() == "production"
    )


def _reference(request: Request) -> str:
    return getattr(request.state, "request_id", None) or uuid.uuid4().hex[:12]


async def scrubbed_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 500 and isinstance(exc.detail, str) and _is_production():
        ref = _reference(request)
        logger.error("500 on %s %s [ref %s]: %s", request.method, request.url.path, ref, exc.detail)
        return JSONResponse(
            status_code=500,
            content={"detail": f"{GENERIC_500} Reference: {ref}", "reference": ref},
            headers=getattr(exc, "headers", None),
        )
    return await http_exception_handler(request, exc)


async def unhandled_exception_handler(request: Request, exc: Exception):
    ref = _reference(request)
    logger.exception("Unhandled error on %s %s [ref %s]", request.method, request.url.path, ref)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{GENERIC_500} Reference: {ref}", "reference": ref},
    )


def install(app) -> None:
    app.add_exception_handler(StarletteHTTPException, scrubbed_http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
