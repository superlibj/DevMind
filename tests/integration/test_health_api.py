"""
Integration tests for health check API endpoints.

Tests the health, readiness, and liveness endpoints to ensure
the application is properly responding to monitoring requests.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_basic_health_check(client: TestClient):
    """Test basic health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "status" in data
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert "version" in data
    assert "environment" in data

    # Check values
    assert data["status"] in ["healthy", "unhealthy", "degraded"]
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


@pytest.mark.integration
def test_health_status_endpoint(client: TestClient):
    """Test /health/status endpoint (alias for basic health)."""
    response = client.get("/health/status")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] in ["healthy", "unhealthy", "degraded"]


@pytest.mark.integration
@pytest.mark.slow
def test_detailed_health_check(client: TestClient):
    """Test detailed health check endpoint."""
    response = client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    required_fields = [
        "status", "timestamp", "uptime_seconds", "version",
        "environment", "system", "dependencies", "metrics"
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Check system info
    system = data["system"]
    assert "cpu" in system
    assert "memory" in system
    assert "disk" in system
    assert "python_version" in system
    assert "platform" in system

    # Check dependencies
    dependencies = data["dependencies"]
    expected_deps = ["llm_provider", "security_scanners", "tool_integration"]
    for dep in expected_deps:
        assert dep in dependencies
        assert "status" in dependencies[dep]
        assert "last_checked" in dependencies[dep]


@pytest.mark.integration
@pytest.mark.slow
def test_readiness_check(client: TestClient):
    """Test readiness check endpoint."""
    response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "ready" in data
    assert "checks" in data
    assert "timestamp" in data

    # Check boolean ready status
    assert isinstance(data["ready"], bool)

    # Check individual checks
    checks = data["checks"]
    assert isinstance(checks, list)

    for check in checks:
        assert "name" in check
        assert "status" in check
        assert "duration_ms" in check
        assert check["status"] in ["ready", "not_ready", "error"]
        assert isinstance(check["duration_ms"], (int, float))


@pytest.mark.integration
def test_liveness_check(client: TestClient):
    """Test liveness check endpoint."""
    response = client.get("/health/live")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "alive" in data
    assert "timestamp" in data
    assert "process_id" in data
    assert "memory_usage_mb" in data

    # Check values
    assert data["alive"] is True
    assert isinstance(data["process_id"], int)
    assert isinstance(data["memory_usage_mb"], (int, float))
    assert data["memory_usage_mb"] > 0


@pytest.mark.integration
def test_health_endpoints_response_format(client: TestClient):
    """Test that all health endpoints follow consistent response format."""
    endpoints = ["/health", "/health/status", "/health/live"]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200

        data = response.json()

        # All health endpoints should have timestamp
        assert "timestamp" in data

        # Timestamp should be in ISO format
        timestamp = data["timestamp"]
        assert "T" in timestamp  # Basic ISO format check
        assert timestamp.endswith("Z") or "+" in timestamp or "-" in timestamp[-6:]


@pytest.mark.integration
def test_health_check_under_load(client: TestClient):
    """Test health check performance under load."""
    import time
    import concurrent.futures

    def make_request():
        response = client.get("/health")
        return response.status_code, response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0

    # Make multiple concurrent requests
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(20)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    end_time = time.time()
    total_time = end_time - start_time

    # All requests should succeed
    for status_code, _ in results:
        assert status_code == 200

    # Total time should be reasonable (less than 5 seconds for 20 requests)
    assert total_time < 5.0, f"Health checks took too long: {total_time:.2f}s"


@pytest.mark.integration
def test_health_check_response_headers(client: TestClient):
    """Test that health check endpoints return appropriate headers."""
    response = client.get("/health")

    assert response.status_code == 200

    # Check content type
    assert response.headers.get("content-type", "").startswith("application/json")

    # Check for security headers (if middleware is configured)
    # These might not be present in test environment
    headers_to_check = [
        "x-request-id",
        "x-processing-time"
    ]

    # Don't assert these are present since they depend on middleware configuration
    # Just verify format if they exist
    if "x-processing-time" in response.headers:
        processing_time = response.headers["x-processing-time"]
        assert float(processing_time) >= 0


@pytest.mark.integration
@pytest.mark.slow
def test_health_check_consistency(client: TestClient):
    """Test that health check responses are consistent across multiple calls."""
    responses = []
    for _ in range(5):
        response = client.get("/health")
        assert response.status_code == 200
        responses.append(response.json())

    # Check that basic fields are consistent
    first_response = responses[0]
    for response in responses[1:]:
        assert response["status"] == first_response["status"]
        assert response["version"] == first_response["version"]
        assert response["environment"] == first_response["environment"]

        # Uptime should increase (or stay the same in fast tests)
        assert response["uptime_seconds"] >= first_response["uptime_seconds"]


@pytest.mark.integration
def test_health_check_error_conditions(client: TestClient):
    """Test health check behavior under error conditions."""
    # Test with invalid HTTP method
    response = client.post("/health")
    assert response.status_code == 405  # Method Not Allowed

    # Test with invalid path
    response = client.get("/health/invalid")
    assert response.status_code == 404  # Not Found