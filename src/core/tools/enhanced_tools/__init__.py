"""
Enhanced development tools for DevMind.

This module provides advanced development tools with rich functionality
for file operations, code analysis, and development workflow automation.
"""

from .read_tool import ReadTool, read_tool
from .write_tool import WriteTool, write_tool
from .edit_tool import EditTool, edit_tool
from .bash_tool import BashTool, bash_tool
from .glob_tool import GlobTool, glob_tool
from .grep_tool import GrepTool, grep_tool
from .websearch_tool import WebSearchTool, websearch_tool
from .webfetch_tool import WebFetchTool, webfetch_tool
from .location_tool import LocationTool, location_tool
from .weather_tool import WeatherTool, weather_tool

__all__ = [
    # Read tool
    "ReadTool",
    "read_tool",

    # Write tool
    "WriteTool",
    "write_tool",

    # Edit tool
    "EditTool",
    "edit_tool",

    # Bash tool
    "BashTool",
    "bash_tool",

    # Glob tool
    "GlobTool",
    "glob_tool",

    # Grep tool
    "GrepTool",
    "grep_tool",

    # Web tools
    "WebSearchTool",
    "websearch_tool",
    "WebFetchTool",
    "webfetch_tool",

    # Location tool
    "LocationTool",
    "location_tool",

    # Weather tool
    "WeatherTool",
    "weather_tool",
]


def register_enhanced_tools():
    """Register all enhanced development tools with the ACP registry."""
    from ..acp_integration import register_acp_tool

    # Register all tools
    register_acp_tool(read_tool)
    register_acp_tool(write_tool)
    register_acp_tool(edit_tool)
    register_acp_tool(bash_tool)
    register_acp_tool(glob_tool)
    register_acp_tool(grep_tool)
    register_acp_tool(websearch_tool)
    register_acp_tool(webfetch_tool)
    register_acp_tool(location_tool)
    register_acp_tool(weather_tool)