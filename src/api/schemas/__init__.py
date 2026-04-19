"""
Pydantic models for API request/response validation.

This module provides comprehensive data models for all API endpoints
with proper validation, documentation, and type safety.
"""

from .agent import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CodeGenerationRequest,
    CodeGenerationResponse,
    CodeReviewRequest,
    CodeReviewResponse,
    CodeRefactorRequest,
    CodeRefactorResponse,
    DebugRequest,
    DebugResponse
)

from .auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserProfileResponse,
    PasswordChangeRequest,
    TokenRefreshRequest
)

from .health import (
    HealthStatus,
    DetailedHealthStatus,
    ReadinessStatus
)

from .common import (
    BaseResponse,
    ErrorResponse,
    ValidationErrorResponse
)

__all__ = [
    # Agent schemas
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "CodeGenerationRequest",
    "CodeGenerationResponse",
    "CodeReviewRequest",
    "CodeReviewResponse",
    "CodeRefactorRequest",
    "CodeRefactorResponse",
    "DebugRequest",
    "DebugResponse",

    # Auth schemas
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserProfileResponse",
    "PasswordChangeRequest",
    "TokenRefreshRequest",

    # Health schemas
    "HealthStatus",
    "DetailedHealthStatus",
    "ReadinessStatus",

    # Common schemas
    "BaseResponse",
    "ErrorResponse",
    "ValidationErrorResponse"
]