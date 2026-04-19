"""
Request logging and correlation middleware for the FastAPI application.

This middleware provides comprehensive request/response logging with
correlation IDs for better observability and debugging.
"""
import logging
import time
import uuid
from typing import Callable, Optional, Dict, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware with correlation tracking."""

    def __init__(self, app: ASGIApp, logger_name: Optional[str] = None):
        """Initialize logging middleware.

        Args:
            app: FastAPI application instance
            logger_name: Optional logger name override
        """
        super().__init__(app)
        self.logger = logging.getLogger(logger_name or __name__)

        # Paths to exclude from logging (for noise reduction)
        self.exclude_paths = {
            "/health",
            "/health/",
            "/health/status",
            "/health/ready",
            "/metrics"
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging and correlation tracking.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response with correlation headers
        """
        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())
        request.state.request_id = correlation_id
        request.state.start_time = time.time()

        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            response = await call_next(request)
            response.headers["X-Request-ID"] = correlation_id
            return response

        # Extract request information
        request_info = self._extract_request_info(request, correlation_id)

        # Log incoming request
        self.logger.info(
            f"Request started: {request_info['method']} {request_info['path']}",
            extra={
                "event": "request_start",
                "correlation_id": correlation_id,
                **request_info
            }
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            processing_time = time.time() - request.state.start_time

            # Extract response information
            response_info = self._extract_response_info(response, processing_time)

            # Log response
            log_level = self._get_log_level(response.status_code)
            self.logger.log(
                log_level,
                f"Request completed: {response.status_code} in {processing_time:.3f}s",
                extra={
                    "event": "request_complete",
                    "correlation_id": correlation_id,
                    **request_info,
                    **response_info
                }
            )

            # Add correlation headers
            response.headers["X-Request-ID"] = correlation_id
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}"

            return response

        except Exception as e:
            # Calculate processing time for errors
            processing_time = time.time() - request.state.start_time

            # Log error
            self.logger.error(
                f"Request failed: {str(e)} in {processing_time:.3f}s",
                extra={
                    "event": "request_error",
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time": processing_time,
                    **request_info
                },
                exc_info=True
            )

            # Re-raise to let other handlers process
            raise

    def _extract_request_info(self, request: Request, correlation_id: str) -> Dict[str, Any]:
        """Extract relevant information from request for logging.

        Args:
            request: HTTP request
            correlation_id: Request correlation ID

        Returns:
            Dictionary of request information
        """
        # Get user information if available
        user_id = getattr(request.state, "user_id", None)
        authenticated = getattr(request.state, "authenticated", False)

        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        return {
            "method": request.method,
            "path": request.url.path,
            "query_string": str(request.url.query) if request.url.query else None,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "user_id": user_id,
            "authenticated": authenticated,
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
            "referer": request.headers.get("referer"),
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }

    def _extract_response_info(self, response: Response, processing_time: float) -> Dict[str, Any]:
        """Extract relevant information from response for logging.

        Args:
            response: HTTP response
            processing_time: Request processing time in seconds

        Returns:
            Dictionary of response information
        """
        return {
            "status_code": response.status_code,
            "response_content_type": response.headers.get("content-type"),
            "response_content_length": response.headers.get("content-length"),
            "processing_time": processing_time,
            "cache_control": response.headers.get("cache-control"),
        }

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request.

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Use client host
        return request.client.host if request.client else "unknown"

    def _get_log_level(self, status_code: int) -> int:
        """Get appropriate log level based on status code.

        Args:
            status_code: HTTP status code

        Returns:
            Logging level
        """
        if status_code >= 500:
            return logging.ERROR
        elif status_code >= 400:
            return logging.WARNING
        elif status_code >= 300:
            return logging.INFO
        else:
            return logging.INFO


class StructuredLogger:
    """Structured logger for consistent application logging."""

    def __init__(self, name: str):
        """Initialize structured logger.

        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)

    def log_agent_operation(
        self,
        operation: str,
        user_id: str,
        operation_id: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Log agent operation with structured data.

        Args:
            operation: Operation name (e.g., 'code_generation', 'code_review')
            user_id: User identifier
            operation_id: Unique operation identifier
            status: Operation status (started, completed, failed)
            details: Additional operation details
            error: Error message if operation failed
        """
        log_data = {
            "event": "agent_operation",
            "operation": operation,
            "user_id": user_id,
            "operation_id": operation_id,
            "status": status,
            "timestamp": time.time()
        }

        if details:
            log_data.update(details)

        if error:
            log_data["error"] = error
            self.logger.error(f"Agent operation failed: {operation}", extra=log_data)
        elif status == "completed":
            self.logger.info(f"Agent operation completed: {operation}", extra=log_data)
        else:
            self.logger.info(f"Agent operation {status}: {operation}", extra=log_data)

    def log_security_scan(
        self,
        scan_type: str,
        file_path: str,
        scan_id: str,
        vulnerabilities_found: int,
        scan_duration: float,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log security scan results.

        Args:
            scan_type: Type of security scan
            file_path: Scanned file path
            scan_id: Unique scan identifier
            vulnerabilities_found: Number of vulnerabilities found
            scan_duration: Scan duration in seconds
            details: Additional scan details
        """
        log_data = {
            "event": "security_scan",
            "scan_type": scan_type,
            "file_path": file_path,
            "scan_id": scan_id,
            "vulnerabilities_found": vulnerabilities_found,
            "scan_duration": scan_duration,
            "timestamp": time.time()
        }

        if details:
            log_data.update(details)

        if vulnerabilities_found > 0:
            self.logger.warning(
                f"Security scan found {vulnerabilities_found} vulnerabilities in {file_path}",
                extra=log_data
            )
        else:
            self.logger.info(f"Security scan clean: {file_path}", extra=log_data)

    def log_tool_execution(
        self,
        tool_name: str,
        operation: str,
        execution_id: str,
        status: str,
        duration: float,
        user_id: str,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Log tool execution with structured data.

        Args:
            tool_name: Name of executed tool
            operation: Operation performed
            execution_id: Unique execution identifier
            status: Execution status
            duration: Execution duration in seconds
            user_id: User identifier
            details: Additional execution details
            error: Error message if execution failed
        """
        log_data = {
            "event": "tool_execution",
            "tool_name": tool_name,
            "operation": operation,
            "execution_id": execution_id,
            "status": status,
            "duration": duration,
            "user_id": user_id,
            "timestamp": time.time()
        }

        if details:
            log_data.update(details)

        if error:
            log_data["error"] = error
            self.logger.error(f"Tool execution failed: {tool_name}.{operation}", extra=log_data)
        else:
            self.logger.info(f"Tool executed: {tool_name}.{operation}", extra=log_data)


# Global structured logger instances
agent_logger = StructuredLogger("aiagent.agent")
security_logger = StructuredLogger("aiagent.security")
tools_logger = StructuredLogger("aiagent.tools")