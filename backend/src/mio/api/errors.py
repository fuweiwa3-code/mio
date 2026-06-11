import logging
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", str(uuid4()))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "trace_id": _trace_id(request),
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message": "请求参数不符合接口要求。",
                "trace_id": _trace_id(request),
                "details": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        trace_id = _trace_id(request)
        logger.error(
            "Unhandled exception trace_id=%s type=%s",
            trace_id,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "message": "服务暂时不可用，请稍后重试。",
                "trace_id": trace_id,
                "details": {},
            },
        )
