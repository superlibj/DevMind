"""
Pydantic models for health check API endpoints.

This module provides request/response models for health monitoring,
readiness checks, and system status endpoints.
"""
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

from .common import BaseResponse, SystemMetrics


class HealthStatus(BaseResponse):
    """Basic health status response model."""
    status: str = Field(..., pattern="^(healthy|unhealthy|degraded)$",
                       description="Service health status")
    uptime_seconds: float = Field(..., ge=0, description="Service uptime in seconds")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Deployment environment")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "status": "healthy",
                "timestamp": "2023-01-01T00:00:00Z",
                "uptime_seconds": 3600.5,
                "version": "1.0.0",
                "environment": "production"
            }
        }


class ComponentStatus(BaseModel):
    """Individual component health status model."""
    status: str = Field(..., pattern="^(healthy|unhealthy|degraded|unknown)$",
                       description="Component status")
    response_time_ms: Optional[float] = Field(None, ge=0,
                                             description="Component response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if component is unhealthy")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional component details")
    last_checked: str = Field(..., description="Timestamp of last health check")


class SystemInfo(BaseModel):
    """System information model."""
    cpu: Dict[str, Any] = Field(..., description="CPU information")
    memory: Dict[str, Any] = Field(..., description="Memory information")
    disk: Dict[str, Any] = Field(..., description="Disk information")
    network: Optional[Dict[str, Any]] = Field(None, description="Network information")
    python_version: str = Field(..., description="Python version")
    platform: str = Field(..., description="Operating system platform")


class DependencyStatus(BaseModel):
    """Dependency status model."""
    llm_provider: ComponentStatus = Field(..., description="LLM provider health")
    security_scanners: ComponentStatus = Field(..., description="Security scanners health")
    tool_integration: ComponentStatus = Field(..., description="Tool integration health")
    database: Optional[ComponentStatus] = Field(None, description="Database health")
    cache: Optional[ComponentStatus] = Field(None, description="Cache service health")
    external_apis: Optional[Dict[str, ComponentStatus]] = Field(None,
                                                               description="External API health status")


class DetailedHealthStatus(BaseResponse):
    """Detailed health status response model."""
    status: str = Field(..., pattern="^(healthy|unhealthy|degraded)$",
                       description="Overall service health status")
    uptime_seconds: float = Field(..., ge=0, description="Service uptime in seconds")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Deployment environment")
    system: SystemInfo = Field(..., description="System information")
    dependencies: DependencyStatus = Field(..., description="Dependency health status")
    metrics: SystemMetrics = Field(..., description="Performance metrics")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "status": "healthy",
                "timestamp": "2023-01-01T00:00:00Z",
                "uptime_seconds": 3600.5,
                "version": "1.0.0",
                "environment": "production",
                "system": {
                    "cpu": {"usage_percent": 25.5, "count": 8},
                    "memory": {"total_gb": 16.0, "available_gb": 12.0, "used_percent": 25.0},
                    "disk": {"total_gb": 100.0, "free_gb": 75.0, "used_percent": 25.0},
                    "python_version": "3.11.0",
                    "platform": "linux"
                },
                "dependencies": {
                    "llm_provider": {
                        "status": "healthy",
                        "response_time_ms": 150.2,
                        "last_checked": "2023-01-01T00:00:00Z"
                    },
                    "security_scanners": {
                        "status": "healthy",
                        "last_checked": "2023-01-01T00:00:00Z"
                    },
                    "tool_integration": {
                        "status": "healthy",
                        "last_checked": "2023-01-01T00:00:00Z"
                    }
                }
            }
        }


class ReadinessCheck(BaseModel):
    """Individual readiness check model."""
    name: str = Field(..., description="Check name")
    status: str = Field(..., pattern="^(ready|not_ready|error)$", description="Check status")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional check details")
    error: Optional[str] = Field(None, description="Error message if check failed")
    duration_ms: float = Field(..., ge=0, description="Check duration in milliseconds")


