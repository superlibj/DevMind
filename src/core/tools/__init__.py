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
from .enhanced_tools import (
    read_tool, ReadTool,
    write_tool, WriteTool,
    edit_tool, EditTool,
    bash_tool, BashTool,
    glob_tool, GlobTool,
    grep_tool, GrepTool,
    websearch_tool, WebSearchTool,
    webfetch_tool, WebFetchTool,
    register_enhanced_tools
)
from .task_management import (
    TaskStore, Task, TaskStatus,
    task_create_tool, TaskCreateTool,
    task_update_tool, TaskUpdateTool,
    task_get_tool, TaskGetTool,
    task_list_tool, TaskListTool,
    enter_plan_mode_tool, EnterPlanModeTool,
    exit_plan_mode_tool, ExitPlanModeTool,
    register_task_management_tools
)
from .permission_system import (
    ask_user_question_tool, AskUserQuestionTool,
    PermissionManager, PermissionLevel, PermissionDecision,
    register_permission_tools
)
from .enhanced_git import (
    smart_commit_tool, SmartCommitTool,
    pr_create_tool, PRCreateTool,
    GitSafetyChecker,
    register_enhanced_git_tools
)
from .background_tasks import (
    BackgroundTaskManager, TaskState, BackgroundTask,
    task_output_tool, TaskOutputTool,
    task_stop_tool, TaskStopTool,
    register_background_task_tools
)
from .memory_system import (
    MemoryManager, MemoryEntry, MemoryTopic,
    EnhancedSessionManager, SessionData,
    auto_memory_tool, AutoMemoryTool,
    register_memory_tools
)
from .agent_system import (
    AgentManager, AgentType, AgentCapability,
    agent_tool, AgentTool,
    agent_manager, agent_registry,
    register_agent_system_tools
)
from .worktree_system import (
    WorktreeManager, WorktreeInfo,
    enter_worktree_tool, EnterWorktreeTool,
    get_worktree_manager,
    register_worktree_tools
)
from .command_queue import (
    CommandQueueManager, QueuedCommand, CommandStatus,
    queue_add_tool, QueueAddTool,
    queue_list_tool, QueueListTool,
    queue_remove_tool, QueueRemoveTool,
    queue_execute_tool, QueueExecuteTool,
    queue_status_tool, QueueStatusTool,
    queue_clear_tool, QueueClearTool,
    QueueExecutor, ExecutionMode,
    get_queue_manager, get_queue_executor,
    register_queue_tools
)
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

    # Enhanced Tools
    "read_tool",
    "ReadTool",
    "write_tool",
    "WriteTool",
    "edit_tool",
    "EditTool",
    "bash_tool",
    "BashTool",
    "glob_tool",
    "GlobTool",
    "grep_tool",
    "GrepTool",
    "websearch_tool",
    "WebSearchTool",
    "webfetch_tool",
    "WebFetchTool",

    # Task Management
    "TaskStore",
    "Task",
    "TaskStatus",
    "task_create_tool",
    "TaskCreateTool",
    "task_update_tool",
    "TaskUpdateTool",
    "task_get_tool",
    "TaskGetTool",
    "task_list_tool",
    "TaskListTool",
    "enter_plan_mode_tool",
    "EnterPlanModeTool",
    "exit_plan_mode_tool",
    "ExitPlanModeTool",

    # Permission System
    "ask_user_question_tool",
    "AskUserQuestionTool",
    "PermissionManager",
    "PermissionLevel",
    "PermissionDecision",

    # Enhanced Git Integration
    "smart_commit_tool",
    "SmartCommitTool",
    "pr_create_tool",
    "PRCreateTool",
    "GitSafetyChecker",

    # Background Task Management
    "BackgroundTaskManager",
    "TaskState",
    "BackgroundTask",
    "task_output_tool",
    "TaskOutputTool",
    "task_stop_tool",
    "TaskStopTool",

    # Memory and Session Management
    "MemoryManager",
    "MemoryEntry",
    "MemoryTopic",
    "EnhancedSessionManager",
    "SessionData",
    "auto_memory_tool",
    "AutoMemoryTool",

    # Agent System
    "AgentManager",
    "AgentType",
    "AgentCapability",
    "agent_tool",
    "AgentTool",
    "agent_manager",
    "agent_registry",

    # Worktree System
    "WorktreeManager",
    "WorktreeInfo",
    "enter_worktree_tool",
    "EnterWorktreeTool",
    "get_worktree_manager",

    # Command Queue System
    "CommandQueueManager",
    "QueuedCommand",
    "CommandStatus",
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
    "QueueExecutor",
    "ExecutionMode",
    "get_queue_manager",
    "get_queue_executor",

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

    # Register enhanced tools
    register_enhanced_tools()

    # Register task management tools
    register_task_management_tools()

    # Register permission system tools
    register_permission_tools()

    # Register enhanced git tools
    register_enhanced_git_tools()

    # Register background task tools
    register_background_task_tools()

    # Register memory system tools
    register_memory_tools()

    # Register agent system tools
    register_agent_system_tools()

    # Register worktree system tools
    register_worktree_tools()

    # Register command queue tools
    register_queue_tools()


def get_available_tools():
    """Get list of all available tools.

    Returns:
        List of tool specifications
    """
    return acp_registry.list_tools()


# Auto-register tools on module import
register_all_tools()