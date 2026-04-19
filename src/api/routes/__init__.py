"""
API route modules for the AI Code Development Agent.

This package contains all the FastAPI route handlers organized by functionality:
- agent: Core AI agent functionality
- auth: Authentication and user management
- health: Health checks and monitoring
"""

from . import agent
from . import auth
from . import health

__all__ = [
    "agent",
    "auth",
    "health"
]