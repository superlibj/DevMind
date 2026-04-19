"""
Permission System for DevMind.

Provides interactive permission management, user confirmation dialogs,
and safety controls for tool execution.
"""

from .ask_user_question_tool import AskUserQuestionTool, ask_user_question_tool
from .permission_manager import PermissionManager, PermissionLevel, PermissionDecision

__all__ = [
    # Permission tools
    "AskUserQuestionTool",
    "ask_user_question_tool",

    # Permission management
    "PermissionManager",
    "PermissionLevel",
    "PermissionDecision",

    # Registration function
    "register_permission_tools",
]


def register_permission_tools():
    """Register all permission system tools with the ACP registry."""
    from ..acp_integration import register_acp_tool

    # Register permission tools
    register_acp_tool(ask_user_question_tool)