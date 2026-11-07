# app/middleware/failure_log.py
"""Failure log: every failed request (status >= 400) and unhandled exception is
recorded in ``t_log``. Successful requests are not logged."""

import time
import traceback

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services import request_log
from app.utils import decode_access_token


async def _http_error(request: Request, exc: StarletteHTTPException):
    # Keep the underlying cause (e.g. the Gemini error behind a generic 502).
    request.state.error = request_log.describe(exc)
    return await http_exception_handler(request, exc)


async def _validation_error(request: Request, exc: RequestValidationError):
    # Field names + messages only: submitted values (code, emails) stay out of the log.
    request.state.error = "; ".join(
        f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
    )
    return await request_validation_exception_handler(request, exc)


def _user_email(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    payload = decode_access_token(auth[7:].strip())
    return payload.get("sub") if payload else None


async def log_failures(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        # The end of the traceback has the actual error.
        request.state.error = "".join(traceback.format_exception(exc))[-2000:]
        response = JSONResponse({"detail": "Internal Server Error"}, status_code=500)
    if response.status_code >= 400:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        await run_in_threadpool(
            request_log.record,
            request.method,
            request.url.path,
            status=response.status_code,
            duration_ms=int((time.perf_counter() - started) * 1000),
            error=getattr(request.state, "error", None),
            client_ip=forwarded or (request.client.host if request.client else None),
            origin=request.headers.get("origin"),
            user_agent=request.headers.get("user-agent"),
            user_email=_user_email(request),
        )
    return response


def install(app: FastAPI) -> None:
    """Attach the failure log to the app (runs for every request)."""
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.middleware("http")(log_failures)
