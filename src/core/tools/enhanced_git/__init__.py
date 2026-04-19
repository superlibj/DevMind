"""
Enhanced Git Integration with Safety Features for DevMind.

Provides intelligent git workflows with safety checks, commit message generation,
PR creation, and comprehensive development workflow automation.
"""

from .smart_commit_tool import SmartCommitTool, smart_commit_tool
from .pr_create_tool import PRCreateTool, pr_create_tool
from .git_safety_checker import GitSafetyChecker

__all__ = [
    # Smart git tools
    "SmartCommitTool",
    "smart_commit_tool",
    "PRCreateTool",
    "pr_create_tool",

    # Safety system
    "GitSafetyChecker",

    # Registration function
    "register_enhanced_git_tools",
]


def register_enhanced_git_tools():
    """Register all enhanced git tools with the ACP registry."""
    from ..acp_integration import register_acp_tool

    # Register enhanced git tools
    register_acp_tool(smart_commit_tool)
    register_acp_tool(pr_create_tool)