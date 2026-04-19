"""
Common Pydantic models used across multiple API endpoints.

This module provides base models and common response types that are
reused throughout the API for consistency and maintainability.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model with common fields."""
    success: bool = Field(True, description="Whether the operation was successful")
    message: Optional[str] = Field(None, description="Optional message")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(),
                          description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Request correlation ID")


class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response model."""
    error: str = Field("validation_error", description="Error type")
    validation_errors: List[Dict[str, Union[str, List[str]]]] = Field(
        ..., description="List of validation errors"
    )


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(20, ge=1, le=100, description="Number of items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseResponse):
    """Paginated response model."""
    data: List[Any] = Field(..., description="List of items")
    pagination: Dict[str, Any] = Field(..., description="Pagination metadata")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "timestamp": "2023-01-01T00:00:00Z",
                "data": [],
                "pagination": {
                    "page": 1,
                    "limit": 20,
                    "total_pages": 5,
                    "total_items": 100,
                    "has_next": True,
                    "has_prev": False
                }
            }
        }


class FileInfo(BaseModel):
    """File information model."""
    name: str = Field(..., description="File name")
    path: str = Field(..., description="File path")
    size: int = Field(..., description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    modified_at: Optional[str] = Field(None, description="Last modification timestamp")


class SecurityScanResult(BaseModel):
    """Security scan result model."""
    scan_id: str = Field(..., description="Unique scan identifier")
    status: str = Field(..., description="Scan status: pending, running, completed, failed")
    vulnerabilities: List[Dict[str, Any]] = Field(default_factory=list,
                                                  description="List of vulnerabilities found")
    total_vulnerabilities: int = Field(0, description="Total number of vulnerabilities")
    critical_count: int = Field(0, description="Number of critical vulnerabilities")
    high_count: int = Field(0, description="Number of high severity vulnerabilities")
    medium_count: int = Field(0, description="Number of medium severity vulnerabilities")
    low_count: int = Field(0, description="Number of low severity vulnerabilities")
    scan_duration: Optional[float] = Field(None, description="Scan duration in seconds")
    scanned_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(),
                           description="Scan timestamp")


class ToolExecutionResult(BaseModel):
    """Tool execution result model."""
    tool_name: str = Field(..., description="Name of the executed tool")
    operation: str = Field(..., description="Operation that was performed")
    status: str = Field(..., description="Execution status: success, error, timeout")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    duration: float = Field(..., description="Execution duration in seconds")
    executed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(),
                            description="Execution timestamp")


class AgentOperation(BaseModel):
    """Agent operation tracking model."""
    operation_id: str = Field(..., description="Unique operation identifier")
    operation_type: str = Field(..., description="Type of operation")
    status: str = Field(..., description="Operation status")
    user_id: str = Field(..., description="User who initiated the operation")
    started_at: str = Field(..., description="Operation start timestamp")
    completed_at: Optional[str] = Field(None, description="Operation completion timestamp")
    duration: Optional[float] = Field(None, description="Operation duration in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional operation metadata")


class CodeMetrics(BaseModel):
    """Code quality metrics model."""
    lines_of_code: int = Field(..., description="Total lines of code")
    complexity: Optional[float] = Field(None, description="Code complexity score")
    maintainability: Optional[float] = Field(None, description="Maintainability score")
    test_coverage: Optional[float] = Field(None, description="Test coverage percentage")
    duplication: Optional[float] = Field(None, description="Code duplication percentage")
    technical_debt: Optional[str] = Field(None, description="Technical debt assessment")


class SystemMetrics(BaseModel):
    """System performance metrics model."""
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    request_count: int = Field(..., description="Total request count")
    average_response_time: float = Field(..., description="Average response time in milliseconds")
    error_rate: float = Field(..., description="Error rate percentage")
    uptime: float = Field(..., description="Uptime in seconds")
    collected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(),
                             description="Metrics collection timestamp")


class WebSocketMessage(BaseModel):
    """WebSocket message model."""
    type: str = Field(..., description="Message type")
    message: Optional[str] = Field(None, description="Message content")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional message data")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(),
                          description="Message timestamp")
    session_id: Optional[str] = Field(None, description="Session identifier")


class TaskStatus(BaseModel):
    """Background task status model."""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status: pending, running, completed, failed")
    progress: Optional[float] = Field(None, ge=0, le=100, description="Task progress percentage")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result data")
    error: Optional[str] = Field(None, description="Error message if task failed")
    created_at: str = Field(..., description="Task creation timestamp")
    started_at: Optional[str] = Field(None, description="Task start timestamp")
    completed_at: Optional[str] = Field(None, description="Task completion timestamp")
    duration: Optional[float] = Field(None, description="Task duration in seconds")