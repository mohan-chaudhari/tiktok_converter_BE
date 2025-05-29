from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from src.config.settings import logger
from pydantic import ValidationError

async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions globally"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with custom logging"""
    logger.warning(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )
