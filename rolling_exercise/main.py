"""Main FastAPI application entrypoint for Air Quality API."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import settings
from database import init_db
from exceptions import lookup_error_handler, value_error_handler
from logging_config import logger
from routers import air_quality, alerts


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to initialize resources on startup."""
    logger.info("Initializing database tables...")
    init_db()
    logger.info(f"{settings.app_name} started successfully.")
    yield
    logger.info(f"{settings.app_name} shutting down.")


app = FastAPI(
    title=settings.app_name,
    description="API for ingesting, calculating AQI, and querying air quality records and alerts.",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# Register centralized exception handlers
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(LookupError, lookup_error_handler)

# Allow CORS for development convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(air_quality.router)
app.include_router(alerts.router)


@app.get("/", tags=["Health"])
def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok", "service": "Air Quality API"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
