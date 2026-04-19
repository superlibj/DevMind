"""
Command Queue Tools for DevMind.

Provides ACP tools for managing command queue operations.
"""
import logging
import time
from typing import Dict, Any, Optional

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .queue_manager import get_queue_manager, Priority, CommandStatus

logger = logging.getLogger(__name__)


class QueueAddTool(ACPTool):
    """Tool for adding commands to the queue."""

    def __init__(self):
        """Initialize QueueAdd tool."""
        spec = ACPToolSpec(
            name="QueueAdd",
            description="Add a command to the execution queue with priority support",
            version="1.0.0",
            parameters={
                "required": ["command", "description"],
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command type to queue (agent, git, tool, etc.)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable description of the command"
                    },
                    "args": {
                        "type": "object",
                        "description": "Command arguments as key-value pairs",
                        "default": {}
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "urgent"],
                        "description": "Command priority level",
                        "default": "normal"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata for the command",
                        "default": {}
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the queue add request."""
        payload = message.payload

        command = payload.get("command")
        if not command:
            return "command is required"

        description = payload.get("description")
        if not description:
            return "description is required"

        priority = payload.get("priority", "normal")
        if priority not in ["low", "normal", "high", "urgent"]:
            return "priority must be one of: low, normal, high, urgent"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute queue add operation."""
        payload = message.payload

        try:
            queue_manager = get_queue_manager()

            # Extract parameters
            command = payload["command"]
            description = payload["description"]
            args = payload.get("args", {})
            priority_str = payload.get("priority", "normal")
            metadata = payload.get("metadata", {})

            # Convert priority
            priority_map = {
                "low": Priority.LOW,
                "normal": Priority.NORMAL,
                "high": Priority.HIGH,
                "urgent": Priority.URGENT
            }
            priority = priority_map[priority_str]

            # Add command to queue
            queued_cmd = queue_manager.add_command(
                command=command,
                description=description,
                args=args,
                priority=priority,
                metadata=metadata
            )

            # Format result
            result_message = f"""📋 **Command Added to Queue**

**ID:** {queued_cmd.id}
**Command:** {command}
**Description:** {description}
**Priority:** {priority.name.title()}
**Status:** {queued_cmd.status.value.title()}

The command has been queued for execution. Use QueueList to see all queued commands or QueueExecute to start processing the queue."""

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=result_message,
                metadata={
                    "command_id": queued_cmd.id,
                    "command": command,
                    "priority": priority.name.lower(),
                    "status": queued_cmd.status.value
                }
            )

        except Exception as e:
            logger.exception(f"Error adding command to queue")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to add command to queue: {str(e)}"
            )


class QueueListTool(ACPTool):
    """Tool for listing queued commands."""

    def __init__(self):
        """Initialize QueueList tool."""
        spec = ACPToolSpec(
            name="QueueList",
            description="List commands in the execution queue with filtering options",
            version="1.0.0",
            parameters={
                "required": [],
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["queued", "running", "completed", "failed", "cancelled"],
                        "description": "Filter by command status"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "urgent"],
                        "description": "Filter by command priority"
                    },
                    "show_stats": {
                        "type": "boolean",
                        "description": "Include queue statistics",
                        "default": True
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30
        )
        super().__init__(spec)

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute queue list operation."""
        payload = message.payload

        try:
            queue_manager = get_queue_manager()

            # Extract filters
            status_filter = None
            if payload.get("status"):
                status_filter = CommandStatus(payload["status"])

            priority_filter = None
            if payload.get("priority"):
                priority_map = {
                    "low": Priority.LOW,
                    "normal": Priority.NORMAL,
                    "high": Priority.HIGH,
                    "urgent": Priority.URGENT
                }
                priority_filter = priority_map[payload["priority"]]

            show_stats = payload.get("show_stats", True)

            # Get commands
            commands = queue_manager.list_commands(
                status_filter=status_filter,
                priority_filter=priority_filter
            )

            # Build result
            result_lines = ["📋 **Command Queue**", ""]

            if show_stats:
                stats = queue_manager.get_queue_stats()
                result_lines.extend([
                    "**Queue Statistics:**",
                    f"• Total Commands: {stats['total_commands']}",
                    f"• Running: {stats['running_commands']}/{stats['max_concurrent']}",
                    f"• Average Wait Time: {stats['avg_wait_time_seconds']}s",
                    f"• Auto-Execute: {'Enabled' if stats['auto_execute'] else 'Disabled'}",
                    ""
                ])

            if not commands:
                result_lines.append("No commands in queue.")
            else:
                result_lines.append("**Commands:**")
                result_lines.append("")

                for i, cmd in enumerate(commands, 1):
                    # Status emoji
                    status_emoji = {
                        CommandStatus.QUEUED: "⏳",
                        CommandStatus.RUNNING: "🏃",
                        CommandStatus.COMPLETED: "✅",
                        CommandStatus.FAILED: "❌",
                        CommandStatus.CANCELLED: "🚫"
                    }

                    # Priority indicator
                    priority_indicator = "●" * cmd.priority.value

                    # Format time info
                    if cmd.status == CommandStatus.RUNNING:
                        time_info = f"Running for {int(time.time() - cmd.started_at)}s" if cmd.started_at else ""
                    elif cmd.duration:
                        time_info = f"Took {cmd.duration:.1f}s"
                    else:
                        time_info = f"Waiting {int(cmd.wait_time)}s"

                    result_lines.extend([
                        f"{i}. {status_emoji.get(cmd.status, '❓')} **{cmd.description}**",
                        f"   ID: `{cmd.id[:8]}...` | Command: `{cmd.command}` | Priority: {priority_indicator}",
                        f"   Status: {cmd.status.value.title()} | {time_info}",
                        ""
                    ])

                    if cmd.error:
                        result_lines.extend([
                            f"   ❌ Error: {cmd.error}",
                            ""
                        ])

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result="\n".join(result_lines),
                metadata={
                    "commands_count": len(commands),
                    "commands": [
                        {
                            "id": cmd.id,
                            "command": cmd.command,
                            "description": cmd.description,
                            "status": cmd.status.value,
                            "priority": cmd.priority.value
                        }
                        for cmd in commands
                    ]
                }
            )

        except Exception as e:
            logger.exception(f"Error listing queue")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to list queue: {str(e)}"
            )


class QueueRemoveTool(ACPTool):
    """Tool for removing commands from the queue."""

    def __init__(self):
        """Initialize QueueRemove tool."""
        spec = ACPToolSpec(
            name="QueueRemove",
            description="Remove a command from the execution queue",
            version="1.0.0",
            parameters={
                "required": ["command_id"],
                "properties": {
                    "command_id": {
                        "type": "string",
                        "description": "ID of the command to remove (can be partial)"
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30
        )
        super().__init__(spec)

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute queue remove operation."""
        payload = message.payload

        try:
            queue_manager = get_queue_manager()
            command_id = payload["command_id"]

            # Try exact match first
            command = queue_manager.get_command(command_id)

            # If not found, try partial match
            if not command:
                all_commands = queue_manager.list_commands()
                matches = [cmd for cmd in all_commands if cmd.id.startswith(command_id)]

                if len(matches) == 1:
                    command = matches[0]
                    command_id = command.id
                elif len(matches) > 1:
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"Ambiguous command ID '{command_id}'. Multiple matches: {[cmd.id[:8] for cmd in matches]}"
                    )

            if not command:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Command not found: {command_id}"
                )

            # Remove command
            success = queue_manager.remove_command(command_id)

            if success:
                result_message = f"""✅ **Command Removed from Queue**

**ID:** {command.id}
**Description:** {command.description}
**Status:** {command.status.value.title()}

The command has been removed from the queue."""

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result=result_message,
                    metadata={
                        "command_id": command_id,
                        "description": command.description,
                        "was_running": command.status == CommandStatus.RUNNING
                    }
                )
            else:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Failed to remove command: {command_id}"
                )

        except Exception as e:
            logger.exception(f"Error removing command from queue")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to remove command: {str(e)}"
            )


class QueueExecuteTool(ACPTool):
    """Tool for executing queued commands."""

    def __init__(self):
        """Initialize QueueExecute tool."""
        spec = ACPToolSpec(
            name="QueueExecute",
            description="Execute commands from the queue",
            version="1.0.0",
            parameters={
                "required": [],
                "properties": {
                    "command_id": {
                        "type": "string",
                        "description": "Execute specific command by ID (if not provided, executes next in queue)"
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Number of commands to execute (default: 1)",
                        "default": 1
                    },
                    "wait": {
                        "type": "boolean",
                        "description": "Wait for commands to complete before returning",
                        "default": False
                    }
                }
            },
            security_level="standard",
            timeout_seconds=300  # 5 minutes for execution
        )
        super().__init__(spec)

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute queue execution operation."""
        payload = message.payload

        try:
            queue_manager = get_queue_manager()

            command_id = payload.get("command_id")
            count = payload.get("count", 1)
            wait = payload.get("wait", False)

            executed_commands = []

            if command_id:
                # Execute specific command
                success = await queue_manager.execute_command(command_id)
                if success:
                    command = queue_manager.get_command(command_id)
                    if command:
                        executed_commands.append(command)
                else:
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"Failed to execute command: {command_id}"
                    )
            else:
                # Execute next commands in queue
                for _ in range(count):
                    next_command = queue_manager.get_next_command()
                    if not next_command:
                        break

                    success = await queue_manager.execute_command(next_command.id)
                    if success:
                        executed_commands.append(next_command)

            if not executed_commands:
                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result="📋 **No commands to execute**\n\nThe queue is empty or no commands are in queued status.",
                    metadata={"executed_count": 0}
                )

            # Wait for completion if requested
            if wait:
                import asyncio
                while any(cmd.id in queue_manager.running_commands for cmd in executed_commands):
                    await asyncio.sleep(0.5)

                # Refresh command status
                for i, cmd in enumerate(executed_commands):
                    executed_commands[i] = queue_manager.get_command(cmd.id) or cmd

            # Format result
            result_lines = [
                f"🚀 **Executed {len(executed_commands)} Command(s)**",
                ""
            ]

            for cmd in executed_commands:
                status_emoji = {
                    CommandStatus.RUNNING: "🏃",
                    CommandStatus.COMPLETED: "✅",
                    CommandStatus.FAILED: "❌",
                    CommandStatus.CANCELLED: "🚫"
                }

                result_lines.extend([
                    f"{status_emoji.get(cmd.status, '❓')} **{cmd.description}**",
                    f"   ID: `{cmd.id[:8]}...` | Status: {cmd.status.value.title()}",
                    ""
                ])

                if cmd.status == CommandStatus.FAILED and cmd.error:
                    result_lines.extend([
                        f"   ❌ Error: {cmd.error}",
                        ""
                    ])
                elif cmd.status == CommandStatus.COMPLETED and cmd.duration:
                    result_lines.extend([
                        f"   ⏱️ Completed in {cmd.duration:.1f}s",
                        ""
                    ])

            if wait:
                result_lines.append("All commands have finished executing.")
            else:
                result_lines.append("Commands are running in the background. Use QueueList to check status.")

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result="\n".join(result_lines),
                metadata={
                    "executed_count": len(executed_commands),
                    "executed_commands": [
                        {
                            "id": cmd.id,
                            "description": cmd.description,
                            "status": cmd.status.value
                        }
                        for cmd in executed_commands
                    ],
                    "waited": wait
                }
            )

        except Exception as e:
            logger.exception(f"Error executing queue commands")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to execute queue commands: {str(e)}"
            )


class QueueStatusTool(ACPTool):
    """Tool for getting queue status and statistics."""

    def __init__(self):
        """Initialize QueueStatus tool."""
        spec = ACPToolSpec(
            name="QueueStatus",
            description="Get detailed status and statistics about the command queue",
            version="1.0.0",
            parameters={
                "required": [],
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "description": "Include detailed breakdown of all commands",
                        "default": False
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30
        )
        super().__init__(spec)

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute queue status operation."""
        payload = message.payload

        try:
            queue_manager = get_queue_manager()
            detailed = payload.get("detailed", False)

            # Get statistics
            stats = queue_manager.get_queue_stats()
            all_commands = queue_manager.list_commands()

            # Build result
            result_lines = [
                "📊 **Command Queue Status**",
                ""
            ]

            # Basic statistics
            result_lines.extend([
                "**Overview:**",
                f"• Total Commands: {stats['total_commands']}",
                f"• Running Commands: {stats['running_commands']}/{stats['max_concurrent']}",
                f"• Auto-Execute: {'Enabled' if stats['auto_execute'] else 'Disabled'}",
                ""
            ])

            # Commands by status
            if stats['commands_by_status']:
                result_lines.append("**Commands by Status:**")
                for status, count in stats['commands_by_status'].items():
                    result_lines.append(f"• {status.title()}: {count}")
                result_lines.append("")

            # Commands by priority
            if stats['commands_by_priority']:
                result_lines.append("**Commands by Priority:**")
                for priority, count in stats['commands_by_priority'].items():
                    result_lines.append(f"• {priority.title()}: {count}")
                result_lines.append("")

            # Performance metrics
            if stats['avg_wait_time_seconds'] > 0 or stats['avg_execution_time_seconds'] > 0:
                result_lines.extend([
                    "**Performance Metrics:**",
                    f"• Average Wait Time: {stats['avg_wait_time_seconds']}s",
                    f"• Average Execution Time: {stats['avg_execution_time_seconds']}s",
                    ""
                ])

            # Detailed breakdown
            if detailed and all_commands:
                result_lines.extend([
                    "**Detailed Command List:**",
                    ""
                ])

                for cmd in all_commands:
                    result_lines.extend([
                        f"**{cmd.description}**",
                        f"  • ID: {cmd.id}",
                        f"  • Command: {cmd.command}",
                        f"  • Status: {cmd.status.value.title()}",
                        f"  • Priority: {cmd.priority.name.title()}",
                        f"  • Created: {time.strftime('%H:%M:%S', time.localtime(cmd.created_at))}",
                        ""
                    ])

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result="\n".join(result_lines),
                metadata=stats
            )

        except Exception as e:
            logger.exception(f"Error getting queue status")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to get queue status: {str(e)}"
            )


