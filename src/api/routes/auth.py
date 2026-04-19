"""
Authentication routes for user registration, login, and token management.

This module provides JWT-based authentication endpoints for the AI agent
web interface.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from src.api.middleware.auth import auth_manager, get_current_user, require_auth
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)


# Request/Response Models
class UserRegisterRequest(BaseModel):
    """User registration request model."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")


class UserLoginRequest(BaseModel):
    """User login request model."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Authentication token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str
    permissions: List[str]


class UserProfileResponse(BaseModel):
    """User profile response model."""
    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    permissions: List[str]
    created_at: str
    last_login: Optional[str]
    is_active: bool


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class TokenRefreshRequest(BaseModel):
    """Token refresh request model."""
    refresh_token: str = Field(..., description="Refresh token")


# Mock user database (replace with real database in production)
MOCK_USERS = {
    "admin": {
        "user_id": "admin_user_001",
        "username": "admin",
        "email": "admin@example.com",
        "password_hash": auth_manager.get_password_hash("admin123"),
        "full_name": "System Administrator",
        "permissions": ["admin", "premium"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
        "is_active": True
    },
    "user": {
        "user_id": "basic_user_001",
        "username": "user",
        "email": "user@example.com",
        "password_hash": auth_manager.get_password_hash("user123"),
        "full_name": "Test User",
        "permissions": ["basic"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
        "is_active": True
    }
}


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username or email.

    Args:
        username: Username or email

    Returns:
        User data or None
    """
    # Check by username
    user = MOCK_USERS.get(username)
    if user:
        return user

    # Check by email
    for user_data in MOCK_USERS.values():
        if user_data["email"].lower() == username.lower():
            return user_data

    return None


def create_user(user_data: UserRegisterRequest) -> Dict[str, Any]:
    """Create a new user.

    Args:
        user_data: User registration data

    Returns:
        Created user data

    Raises:
        HTTPException: If user already exists
    """
    # Check if user already exists
    if get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )

    if get_user_by_username(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Create user
    user_id = f"user_{int(time.time())}"
    new_user = {
        "user_id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": auth_manager.get_password_hash(user_data.password),
        "full_name": user_data.full_name,
        "permissions": ["basic"],  # Default permissions
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
        "is_active": True
    }

    # Store user (in production, save to database)
    MOCK_USERS[user_data.username] = new_user

    return new_user


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user credentials.

    Args:
        username: Username or email
        password: Password

    Returns:
        User data if authentication successful, None otherwise
    """
    user = get_user_by_username(username)
    if not user:
        return None

    if not user["is_active"]:
        return None

    if not auth_manager.verify_password(password, user["password_hash"]):
        return None

    # Update last login
    user["last_login"] = datetime.now(timezone.utc).isoformat()

    return user


@router.post("/register", response_model=TokenResponse, summary="Register new user")
async def register(user_data: UserRegisterRequest) -> TokenResponse:
    """
    Register a new user account.

    Creates a new user account and returns an authentication token.
    The user can immediately start using the API with the returned token.
    """
    try:
        # Create user
        user = create_user(user_data)

        # Generate access token
        token = auth_manager.create_user_token(
            user_id=user["user_id"],
            username=user["username"],
            permissions=user["permissions"]
        )

        logger.info(f"User registered successfully: {user['username']}")

        return TokenResponse(
            access_token=token,
            expires_in=settings.security.jwt_expiration_hours * 3600,
            user_id=user["user_id"],
            username=user["username"],
            permissions=user["permissions"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse, summary="User login")
async def login(credentials: UserLoginRequest) -> TokenResponse:
    """
    Authenticate user and return access token.

    Validates user credentials and returns a JWT token for API access.
    The token should be included in the Authorization header for subsequent requests.
    """
    try:
        # Authenticate user
        user = authenticate_user(credentials.username, credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate access token
        token = auth_manager.create_user_token(
            user_id=user["user_id"],
            username=user["username"],
            permissions=user["permissions"]
        )

        logger.info(f"User logged in successfully: {user['username']}")

        return TokenResponse(
            access_token=token,
            expires_in=settings.security.jwt_expiration_hours * 3600,
            user_id=user["user_id"],
            username=user["username"],
            permissions=user["permissions"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/profile", response_model=UserProfileResponse, summary="Get user profile")
async def get_profile(request: Request, user: Dict[str, Any] = Depends(require_auth)) -> UserProfileResponse:
    """
    Get current user's profile information.

    Returns the profile information for the currently authenticated user.
    Requires a valid JWT token in the Authorization header.
    """
    try:
        # Get full user data
        full_user = get_user_by_username(user["username"])
        if not full_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserProfileResponse(
            user_id=full_user["user_id"],
            username=full_user["username"],
            email=full_user["email"],
            full_name=full_user["full_name"],
            permissions=full_user["permissions"],
            created_at=full_user["created_at"],
            last_login=full_user["last_login"],
            is_active=full_user["is_active"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        )


@router.put("/password", summary="Change password")
async def change_password(
    request: Request,
    password_data: PasswordChangeRequest,
    user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, str]:
    """
    Change user's password.

    Allows authenticated users to change their password by providing
    their current password and a new password.
    """
    try:
        # Get full user data
        full_user = get_user_by_username(user["username"])
        if not full_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify current password
        if not auth_manager.verify_password(password_data.current_password, full_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        # Update password
        full_user["password_hash"] = auth_manager.get_password_hash(password_data.new_password)

        logger.info(f"Password changed for user: {user['username']}")

        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/logout", summary="User logout")
async def logout(request: Request, user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, str]:
    """
    Logout current user.

    Invalidates the current session. In a production system, this would
    add the token to a blacklist. For now, it just logs the logout event.
    """
    try:
        logger.info(f"User logged out: {user['username']}")

        return {"message": "Logged out successfully"}

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/verify-token", summary="Verify token")
async def verify_token(request: Request, user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """
    Verify the validity of the current JWT token.

    Returns token information if the token is valid. This can be used
    by client applications to check if their stored token is still valid.
    """
    try:
        return {
            "valid": True,
            "user_id": user["sub"],
            "username": user["username"],
            "permissions": user["permissions"],
            "expires_at": user.get("exp"),
            "issued_at": user.get("iat")
        }

    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )