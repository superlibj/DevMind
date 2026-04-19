"""
Unit tests for authentication functionality.

Tests JWT token creation, validation, password hashing,
and authentication middleware components.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.api.middleware.auth import auth_manager, JWTMiddleware
from jose import JWTError


@pytest.mark.unit
class TestAuthManager:
    """Test cases for AuthManager class."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123"

        # Hash password
        hashed = auth_manager.get_password_hash(password)

        # Verify password
        assert auth_manager.verify_password(password, hashed) is True
        assert auth_manager.verify_password("wrong_password", hashed) is False

    def test_password_hash_consistency(self):
        """Test that password hashing produces different hashes for same password."""
        password = "test_password_123"

        hash1 = auth_manager.get_password_hash(password)
        hash2 = auth_manager.get_password_hash(password)

        # Hashes should be different (due to salt)
        assert hash1 != hash2

        # But both should verify correctly
        assert auth_manager.verify_password(password, hash1) is True
        assert auth_manager.verify_password(password, hash2) is True

    def test_create_access_token(self):
        """Test JWT token creation."""
        user_data = {
            "sub": "test_user_123",
            "username": "testuser",
            "permissions": ["basic"]
        }

        token = auth_manager.create_access_token(user_data)

        # Token should be a string
        assert isinstance(token, str)

        # Token should have 3 parts (header.payload.signature)
        parts = token.split(".")
        assert len(parts) == 3

    def test_create_access_token_with_expiration(self):
        """Test JWT token creation with custom expiration."""
        user_data = {
            "sub": "test_user_123",
            "username": "testuser"
        }

        # Create token with 1 hour expiration
        token = auth_manager.create_access_token(user_data, expires_delta=3600)

        # Decode and verify expiration
        payload = auth_manager.decode_token(token)
        assert "exp" in payload

        # Expiration should be approximately 1 hour from now
        exp_time = payload["exp"]
        now = datetime.now(timezone.utc).timestamp()
        assert 3500 < (exp_time - now) < 3700  # Allow some tolerance

    def test_decode_token_valid(self):
        """Test decoding valid JWT token."""
        user_data = {
            "sub": "test_user_123",
            "username": "testuser",
            "permissions": ["basic"]
        }

        token = auth_manager.create_access_token(user_data)
        decoded = auth_manager.decode_token(token)

        # Check required fields
        assert decoded["sub"] == user_data["sub"]
        assert decoded["username"] == user_data["username"]
        assert decoded["permissions"] == user_data["permissions"]
        assert "exp" in decoded
        assert "iat" in decoded
        assert decoded["type"] == "access"

    def test_decode_token_invalid(self):
        """Test decoding invalid JWT token."""
        # Test with invalid token
        with pytest.raises(JWTError):
            auth_manager.decode_token("invalid_token")

        # Test with malformed token
        with pytest.raises(JWTError):
            auth_manager.decode_token("invalid.token.format")

    def test_create_user_token(self):
        """Test creating user-specific token."""
        token = auth_manager.create_user_token(
            user_id="test_123",
            username="testuser",
            permissions=["basic", "code_generation"]
        )

        decoded = auth_manager.decode_token(token)

        assert decoded["sub"] == "test_123"
        assert decoded["username"] == "testuser"
        assert decoded["permissions"] == ["basic", "code_generation"]
        assert decoded["token_type"] == "access"

    def test_create_user_token_default_permissions(self):
        """Test creating user token with default permissions."""
        token = auth_manager.create_user_token(
            user_id="test_123",
            username="testuser"
        )

        decoded = auth_manager.decode_token(token)
        assert decoded["permissions"] == []


