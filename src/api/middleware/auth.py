"""
JWT Authentication middleware for the FastAPI application.

This middleware handles JWT token validation and user authentication
for protected routes.
"""
import logging
import time
from typing import Optional, Dict, Any, Set

from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config.settings import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme for OpenAPI
security = HTTPBearer(auto_error=False)


class JWTMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""

    def __init__(self, app):
        """Initialize JWT middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)

        # Routes that don't require authentication
        self.public_routes: Set[str] = {
            "/",
            "/health",
            "/health/",
            "/health/status",
            "/health/ready",
            "/auth/login",
            "/auth/register",
            "/docs",
            "/redoc",
            "/openapi.json"
        }

        # Route prefixes that don't require authentication
        self.public_prefixes: Set[str] = {
            "/health/",
            "/auth/",
            "/static/"
        }

    async def dispatch(self, request: Request, call_next):
        """Process request and validate JWT if required.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response
        """
        # Skip authentication for public routes
        if self._is_public_route(request.url.path):
            return await call_next(request)

        # Extract and validate JWT token
        try:
            user_info = await self._authenticate_request(request)

            # Add user info to request state
            request.state.user = user_info
            request.state.user_id = user_info.get("sub")
            request.state.authenticated = True

        except HTTPException as e:
            # Return authentication error
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.detail,
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Authentication service error",
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            )

        # Continue to next middleware/route
        response = await call_next(request)
        return response

    def _is_public_route(self, path: str) -> bool:
        """Check if route is public (doesn't require authentication).

        Args:
            path: Request path

        Returns:
            True if route is public
        """
        # Check exact matches
        if path in self.public_routes:
            return True

        # Check prefix matches
        for prefix in self.public_prefixes:
            if path.startswith(prefix):
                return True

        return False

    async def _authenticate_request(self, request: Request) -> Dict[str, Any]:
        """Authenticate request using JWT token.

        Args:
            request: HTTP request

        Returns:
            User information from JWT payload

        Raises:
            HTTPException: If authentication fails
        """
        # Extract token from Authorization header
        token = self._extract_token(request)

        if not token:
            raise HTTPException(
                status_code=401,
                detail="Authorization token required"
            )

        # Validate and decode JWT token
        try:
            payload = jwt.decode(
                token,
                settings.security.jwt_secret_key,
                algorithms=[settings.security.jwt_algorithm]
            )

            # Check token expiration
            exp = payload.get("exp")
            if exp and exp < time.time():
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired"
                )

            # Validate required claims
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token: missing user ID"
                )

            logger.debug(f"Authenticated user: {user_id}")
            return payload

        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid or malformed token"
            )

    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request.

        Args:
            request: HTTP request

        Returns:
            JWT token string or None
        """
        # Try Authorization header first
        authorization = request.headers.get("Authorization")
        if authorization:
            try:
                scheme, token = authorization.split()
                if scheme.lower() == "bearer":
                    return token
            except ValueError:
                pass

        # Try query parameter (for WebSocket)
        token = request.query_params.get("token")
        if token:
            return token

        # Try cookie (if configured)
        token = request.cookies.get("access_token")
        if token:
            return token

        return None


class AuthManager:
    """Authentication manager for user operations."""

    def __init__(self):
        """Initialize auth manager."""
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash password.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[int] = None
    ) -> str:
        """Create JWT access token.

        Args:
            data: Token payload data
            expires_delta: Token expiration in seconds

        Returns:
            JWT token string
        """
        to_encode = data.copy()

        # Set expiration
        if expires_delta:
            expire = time.time() + expires_delta
        else:
            expire = time.time() + (settings.security.jwt_expiration_hours * 3600)

        to_encode.update({
            "exp": expire,
            "iat": time.time(),
            "type": "access"
        })

        # Create JWT token
        encoded_jwt = jwt.encode(
            to_encode,
            settings.security.jwt_secret_key,
            algorithm=settings.security.jwt_algorithm
        )

        return encoded_jwt

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token.

        Args:
            token: JWT token string

        Returns:
            Token payload

        Raises:
            JWTError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.security.jwt_secret_key,
                algorithms=[settings.security.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            logger.warning(f"Token decode failed: {e}")
            raise

    def create_user_token(
        self,
        user_id: str,
        username: str,
        permissions: Optional[list] = None
    ) -> str:
        """Create user access token.

        Args:
            user_id: User ID
            username: Username
            permissions: User permissions list

        Returns:
            JWT access token
        """
        token_data = {
            "sub": user_id,
            "username": username,
            "permissions": permissions or [],
            "token_type": "access"
        }

        return self.create_access_token(token_data)


# Global auth manager instance
auth_manager = AuthManager()


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current authenticated user from request state.

    Args:
        request: HTTP request

    Returns:
        User information or None
    """
    return getattr(request.state, "user", None)


def require_auth(request: Request) -> Dict[str, Any]:
    """Require authentication and return user info.

    Args:
        request: HTTP request

    Returns:
        User information

    Raises:
        HTTPException: If user not authenticated
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return user


def require_permission(request: Request, permission: str) -> Dict[str, Any]:
    """Require specific permission and return user info.

    Args:
        request: HTTP request
        permission: Required permission

    Returns:
        User information

    Raises:
        HTTPException: If user lacks permission
    """
    user = require_auth(request)
    user_permissions = user.get("permissions", [])

    if permission not in user_permissions and "admin" not in user_permissions:
        raise HTTPException(
            status_code=403,
            detail=f"Permission required: {permission}"
        )

    return user