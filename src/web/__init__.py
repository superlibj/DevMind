"""
Web interface components for the AI Code Development Agent.

This package provides WebSocket handlers and other web interface
components for real-time interaction with the AI agent.
"""

from .websocket import chat_handler, connection_manager

__all__ = [
    "chat_handler",
    "connection_manager"
]