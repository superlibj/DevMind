"""
Memory and Session Management System for DevMind.

Provides persistent memory across conversations, auto-memory functionality,
topic-based organization, and comprehensive session management.
"""

from .memory_manager import MemoryManager, MemoryEntry, MemoryTopic
from .session_manager import EnhancedSessionManager, SessionData
from .auto_memory_tool import AutoMemoryTool, auto_memory_tool

__all__ = [
    # Core memory management
    "MemoryManager",
    "MemoryEntry",
    "MemoryTopic",

    # Session management
    "EnhancedSessionManager",
    "SessionData",

    # Memory tools
    "AutoMemoryTool",
    "auto_memory_tool",

    # Registration function
    "register_memory_tools",
]


def register_memory_tools():
    """Register all memory management tools with the ACP registry."""
    from ..acp_integration import register_acp_tool

    # Register memory tools
    register_acp_tool(auto_memory_tool)