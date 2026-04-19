"""
Middleware modules for the AI Code Development Agent API.

This package contains middleware for:
- Authentication and authorization (JWT)
- Request/response logging with correlation IDs
- Rate limiting with token bucket algorithm
"""

from .auth import JWTMiddleware, auth_manager, get_current_user, require_auth, require_permission
from .logging import LoggingMiddleware, StructuredLogger, agent_logger, security_logger, tools_logger
from .rate_limit import RateLimitMiddleware, RateLimitConfig, TokenBucket

__all__ = [
    "JWTMiddleware",
    "LoggingMiddleware",
    "RateLimitMiddleware",
    "RateLimitConfig",
    "TokenBucket",
    "StructuredLogger",
    "auth_manager",
    "get_current_user",
    "require_auth",
    "require_permission",
    "agent_logger",
    "security_logger",
    "tools_logger"
]