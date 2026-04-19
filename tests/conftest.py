"""
Pytest configuration and fixtures for AI Code Development Agent tests.

This module provides shared fixtures and configuration for all test modules
including database setup, API client setup, and mock data generation.
"""
import asyncio
import os
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

import httpx
from fastapi.testclient import TestClient

# Test environment setup
os.environ["APP__ENVIRONMENT"] = "test"
os.environ["APP__DEBUG"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SECURITY__JWT_SECRET_KEY"] = "test-secret-key"

from src.api.main import app
from src.api.middleware.auth import auth_manager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_user():
    """Mock user data for testing."""
    return {
        "sub": "test_user_123",
        "username": "testuser",
        "email": "test@example.com",
        "permissions": ["basic"],
        "iat": 1640995200,  # 2022-01-01
        "exp": 1640995200 + 3600  # 1 hour later
    }


@pytest.fixture
def admin_user():
    """Mock admin user data for testing."""
    return {
        "sub": "admin_user_123",
        "username": "admin",
        "email": "admin@example.com",
        "permissions": ["admin", "premium", "basic"],
        "iat": 1640995200,
        "exp": 1640995200 + 3600
    }


@pytest.fixture
def auth_token(mock_user):
    """Generate a valid JWT token for testing."""
    return auth_manager.create_access_token(mock_user)


@pytest.fixture
def admin_token(admin_user):
    """Generate a valid admin JWT token for testing."""
    return auth_manager.create_access_token(admin_user)


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers for API requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """Create admin authorization headers for API requests."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    mock = AsyncMock()
    mock.name = "test_provider"
    mock.default_model = "test_model"
    mock.chat.return_value = {
        "content": "Test response from AI agent",
        "role": "assistant",
        "usage": {"total_tokens": 100}
    }
    mock.complete.return_value = {
        "content": "Test completion",
        "usage": {"total_tokens": 50}
    }
    return mock


@pytest.fixture
def mock_code_scanner():
    """Mock code scanner for testing."""
    mock = Mock()
    mock.scan_code.return_value = {
        "scan_id": "test_scan_123",
        "status": "completed",
        "vulnerabilities": [],
        "total_vulnerabilities": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "scan_duration": 0.5
    }
    return mock


@pytest.fixture
def mock_acp_tool():
    """Mock ACP tool for testing."""
    mock = AsyncMock()
    mock.name = "test_tool"
    mock.call_tool.return_value = Mock(
        status=Mock(value="completed"),
        result={"output": "Test tool output", "success": True},
        error=None
    )
    return mock


@pytest.fixture
def sample_code():
    """Sample code for testing."""
    return '''
def hello_world(name: str = "World") -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"

def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

if __name__ == "__main__":
    print(hello_world())
    print(add_numbers(5, 3))
'''


@pytest.fixture
def vulnerable_code():
    """Sample vulnerable code for testing security scanning."""
    return '''
import subprocess
import os

def unsafe_function(user_input):
    # SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE name = '{user_input}'"

    # Command injection vulnerability
    subprocess.call(f"echo {user_input}", shell=True)

    # Hardcoded secret
    api_key = "sk-1234567890abcdef"

    return query
'''


@pytest.fixture
def chat_session_data():
    """Sample chat session data for testing."""
    return {
        "session_id": "test_session_123",
        "user_id": "test_user_123",
        "messages": [
            {
                "role": "user",
                "content": "Hello, can you help me write a Python function?",
                "timestamp": "2023-01-01T00:00:00Z"
            },
            {
                "role": "assistant",
                "content": "Of course! I'd be happy to help you write a Python function.",
                "timestamp": "2023-01-01T00:00:01Z"
            }
        ]
    }


@pytest.fixture
async def mock_database():
    """Mock database connection for testing."""
    # In a real implementation, this would set up a test database
    # For now, we'll use a simple mock
    db_mock = AsyncMock()
    db_mock.execute.return_value = None
    db_mock.fetch_all.return_value = []
    db_mock.fetch_one.return_value = None
    yield db_mock


@pytest.fixture
async def mock_redis():
    """Mock Redis connection for testing."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = False
    yield redis_mock


# Test markers
pytest_plugins = ["pytest_asyncio"]

# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "security: mark test as a security test")
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_api_key: mark test as requiring API keys")
    config.addinivalue_line("markers", "requires_docker: mark test as requiring Docker")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)

        # Add slow marker for tests that take longer than 10 seconds
        if hasattr(item, "get_closest_marker"):
            slow_marker = item.get_closest_marker("slow")
            if slow_marker:
                item.add_marker(pytest.mark.timeout(60))


# Mock environment variables for testing
@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables automatically for all tests."""
    monkeypatch.setenv("APP__ENVIRONMENT", "test")
    monkeypatch.setenv("APP__DEBUG", "true")
    monkeypatch.setenv("SECURITY__JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")


# Cleanup fixtures
@pytest.fixture(autouse=True)
async def cleanup():
    """Clean up after each test."""
    yield
    # Perform any necessary cleanup here
    pass