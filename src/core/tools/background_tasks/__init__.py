"""
Background Task Management System for DevMind.

Provides comprehensive background task execution, monitoring, and management
capabilities for long-running operations and parallel execution.
"""

from .task_manager import BackgroundTaskManager, TaskState, BackgroundTask
from .task_output_tool import TaskOutputTool, task_output_tool
from .task_stop_tool import TaskStopTool, task_stop_tool

__all__ = [
    # Core background task management
    "BackgroundTaskManager",
    "TaskState",
    "BackgroundTask",

    # Task management tools
    "TaskOutputTool",
    "task_output_tool",
    "TaskStopTool",
    "task_stop_tool",

    # Registration function
    "register_background_task_tools",
]


def register_background_task_tools():
    """Register all background task management tools with the ACP registry."""
    from ..acp_integration import register_acp_tool

    # Register background task tools
    register_acp_tool(task_output_tool)
    register_acp_tool(task_stop_tool)