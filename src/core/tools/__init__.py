"""
Tool integration system for AI Code Development Agent.

This module provides ACP-compliant tools for development operations including
git operations, file management, and vim integration.
"""

from .acp_integration import (
    ACPMessage,
    ACPMessageType,
    ACPStatus,
    ACPToolResult,
    ACPToolSpec,
    ACPTool,
    ACPRegistry,
    ACPClient,
    acp_registry,
    acp_client,
    register_acp_tool,
    create_acp_message
)

from .git_tool import git_tool, GitTool
from .file_tool import file_tool, FileTool
from .vim_tool import vim_tool, VimTool
from .agent_integration import (
    acp_tool_manager,
    initialize_acp_integration,
    get_acp_tool_info,
    list_acp_tools,
    execute_acp_tool
)

__all__ = [
    # ACP Framework
    "ACPMessage",
    "ACPMessageType",
    "ACPStatus",
    "ACPToolResult",
    "ACPToolSpec",
    "ACPTool",
    "ACPRegistry",
    "ACPClient",
    "acp_registry",
    "acp_client",
    "register_acp_tool",
    "create_acp_message",

    # Tools
    "git_tool",
    "GitTool",
    "file_tool",
    "FileTool",
    "vim_tool",
    "VimTool",

    # Agent Integration
    "acp_tool_manager",
    "initialize_acp_integration",
    "get_acp_tool_info",
    "list_acp_tools",
    "execute_acp_tool",

    # Registration functions
    "register_all_tools",
    "get_available_tools",
]


def register_all_tools():
    """Register all available tools with the ACP registry."""
    # Register core tools
    register_acp_tool(git_tool)
    register_acp_tool(file_tool)
    register_acp_tool(vim_tool)


def get_available_tools():
    """Get list of all available tools.

    Returns:
        List of tool specifications
    """
    return acp_registry.list_tools()


# Auto-register tools on module import
register_all_tools()