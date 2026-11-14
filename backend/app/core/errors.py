"""Errors are returned as stable machine-readable codes.

The frontend translates `error.code` into the user's language; `message` is an
English fallback for developers only.

Response shape:
    {"error": {"code": "auth.invalid_credentials", "message": "...", "params": {}}}
Validation errors:
    {"error": {"code": "validation_error", "message": "...",
               "fields": [{"field": "password", "code": "string_too_short", "message": "..."}]}}
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        message: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or code)
        self.code = code
        self.status_code = status_code
        self.message = message or code
        self.params = params or {}

    def with_params(self, **params: Any) -> "AppError":
        self.params.update(params)
        return self


class NotFound(AppError):
    def __init__(self, code: str = "not_found", message: str = "Not found") -> None:
        super().__init__(code, status.HTTP_404_NOT_FOUND, message)


class Forbidden(AppError):
    def __init__(self, code: str = "forbidden", message: str = "Forbidden") -> None:
        super().__init__(code, status.HTTP_403_FORBIDDEN, message)


class Unauthorized(AppError):
    def __init__(self, code: str = "auth.unauthorized", message: str = "Not authenticated") -> None:
        super().__init__(code, status.HTTP_401_UNAUTHORIZED, message)


class Conflict(AppError):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(code, status.HTTP_409_CONFLICT, message)


def _error_body(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, **extra}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        headers = None
        if exc.status_code == 401:
            headers = {"WWW-Authenticate": "Bearer"}
        elif exc.status_code == 429 and "retry_after" in exc.params:
            headers = {"Retry-After": str(exc.params["retry_after"])}
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, params=exc.params),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            fields.append(
                {"field": ".".join(loc), "code": err.get("type"), "message": err.get("msg")}
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body("validation_error", "Invalid request", fields=fields),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "auth.unauthorized", 403: "forbidden", 404: "not_found"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code, str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )
