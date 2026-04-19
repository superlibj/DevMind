"""
Main FastAPI application for AI Code Development Agent.

This module sets up the FastAPI application with all routes, middleware,
and configuration for the AI agent web interface.
"""
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
import uvicorn

from .routes import agent, health, auth
from .middleware.auth import JWTMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.logging import LoggingMiddleware
from src.core.tools import initialize_acp_integration
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.app.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting AI Code Development Agent API...")

    try:
        # Initialize tool integration
        initialize_acp_integration()
        logger.info("✓ ACP tool integration initialized")

        # Additional startup tasks can be added here
        # - Database connections
        # - Cache initialization
        # - Background task setup

        logger.info("✓ Application startup complete")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down AI Code Development Agent API...")

    try:
        # Cleanup tasks
        # - Close database connections
        # - Stop background tasks
        # - Save state if needed

        logger.info("✓ Application shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app.app_name,
    description="""
    AI Code Development Agent API

    A comprehensive AI-powered development assistant that provides:
    - Secure code generation with vulnerability scanning
    - Intelligent code review and analysis
    - Smart refactoring and optimization
    - AI-assisted debugging and error resolution
    - Real-time chat interface via WebSocket
    - Integration with development tools (git, vim, file operations)

    ## Features

    - **Security-First**: All AI-generated code is automatically scanned for vulnerabilities
    - **Multi-Provider LLM**: Support for OpenAI, Anthropic Claude, and local models
    - **ReAct Agent**: Production-proven reasoning and acting cycles for complex tasks
    - **Tool Integration**: Safe integration with git, file operations, and vim
    - **Real-time Interface**: WebSocket support for live chat interactions

    ## Authentication

    This API uses JWT (JSON Web Tokens) for authentication. Include your JWT token
    in the Authorization header:

    ```
    Authorization: Bearer <your-jwt-token>
    ```

    ## Rate Limiting

    API endpoints are rate limited to ensure fair usage and system stability.
    Default limits: 100 requests per minute per user.

    ## WebSocket Chat

    Real-time chat is available via WebSocket at `/ws/chat`. Authentication is
    required via query parameter: `/ws/chat?token=<your-jwt-token>`
    """,
    version=settings.app.version,
    docs_url="/docs" if settings.app.debug else None,
    redoc_url="/redoc" if settings.app.debug else None,
    openapi_url="/openapi.json" if settings.app.debug else None,
    lifespan=lifespan
)


# Add middleware (order matters - first added = outermost layer)

# Logging middleware (outermost)
app.add_middleware(LoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining"]
)

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# JWT authentication middleware (innermost for protected routes)
app.add_middleware(JWTMiddleware)


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(agent.router, prefix=settings.app.api_prefix, tags=["Agent"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Don't expose internal errors in production
    if settings.app.is_production:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later.",
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "type": type(exc).__name__,
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        )


# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", "unknown")
        }
    )


# Root endpoint
@app.get("/", include_in_schema=False)
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "name": settings.app.app_name,
        "version": settings.app.version,
        "status": "running",
        "docs": "/docs" if settings.app.debug else "Documentation disabled in production",
        "health": "/health",
        "api": settings.app.api_prefix
    }


# Custom OpenAPI documentation (if enabled)
if settings.app.debug:

    def custom_openapi():
        """Generate custom OpenAPI schema."""
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=settings.app.app_name,
            version=settings.app.version,
            description=app.description,
            routes=app.routes,
        )

        # Add security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token authentication"
            }
        }

        # Add global security requirement
        openapi_schema["security"] = [{"BearerAuth": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi


# Development server configuration
def run_dev_server():
    """Run development server with hot reload."""
    uvicorn.run(
        "src.api.main:app",
        host=settings.app.api_host,
        port=settings.app.api_port,
        reload=settings.app.debug,
        log_level="debug" if settings.app.debug else "info",
        access_log=settings.app.debug
    )


if __name__ == "__main__":
    run_dev_server()