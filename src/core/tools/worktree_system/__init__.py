"""
Worktree System for DevMind - Git worktree support and isolation.

Provides isolated workspace management with git worktree integration
and VCS-agnostic hooks support.
"""

from .worktree_manager import (
    WorktreeManager, WorktreeInfo,
    get_worktree_manager
)
from .enter_worktree_tool import enter_worktree_tool, EnterWorktreeTool

__all__ = [
    # Worktree Management
    "WorktreeManager",
    "WorktreeInfo",
    "get_worktree_manager",

    # Worktree Tool
    "enter_worktree_tool",
    "EnterWorktreeTool",

    # Registration function
    "register_worktree_tools"
]


def register_worktree_tools():
    """Register worktree system tools with the ACP registry."""
    from ..acp_integration import register_acp_tool

    register_acp_tool(enter_worktree_tool)