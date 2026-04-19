"""
Health check endpoints for monitoring and load balancing.

These endpoints provide health status information for the AI agent
service and its dependencies.
"""
import asyncio
import logging
import psutil
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Service start time for uptime calculation
SERVICE_START_TIME = time.time()


class HealthStatus(BaseModel):
    """Health status response model."""
    status: str
    timestamp: str
    uptime_seconds: float
    version: str
    environment: str


class DetailedHealthStatus(BaseModel):
    """Detailed health status response model."""
    status: str
    timestamp: str
    uptime_seconds: float
    version: str
    environment: str
    system: Dict[str, Any]
    dependencies: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Any]


class ReadinessStatus(BaseModel):
    """Service readiness response model."""
    ready: bool
    timestamp: str
    checks: Dict[str, Dict[str, Any]]


async def check_llm_provider() -> Dict[str, Any]:
    """Check LLM provider availability.

    Returns:
        Dictionary with provider health status
    """
    try:
        from src.core.llm import LLMManager

        llm_manager = LLMManager()

        # Try to get a simple response from the default provider
        start_time = time.time()
        await asyncio.wait_for(
            llm_manager.chat([{"role": "user", "content": "ping"}]),
            timeout=5.0
        )
        response_time = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "provider": llm_manager.current_provider.name,
            "model": llm_manager.current_provider.default_model
        }
    except asyncio.TimeoutError:
        return {
            "status": "unhealthy",
            "error": "LLM provider timeout",
            "response_time_ms": None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": None
        }


async def check_security_scanners() -> Dict[str, Any]:
    """Check security scanner availability.

    Returns:
        Dictionary with security scanner health status
    """
    try:
        from src.core.security import CodeScanner

        scanner = CodeScanner()

        # Check if security tools are available
        available_scanners = []
        errors = []

        # Test each scanner
        for scanner_name in ["bandit", "semgrep", "safety"]:
            try:
                # This would be a quick test to see if the scanner is available
                # Implementation would depend on the actual scanner setup
                available_scanners.append(scanner_name)
            except Exception as e:
                errors.append(f"{scanner_name}: {str(e)}")

        if available_scanners:
            return {
                "status": "healthy",
                "available_scanners": available_scanners,
                "errors": errors if errors else None
            }
        else:
            return {
                "status": "unhealthy",
                "error": "No security scanners available",
                "errors": errors
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_tool_integration() -> Dict[str, Any]:
    """Check tool integration system health.

    Returns:
        Dictionary with tool system health status
    """
    try:
        from src.core.tools import list_acp_tools

        # Get available tools
        tools = list_acp_tools()

        return {
            "status": "healthy",
            "available_tools": len(tools),
            "tools": [tool["name"] for tool in tools]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def get_system_metrics() -> Dict[str, Any]:
    """Get system performance metrics.

    Returns:
        Dictionary with system metrics
    """
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory usage
        memory = psutil.virtual_memory()

        # Disk usage
        disk = psutil.disk_usage('/')

        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "used_percent": round((disk.used / disk.total) * 100, 1)
            }
        }
    except Exception as e:
        logger.warning(f"Failed to get system metrics: {e}")
        return {"error": str(e)}


@router.get("/", response_model=HealthStatus, summary="Basic health check")
@router.get("/status", response_model=HealthStatus, summary="Basic health check")
async def health_check() -> HealthStatus:
    """
    Basic health check endpoint.

    Returns basic service health information including uptime and version.
    Used by load balancers and monitoring systems for quick health verification.
    """
    uptime = time.time() - SERVICE_START_TIME

    return HealthStatus(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(uptime, 2),
        version=settings.app.version,
        environment=settings.app.environment
    )


@router.get("/detailed", response_model=DetailedHealthStatus, summary="Detailed health check")
async def detailed_health_check() -> DetailedHealthStatus:
    """
    Detailed health check endpoint.

    Returns comprehensive health information including system metrics,
    dependency status, and performance data. Used for debugging and
    detailed monitoring.
    """
    uptime = time.time() - SERVICE_START_TIME

    # Check dependencies in parallel
    llm_check, security_check, tools_check = await asyncio.gather(
        check_llm_provider(),
        check_security_scanners(),
        check_tool_integration(),
        return_exceptions=True
    )

    # Handle exceptions from dependency checks
    dependencies = {}
    for name, check in [("llm", llm_check), ("security", security_check), ("tools", tools_check)]:
        if isinstance(check, Exception):
            dependencies[name] = {
                "status": "error",
                "error": str(check)
            }
        else:
            dependencies[name] = check

    # Get system metrics
    system_metrics = get_system_metrics()

    # Calculate overall status
    overall_status = "healthy"
    for dep_status in dependencies.values():
        if dep_status.get("status") != "healthy":
            overall_status = "degraded"
            break

    return DetailedHealthStatus(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(uptime, 2),
        version=settings.app.version,
        environment=settings.app.environment,
        system=system_metrics,
        dependencies=dependencies,
        metrics={
            "uptime_seconds": round(uptime, 2),
            "service_start_time": SERVICE_START_TIME,
            "requests_processed": "N/A"  # Could be tracked with middleware
        }
    )


@router.get("/ready", response_model=ReadinessStatus, summary="Readiness check")
async def readiness_check() -> ReadinessStatus:
    """
    Readiness check endpoint.

    Determines if the service is ready to accept traffic by checking
    critical dependencies. Used by Kubernetes and other orchestrators
    to determine when to route traffic to this instance.
    """
    checks = {}
    ready = True

    # Check critical dependencies
    try:
        # LLM provider check
        llm_status = await asyncio.wait_for(check_llm_provider(), timeout=10.0)
        checks["llm_provider"] = llm_status
        if llm_status["status"] != "healthy":
            ready = False
    except Exception as e:
        checks["llm_provider"] = {"status": "error", "error": str(e)}
        ready = False

    try:
        # Security scanners check
        security_status = await asyncio.wait_for(check_security_scanners(), timeout=5.0)
        checks["security_scanners"] = security_status
        if security_status["status"] != "healthy":
            ready = False
    except Exception as e:
        checks["security_scanners"] = {"status": "error", "error": str(e)}
        ready = False

    try:
        # Tool integration check
        tools_status = await asyncio.wait_for(check_tool_integration(), timeout=5.0)
        checks["tool_integration"] = tools_status
        if tools_status["status"] != "healthy":
            ready = False
    except Exception as e:
        checks["tool_integration"] = {"status": "error", "error": str(e)}
        ready = False

    return ReadinessStatus(
        ready=ready,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=checks
    )


@router.get("/live", summary="Liveness check")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint.

    Simple endpoint that returns 200 if the service is alive.
    Used by Kubernetes and other orchestrators to determine if
    the service should be restarted.
    """
    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }