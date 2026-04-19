"""
Command Queue System for DevMind.

Provides command queuing functionality similar to Claude Code, allowing users
to queue multiple commands for sequential execution with priority support.
"""

from .queue_manager import (
    CommandQueueManager, QueuedCommand, CommandStatus, Priority,
    get_queue_manager
)
from .queue_tools import (
    queue_add_tool, QueueAddTool,
    queue_list_tool, QueueListTool,
    queue_remove_tool, QueueRemoveTool,
    queue_execute_tool, QueueExecuteTool,
    queue_status_tool, QueueStatusTool,
    queue_clear_tool, QueueClearTool
)
from .queue_executor import (
    QueueExecutor, ExecutionMode,
    get_queue_executor
)

__all__ = [
    # Queue Management
    "CommandQueueManager",
    "QueuedCommand",
    "CommandStatus",
    "Priority",
    "get_queue_manager",

    # Queue Tools
    "queue_add_tool",
    "QueueAddTool",
    "queue_list_tool",
    "QueueListTool",
    "queue_remove_tool",
    "QueueRemoveTool",
    "queue_execute_tool",
    "QueueExecuteTool",
    "queue_status_tool",
    "QueueStatusTool",
    "queue_clear_tool",
    "QueueClearTool",

    # Queue Executor
    "QueueExecutor",
    "ExecutionMode",
    "get_queue_executor",

    # Registration function
    "register_queue_tools"
]


def register_queue_tools():
    """Register command queue tools with the ACP registry."""
    from ..acp_integration import register_acp_tool

    register_acp_tool(queue_add_tool)
    register_acp_tool(queue_list_tool)
    register_acp_tool(queue_remove_tool)
    register_acp_tool(queue_execute_tool)
    register_acp_tool(queue_status_tool)
    register_acp_tool(queue_clear_tool)