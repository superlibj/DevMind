"""
Pydantic models for authentication API endpoints.

This module provides request/response models for user authentication,
registration, profile management, and token operations.
"""
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from .common import BaseResponse


class UserRegisterRequest(BaseModel):
    """User registration request model."""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$",
                         description="Username (alphanumeric, underscore, hyphen only)")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, max_length=100, description="Password (minimum 8 characters)")
    full_name: Optional[str] = Field(None, max_length=100, description="User's full name")
    accept_terms: bool = Field(..., description="User must accept terms and conditions")

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain uppercase, lowercase, and numeric characters')

        return v

    @validator('accept_terms')
    def validate_terms_acceptance(cls, v):
        """Ensure terms are accepted."""
        if not v:
            raise ValueError('Terms and conditions must be accepted')
        return v

    class Config:
        schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "SecurePass123",
                "full_name": "John Doe",
                "accept_terms": True
            }
        }


class UserLoginRequest(BaseModel):
    """User login request model."""
    username: str = Field(..., min_length=1, description="Username or email address")
    password: str = Field(..., min_length=1, description="User password")
    remember_me: bool = Field(False, description="Whether to extend token expiration")

    class Config:
        schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "SecurePass123",
                "remember_me": False
            }
        }


class TokenResponse(BaseResponse):
    """Authentication token response model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    permissions: List[str] = Field(..., description="User permissions")
    refresh_token: Optional[str] = Field(None, description="Refresh token (if remember_me is True)")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user_id": "user_123456",
                "username": "john_doe",
                "permissions": ["basic", "code_generation"]
            }
        }


class UserProfileResponse(BaseResponse):
    """User profile response model."""
    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    permissions: List[str] = Field(..., description="User permissions")
    created_at: str = Field(..., description="Account creation timestamp")
    last_login: Optional[str] = Field(None, description="Last login timestamp")
    is_active: bool = Field(..., description="Whether the account is active")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    preferences: Optional[dict] = Field(None, description="User preferences")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "user_id": "user_123456",
                "username": "john_doe",
                "email": "john@example.com",
                "full_name": "John Doe",
                "permissions": ["basic", "code_generation"],
                "created_at": "2023-01-01T00:00:00Z",
                "last_login": "2023-01-02T12:00:00Z",
                "is_active": True
            }
        }


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    current_password: str = Field(..., min_length=1, description="Current password for verification")
    new_password: str = Field(..., min_length=8, max_length=100,
                             description="New password (minimum 8 characters)")
    confirm_password: str = Field(..., description="New password confirmation")

    @validator('new_password')
    def validate_new_password_strength(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain uppercase, lowercase, and numeric characters')

        return v

    @validator('confirm_password')
    def validate_passwords_match(cls, v, values):
        """Ensure passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

    class Config:
        schema_extra = {
            "example": {
                "current_password": "OldPassword123",
                "new_password": "NewSecurePass456",
                "confirm_password": "NewSecurePass456"
            }
        }


class TokenRefreshRequest(BaseModel):
    """Token refresh request model."""
    refresh_token: str = Field(..., description="Valid refresh token")

    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class TokenVerifyResponse(BaseResponse):
    """Token verification response model."""
    valid: bool = Field(..., description="Whether the token is valid")
    user_id: str = Field(..., description="User identifier from token")
    username: str = Field(..., description="Username from token")
    permissions: List[str] = Field(..., description="User permissions from token")
    expires_at: Optional[int] = Field(None, description="Token expiration timestamp")
    issued_at: Optional[int] = Field(None, description="Token issuance timestamp")
    time_until_expiry: Optional[int] = Field(None, description="Seconds until token expires")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "valid": True,
                "user_id": "user_123456",
                "username": "john_doe",
                "permissions": ["basic", "code_generation"],
                "expires_at": 1672531200,
                "issued_at": 1672527600,
                "time_until_expiry": 3600
            }
        }


class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    email: EmailStr = Field(..., description="Email address for password reset")

    class Config:
        schema_extra = {
            "example": {
                "email": "john@example.com"
            }
        }


class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation request model."""
    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(..., min_length=8, max_length=100,
                             description="New password (minimum 8 characters)")
    confirm_password: str = Field(..., description="New password confirmation")

    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain uppercase, lowercase, and numeric characters')

        return v

    @validator('confirm_password')
    def validate_passwords_match(cls, v, values):
        """Ensure passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

    class Config:
        schema_extra = {
            "example": {
                "token": "reset_token_123456",
                "new_password": "NewSecurePass456",
                "confirm_password": "NewSecurePass456"
            }
        }


class UserPermission(BaseModel):
    """User permission model."""
    name: str = Field(..., description="Permission name")
    description: str = Field(..., description="Permission description")
    category: str = Field(..., description="Permission category")


class PermissionsResponse(BaseResponse):
    """Available permissions response model."""
    permissions: List[UserPermission] = Field(..., description="List of available permissions")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "permissions": [
                    {
                        "name": "code_generation",
                        "description": "Generate code using AI",
                        "category": "agent"
                    },
                    {
                        "name": "code_review",
                        "description": "Review code for quality and security",
                        "category": "agent"
                    }
                ]
            }
        }


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    created_at: str = Field(..., description="Session creation timestamp")
    last_activity: str = Field(..., description="Last activity timestamp")
    ip_address: str = Field(..., description="Client IP address")
    user_agent: str = Field(..., description="Client user agent")
    is_active: bool = Field(..., description="Whether session is active")


class ActiveSessionsResponse(BaseResponse):
    """Active sessions response model."""
    sessions: List[SessionInfo] = Field(..., description="List of active sessions")
    total_sessions: int = Field(..., description="Total number of active sessions")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "sessions": [
                    {
                        "session_id": "session_123",
                        "user_id": "user_456",
                        "created_at": "2023-01-01T00:00:00Z",
                        "last_activity": "2023-01-01T01:00:00Z",
                        "ip_address": "192.168.1.100",
                        "user_agent": "Mozilla/5.0...",
                        "is_active": True
                    }
                ],
                "total_sessions": 1
            }
        }