class ReadinessStatus(BaseResponse):
    """Service readiness response model."""
    ready: bool = Field(..., description="Whether the service is ready to accept traffic")
    checks: List[ReadinessCheck] = Field(..., description="Individual readiness checks")
    total_checks: int = Field(..., description="Total number of readiness checks")
    passed_checks: int = Field(..., description="Number of passed checks")
    failed_checks: int = Field(..., description="Number of failed checks")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "ready": True,
                "timestamp": "2023-01-01T00:00:00Z",
                "checks": [
                    {
                        "name": "llm_provider",
                        "status": "ready",
                        "duration_ms": 150.2
                    },
                    {
                        "name": "security_scanners",
                        "status": "ready",
                        "duration_ms": 50.1
                    }
                ],
                "total_checks": 2,
                "passed_checks": 2,
                "failed_checks": 0
            }
        }


class LivenessStatus(BaseResponse):
    """Service liveness response model."""
    alive: bool = Field(..., description="Whether the service is alive")
    process_id: int = Field(..., description="Process ID")
    memory_usage_mb: float = Field(..., description="Current memory usage in MB")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "alive": True,
                "timestamp": "2023-01-01T00:00:00Z",
                "process_id": 12345,
                "memory_usage_mb": 512.5
            }
        }


class PerformanceMetrics(BaseModel):
    """Performance metrics model."""
    request_metrics: Dict[str, Any] = Field(..., description="Request performance metrics")
    agent_metrics: Dict[str, Any] = Field(..., description="AI agent performance metrics")
    system_metrics: SystemMetrics = Field(..., description="System performance metrics")
    error_rates: Dict[str, float] = Field(..., description="Error rates by endpoint")
    response_times: Dict[str, Dict[str, float]] = Field(...,
                                                       description="Response time percentiles by endpoint")


class MetricsResponse(BaseResponse):
    """Metrics response model."""
    metrics: PerformanceMetrics = Field(..., description="Collected performance metrics")
    collection_period: str = Field(..., description="Metrics collection period")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "timestamp": "2023-01-01T00:00:00Z",
                "metrics": {
                    "request_metrics": {
                        "total_requests": 1000,
                        "successful_requests": 950,
                        "failed_requests": 50,
                        "average_response_time_ms": 250.5
                    },
                    "agent_metrics": {
                        "code_generations": 100,
                        "code_reviews": 50,
                        "chat_messages": 300,
                        "average_processing_time_ms": 1500.2
                    },
                    "system_metrics": {
                        "cpu_usage": 25.5,
                        "memory_usage": 30.0,
                        "disk_usage": 45.0
                    }
                },
                "collection_period": "last_hour"
            }
        }


class ServiceInfo(BaseModel):
    """Service information model."""
    name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    description: str = Field(..., description="Service description")
    api_version: str = Field(..., description="API version")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")
    support_email: Optional[str] = Field(None, description="Support contact email")
    build_info: Dict[str, Any] = Field(..., description="Build information")


class ServiceInfoResponse(BaseResponse):
    """Service information response model."""
    service: ServiceInfo = Field(..., description="Service information")
    features: List[str] = Field(..., description="Available features")
    endpoints: Dict[str, List[str]] = Field(..., description="Available endpoints by category")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "timestamp": "2023-01-01T00:00:00Z",
                "service": {
                    "name": "AI Code Development Agent",
                    "version": "1.0.0",
                    "description": "AI-powered development assistant",
                    "api_version": "v1",
                    "build_info": {
                        "commit": "abc123def",
                        "build_date": "2023-01-01T00:00:00Z",
                        "environment": "production"
                    }
                },
                "features": [
                    "code_generation",
                    "code_review",
                    "refactoring",
                    "debugging",
                    "chat_interface"
                ],
                "endpoints": {
                    "agent": ["/api/v1/chat", "/api/v1/generate", "/api/v1/review"],
                    "auth": ["/auth/login", "/auth/register", "/auth/profile"],
                    "health": ["/health", "/health/ready", "/health/live"]
                }
            }
        }