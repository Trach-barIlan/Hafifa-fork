"""Centralized FastAPI exception handlers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from logging_config import logger


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle standard Python ValueError as HTTP 400 Bad Request."""
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


async def lookup_error_handler(request: Request, exc: LookupError) -> JSONResponse:
    """Handle Python LookupError / KeyError as HTTP 404 Not Found."""
    logger.info(f"Resource not found on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )
