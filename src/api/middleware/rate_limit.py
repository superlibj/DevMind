"""
Rate limiting middleware for the FastAPI application.

This middleware implements rate limiting using a token bucket algorithm
to prevent abuse and ensure fair usage of the API.
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Tuple
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config.settings import settings

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed successfully
        """
        async with self._lock:
            now = time.time()

            # Refill tokens based on time elapsed
            time_elapsed = now - self.last_refill
            tokens_to_add = time_elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now

            # Try to consume tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False

    def get_tokens(self) -> float:
        """Get current number of tokens."""
        now = time.time()
        time_elapsed = now - self.last_refill
        tokens_to_add = time_elapsed * self.refill_rate
        return min(self.capacity, self.tokens + tokens_to_add)

    def time_until_token(self) -> float:
        """Get time until next token is available."""
        if self.tokens >= 1:
            return 0.0

        tokens_needed = 1 - self.tokens
        return tokens_needed / self.refill_rate


class RateLimitConfig:
    """Rate limit configuration for different endpoints."""

    def __init__(self):
        """Initialize rate limit configuration."""
        # Default rate limits (requests per window)
        self.default_limit = settings.security.rate_limit_requests
        self.default_window = settings.security.rate_limit_window

        # Endpoint-specific rate limits
        self.endpoint_limits = {
            # Authentication endpoints (stricter)
            "/auth/login": (5, 60),       # 5 requests per minute
            "/auth/register": (3, 300),   # 3 requests per 5 minutes

            # Agent endpoints (moderate)
            "/api/v1/agent/chat": (60, 60),      # 60 requests per minute
            "/api/v1/agent/generate": (10, 60),  # 10 requests per minute
            "/api/v1/agent/review": (20, 60),    # 20 requests per minute
            "/api/v1/agent/refactor": (15, 60),  # 15 requests per minute
            "/api/v1/agent/debug": (20, 60),     # 20 requests per minute

            # Tool endpoints (moderate)
            "/api/v1/tools/": (30, 60),  # 30 requests per minute

            # Health endpoints (lenient)
            "/health": (300, 60),  # 300 requests per minute
        }

        # User type multipliers
        self.user_multipliers = {
            "admin": 10.0,      # Admins get 10x rate limit
            "premium": 3.0,     # Premium users get 3x
            "basic": 1.0,       # Basic users get standard rate
            "anonymous": 0.5    # Anonymous users get half rate
        }

    def get_limit(self, endpoint: str, user_type: str = "basic") -> Tuple[int, int]:
        """Get rate limit for endpoint and user type.

        Args:
            endpoint: API endpoint
            user_type: User type (admin, premium, basic, anonymous)

        Returns:
            Tuple of (requests, window_seconds)
        """
        # Find matching endpoint config
        limit, window = self.default_limit, self.default_window

        for pattern, (req_limit, req_window) in self.endpoint_limits.items():
            if endpoint.startswith(pattern):
                limit, window = req_limit, req_window
                break

        # Apply user type multiplier
        multiplier = self.user_multipliers.get(user_type, 1.0)
        limit = int(limit * multiplier)

        return limit, window


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket algorithm."""

    def __init__(self, app):
        """Initialize rate limit middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)
        self.config = RateLimitConfig()
        self.buckets: Dict[str, TokenBucket] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response
        """
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request):
            return await call_next(request)

        try:
            # Check rate limit
            client_id = self._get_client_id(request)
            user_type = self._get_user_type(request)
            endpoint = self._normalize_endpoint(request.url.path)

            # Get rate limit configuration
            limit, window = self.config.get_limit(endpoint, user_type)

            # Check and consume tokens
            allowed, retry_after = await self._check_rate_limit(
                client_id, endpoint, limit, window
            )

            if not allowed:
                # Rate limit exceeded
                return self._create_rate_limit_response(retry_after)

            # Add rate limit headers
            response = await call_next(request)
            self._add_rate_limit_headers(response, client_id, endpoint, limit, window)

            return response

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting on error
            return await call_next(request)

        finally:
            # Periodic cleanup of old buckets
            await self._cleanup_buckets()

    def _should_skip_rate_limit(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request.

        Args:
            request: HTTP request

        Returns:
            True if rate limiting should be skipped
        """
        # Skip for health checks
        if request.url.path.startswith("/health"):
            return True

        # Skip for static files
        if request.url.path.startswith("/static"):
            return True

        # Skip for documentation in development
        if settings.app.debug and request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return True

        return False

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting.

        Args:
            request: HTTP request

        Returns:
            Client identifier
        """
        # Try to get user ID from authentication
        user = getattr(request.state, "user", None)
        if user:
            return f"user:{user.get('sub', 'unknown')}"

        # Fall back to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address.

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Use client host
        return request.client.host if request.client else "unknown"

    def _get_user_type(self, request: Request) -> str:
        """Get user type for rate limiting.

        Args:
            request: HTTP request

        Returns:
            User type (admin, premium, basic, anonymous)
        """
        user = getattr(request.state, "user", None)
        if not user:
            return "anonymous"

        # Check user permissions/role
        permissions = user.get("permissions", [])
        if "admin" in permissions:
            return "admin"
        elif "premium" in permissions:
            return "premium"
        else:
            return "basic"

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for rate limiting.

        Args:
            path: Request path

        Returns:
            Normalized path
        """
        # Remove query parameters
        path = path.split("?")[0]

        # Normalize path parameters (e.g., /users/123 -> /users/)
        parts = path.split("/")
        normalized_parts = []

        for part in parts:
            if part.isdigit() or len(part) == 36:  # UUID length
                normalized_parts.append("*")
            else:
                normalized_parts.append(part)

        return "/".join(normalized_parts)

    async def _check_rate_limit(
        self,
        client_id: str,
        endpoint: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Optional[float]]:
        """Check rate limit for client and endpoint.

        Args:
            client_id: Client identifier
            endpoint: API endpoint
            limit: Request limit
            window: Time window in seconds

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        bucket_key = f"{client_id}:{endpoint}"

        # Get or create token bucket
        if bucket_key not in self.buckets:
            refill_rate = limit / window  # tokens per second
            self.buckets[bucket_key] = TokenBucket(limit, refill_rate)

        bucket = self.buckets[bucket_key]

        # Try to consume a token
        allowed = await bucket.consume(1)

        if allowed:
            return True, None
        else:
            retry_after = bucket.time_until_token()
            return False, retry_after

    def _create_rate_limit_response(self, retry_after: float) -> JSONResponse:
        """Create rate limit exceeded response.

        Args:
            retry_after: Seconds until retry is allowed

        Returns:
            JSON response with rate limit error
        """
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Try again in {retry_after:.1f} seconds.",
                "retry_after": retry_after
            },
            headers={
                "Retry-After": str(int(retry_after) + 1),
                "X-RateLimit-Reset": str(int(time.time() + retry_after))
            }
        )

    def _add_rate_limit_headers(
        self,
        response,
        client_id: str,
        endpoint: str,
        limit: int,
        window: int
    ):
        """Add rate limit headers to response.

        Args:
            response: HTTP response
            client_id: Client identifier
            endpoint: API endpoint
            limit: Request limit
            window: Time window
        """
        bucket_key = f"{client_id}:{endpoint}"
        bucket = self.buckets.get(bucket_key)

        if bucket:
            remaining = max(0, int(bucket.get_tokens()))
            reset_time = int(time.time() + (limit - remaining) / bucket.refill_rate)

            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            response.headers["X-RateLimit-Window"] = str(window)

    async def _cleanup_buckets(self):
        """Clean up old unused token buckets."""
        now = time.time()

        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Remove buckets that haven't been used in a while
        cutoff_time = now - (self.cleanup_interval * 2)
        to_remove = []

        for bucket_key, bucket in self.buckets.items():
            if bucket.last_refill < cutoff_time:
                to_remove.append(bucket_key)

        for bucket_key in to_remove:
            del self.buckets[bucket_key]

        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old rate limit buckets")

        self.last_cleanup = now