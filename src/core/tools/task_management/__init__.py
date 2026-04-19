"""
Task Management System for DevMind.

Provides comprehensive task lifecycle management with planning mode support,
task dependencies, and progress tracking capabilities.
"""

from .task_store import TaskStore, Task, TaskStatus
from .task_create_tool import TaskCreateTool, task_create_tool
from .task_update_tool import TaskUpdateTool, task_update_tool
from .task_get_tool import TaskGetTool, task_get_tool
from .task_list_tool import TaskListTool, task_list_tool
from .plan_mode_tools import (
    EnterPlanModeTool, enter_plan_mode_tool,
    ExitPlanModeTool, exit_plan_mode_tool
)

__all__ = [
    # Core task management
    "TaskStore",
    "Task",
    "TaskStatus",

    # Task tools
    "TaskCreateTool",
    "task_create_tool",
    "TaskUpdateTool",
    "task_update_tool",
    "TaskGetTool",
    "task_get_tool",
    "TaskListTool",
    "task_list_tool",

    # Plan mode tools
    "EnterPlanModeTool",
    "enter_plan_mode_tool",
    "ExitPlanModeTool",
    "exit_plan_mode_tool",

    # Registration function
    "register_task_management_tools",
]


def register_task_management_tools():
    """Register all task management tools with the ACP registry."""
    from ..acp_integration import register_acp_tool

    # Register task management tools
    register_acp_tool(task_create_tool)
    register_acp_tool(task_update_tool)
    register_acp_tool(task_get_tool)
    register_acp_tool(task_list_tool)

    # Register plan mode tools
    register_acp_tool(enter_plan_mode_tool)
    register_acp_tool(exit_plan_mode_tool)