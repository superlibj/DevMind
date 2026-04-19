"""
FastAPI-based web interface for the AI Code Development Agent.

This package provides a RESTful API and WebSocket interface for interacting
with the AI agent, including authentication, rate limiting, and comprehensive
request/response validation.

Key Components:
- main.py: FastAPI application setup and configuration
- routes/: API route handlers organized by functionality
- middleware/: Authentication, logging, and rate limiting middleware
- schemas/: Pydantic models for request/response validation
"""

from .main import app

__all__ = ["app"]