class QueueClearTool(ACPTool):
    """Tool for clearing the command queue."""

    def __init__(self):
        """Initialize QueueClear tool."""
        spec = ACPToolSpec(
            name="QueueClear",
            description="Clear commands from the queue",
            version="1.0.0",
            parameters={
                "required": [],
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["queued", "completed", "failed", "cancelled", "all"],
                        "description": "Clear only commands with specific status (default: queued)",
                        "default": "queued"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirmation to clear the queue",
                        "default": False
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30
        )
        super().__init__(spec)

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute queue clear operation."""
        payload = message.payload

        try:
            queue_manager = get_queue_manager()

            status_filter_str = payload.get("status", "queued")
            confirm = payload.get("confirm", False)

            if not confirm:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="Queue clear operation requires confirmation. Set 'confirm: true' to proceed."
                )

            # Map status string to enum
            status_filter = None
            if status_filter_str != "all":
                try:
                    status_filter = CommandStatus(status_filter_str)
                except ValueError:
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"Invalid status: {status_filter_str}"
                    )

            # Clear queue
            removed_count = queue_manager.clear_queue(status_filter)

            # Format result
            status_text = status_filter_str if status_filter_str != "all" else "all"
            result_message = f"""🗑️ **Queue Cleared**

**Status Filter:** {status_text.title()}
**Commands Removed:** {removed_count}

The specified commands have been removed from the queue."""

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=result_message,
                metadata={
                    "removed_count": removed_count,
                    "status_filter": status_filter_str
                }
            )

        except Exception as e:
            logger.exception(f"Error clearing queue")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to clear queue: {str(e)}"
            )


# Create singleton instances
queue_add_tool = QueueAddTool()
queue_list_tool = QueueListTool()
queue_remove_tool = QueueRemoveTool()
queue_execute_tool = QueueExecuteTool()
queue_status_tool = QueueStatusTool()
queue_clear_tool = QueueClearTool()