@pytest.mark.unit
class TestJWTMiddleware:
    """Test cases for JWT authentication middleware."""

    def test_is_public_route(self):
        """Test public route identification."""
        middleware = JWTMiddleware(Mock())

        # Test exact matches
        assert middleware._is_public_route("/health") is True
        assert middleware._is_public_route("/auth/login") is True
        assert middleware._is_public_route("/docs") is True

        # Test prefix matches
        assert middleware._is_public_route("/health/status") is True
        assert middleware._is_public_route("/auth/register") is True
        assert middleware._is_public_route("/static/css/style.css") is True

        # Test protected routes
        assert middleware._is_public_route("/api/v1/chat") is False
        assert middleware._is_public_route("/api/v1/generate") is False
        assert middleware._is_public_route("/user/profile") is False

    def test_extract_token_from_header(self):
        """Test token extraction from Authorization header."""
        middleware = JWTMiddleware(Mock())

        # Mock request with Bearer token
        request = Mock()
        request.headers = {"Authorization": "Bearer test_token_123"}
        request.query_params = {}
        request.cookies = {}

        token = middleware._extract_token(request)
        assert token == "test_token_123"

    def test_extract_token_from_query(self):
        """Test token extraction from query parameter."""
        middleware = JWTMiddleware(Mock())

        # Mock request with token query parameter
        request = Mock()
        request.headers = {}
        request.query_params = {"token": "test_token_123"}
        request.cookies = {}

        token = middleware._extract_token(request)
        assert token == "test_token_123"

    def test_extract_token_from_cookie(self):
        """Test token extraction from cookie."""
        middleware = JWTMiddleware(Mock())

        # Mock request with token cookie
        request = Mock()
        request.headers = {}
        request.query_params = {}
        request.cookies = {"access_token": "test_token_123"}

        token = middleware._extract_token(request)
        assert token == "test_token_123"

    def test_extract_token_priority(self):
        """Test token extraction priority (header > query > cookie)."""
        middleware = JWTMiddleware(Mock())

        # Mock request with all token sources
        request = Mock()
        request.headers = {"Authorization": "Bearer header_token"}
        request.query_params = {"token": "query_token"}
        request.cookies = {"access_token": "cookie_token"}

        # Header should take priority
        token = middleware._extract_token(request)
        assert token == "header_token"

    def test_extract_token_no_token(self):
        """Test token extraction when no token provided."""
        middleware = JWTMiddleware(Mock())

        # Mock request without any token
        request = Mock()
        request.headers = {}
        request.query_params = {}
        request.cookies = {}

        token = middleware._extract_token(request)
        assert token is None

    def test_extract_token_invalid_header_format(self):
        """Test token extraction with invalid header format."""
        middleware = JWTMiddleware(Mock())

        # Mock request with invalid Authorization header
        request = Mock()
        request.headers = {"Authorization": "InvalidFormat"}
        request.query_params = {}
        request.cookies = {}

        token = middleware._extract_token(request)
        assert token is None

    @pytest.mark.asyncio
    async def test_authenticate_request_valid_token(self, mock_user):
        """Test successful authentication with valid token."""
        middleware = JWTMiddleware(Mock())

        # Create a valid token
        token = auth_manager.create_access_token(mock_user)

        # Mock request with valid token
        request = Mock()
        request.headers = {"Authorization": f"Bearer {token}"}
        request.query_params = {}
        request.cookies = {}

        # Should return user info without raising exception
        user_info = await middleware._authenticate_request(request)

        assert user_info["sub"] == mock_user["sub"]
        assert user_info["username"] == mock_user["username"]

    @pytest.mark.asyncio
    async def test_authenticate_request_no_token(self):
        """Test authentication failure with no token."""
        from fastapi import HTTPException

        middleware = JWTMiddleware(Mock())

        # Mock request without token
        request = Mock()
        request.headers = {}
        request.query_params = {}
        request.cookies = {}

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await middleware._authenticate_request(request)

        assert exc_info.value.status_code == 401
        assert "Authorization token required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_request_invalid_token(self):
        """Test authentication failure with invalid token."""
        from fastapi import HTTPException

        middleware = JWTMiddleware(Mock())

        # Mock request with invalid token
        request = Mock()
        request.headers = {"Authorization": "Bearer invalid_token"}
        request.query_params = {}
        request.cookies = {}

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await middleware._authenticate_request(request)

        assert exc_info.value.status_code == 401
        assert "Invalid or malformed token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_request_expired_token(self, mock_user):
        """Test authentication failure with expired token."""
        from fastapi import HTTPException

        middleware = JWTMiddleware(Mock())

        # Create expired token (expires in past)
        expired_data = mock_user.copy()
        expired_data["exp"] = 1640000000  # Some time in the past

        with patch.object(auth_manager, "decode_token", return_value=expired_data):
            request = Mock()
            request.headers = {"Authorization": "Bearer expired_token"}
            request.query_params = {}
            request.cookies = {}

            with pytest.raises(HTTPException) as exc_info:
                await middleware._authenticate_request(request)

            assert exc_info.value.status_code == 401
            assert "Token has expired" in str(exc_info.value.detail)