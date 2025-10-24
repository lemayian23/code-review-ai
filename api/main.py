"""
FastAPI application for Code Review AI
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import make_asgi_app
from sentry_sdk.integrations.fastapi import FastApiIntegration

from api.middleware.auth import AuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.routers import analyze, feedback, health
from core.config import get_settings
from observability.logging import setup_logging
from observability.metrics import setup_metrics
from observability.tracing import setup_tracing

# Configure structured logging
setup_logging()
logger = structlog.get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Code Review AI API")
    setup_metrics()
    setup_tracing()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Code Review AI API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Code Review AI",
        description="Intelligent Code Review Assistant with Contextual Learning",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    # Custom middleware
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(analyze.router, prefix="/api/v1/analyze", tags=["analyze"])
    app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])

    # Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


app = create_app()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Code Review AI API",
        "version": "0.1.0",
        "status": "healthy"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
