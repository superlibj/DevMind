"""
Command Queue Manager for DevMind.

Manages command queuing, prioritization, and execution scheduling.
"""
import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)


class CommandStatus(Enum):
    """Command execution status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Command priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class QueuedCommand:
    """Represents a queued command."""
    id: str
    command: str
    description: str
    args: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    status: CommandStatus = CommandStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueuedCommand':
        """Create from dictionary."""
        data = data.copy()
        data['priority'] = Priority(data.get('priority', Priority.NORMAL.value))
        data['status'] = CommandStatus(data.get('status', CommandStatus.QUEUED.value))
        return cls(**data)

    @property
    def duration(self) -> Optional[float]:
        """Get command execution duration in seconds."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def wait_time(self) -> float:
        """Get time waiting in queue in seconds."""
        start_time = self.started_at or time.time()
        return start_time - self.created_at


class CommandQueueManager:
    """Manages command queue operations."""

    def __init__(self, queue_dir: Optional[Path] = None):
        """Initialize command queue manager.

        Args:
            queue_dir: Directory for queue persistence
        """
        self.queue_dir = queue_dir or Path("sessions/command_queue")
        self.queue_dir.mkdir(parents=True, exist_ok=True)

        # Queue storage
        self.queue_file = self.queue_dir / "queue.json"
        self.commands: Dict[str, QueuedCommand] = {}

        # Queue configuration
        self.max_queue_size = 100
        self.max_concurrent_commands = 3
        self.auto_execute = False

        # Execution tracking
        self.running_commands: Dict[str, asyncio.Task] = {}
        self.execution_lock = asyncio.Lock()

        # Load existing queue
        self._load_queue()

        # Command handlers registry
        self.command_handlers: Dict[str, Callable] = {}
        self._register_builtin_handlers()

    def add_command(
        self,
        command: str,
        description: str,
        args: Optional[Dict[str, Any]] = None,
        priority: Priority = Priority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QueuedCommand:
        """Add a command to the queue.

        Args:
            command: Command name or identifier
            description: Human-readable description
            args: Command arguments
            priority: Command priority
            metadata: Additional metadata

        Returns:
            Created QueuedCommand instance
        """
        # Check queue size limit
        if len(self.commands) >= self.max_queue_size:
            # Remove oldest completed commands
            self._cleanup_completed_commands()

            if len(self.commands) >= self.max_queue_size:
                # Force cleanup with lower threshold
                self._cleanup_completed_commands(max_keep=5)

                if len(self.commands) >= self.max_queue_size:
                    raise RuntimeError(f"Queue is full (max {self.max_queue_size} commands)")

        # Create command
        queued_cmd = QueuedCommand(
            id=str(uuid.uuid4()),
            command=command,
            description=description,
            args=args or {},
            priority=priority,
            metadata=metadata or {}
        )

        self.commands[queued_cmd.id] = queued_cmd
        self._save_queue()

        logger.info(f"Added command to queue: {queued_cmd.id} - {description}")
        return queued_cmd

    def get_command(self, command_id: str) -> Optional[QueuedCommand]:
        """Get a command by ID.

        Args:
            command_id: Command ID

        Returns:
            QueuedCommand if found, None otherwise
        """
        return self.commands.get(command_id)

    def list_commands(
        self,
        status_filter: Optional[CommandStatus] = None,
        priority_filter: Optional[Priority] = None
    ) -> List[QueuedCommand]:
        """List commands in the queue.

        Args:
            status_filter: Optional status filter
            priority_filter: Optional priority filter

        Returns:
            List of matching commands
        """
        commands = list(self.commands.values())

        # Apply filters
        if status_filter:
            commands = [cmd for cmd in commands if cmd.status == status_filter]

        if priority_filter:
            commands = [cmd for cmd in commands if cmd.priority == priority_filter]

        # Sort by priority (high to low) then by creation time
        commands.sort(key=lambda x: (-x.priority.value, x.created_at))
        return commands

    def remove_command(self, command_id: str) -> bool:
        """Remove a command from the queue.

        Args:
            command_id: Command ID to remove

        Returns:
            True if command was removed
        """
        command = self.commands.get(command_id)
        if not command:
            return False

        # Cancel if running
        if command.status == CommandStatus.RUNNING:
            if command_id in self.running_commands:
                task = self.running_commands[command_id]
                task.cancel()
                del self.running_commands[command_id]

            command.status = CommandStatus.CANCELLED

        # Remove from queue
        del self.commands[command_id]
        self._save_queue()

        logger.info(f"Removed command from queue: {command_id}")
        return True

    def clear_queue(self, status_filter: Optional[CommandStatus] = None) -> int:
        """Clear commands from the queue.

        Args:
            status_filter: Optional status filter (if None, clears all non-running)

        Returns:
            Number of commands removed
        """
        to_remove = []

        for command_id, command in self.commands.items():
            # Don't remove running commands unless explicitly specified
            if command.status == CommandStatus.RUNNING and status_filter != CommandStatus.RUNNING:
                continue

            if status_filter is None or command.status == status_filter:
                to_remove.append(command_id)

        # Remove commands
        for command_id in to_remove:
            self.remove_command(command_id)

        logger.info(f"Cleared {len(to_remove)} commands from queue")
        return len(to_remove)

    def get_next_command(self) -> Optional[QueuedCommand]:
        """Get the next command to execute based on priority.

        Returns:
            Next command to execute, or None if queue is empty
        """
        queued_commands = [
            cmd for cmd in self.commands.values()
            if cmd.status == CommandStatus.QUEUED
        ]

        if not queued_commands:
            return None

        # Sort by priority (high to low) then by creation time (oldest first)
        queued_commands.sort(key=lambda x: (-x.priority.value, x.created_at))
        return queued_commands[0]

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        commands_by_status = {}
        commands_by_priority = {}

        for command in self.commands.values():
            # Count by status
            status_key = command.status.value
            commands_by_status[status_key] = commands_by_status.get(status_key, 0) + 1

            # Count by priority
            priority_key = command.priority.name.lower()
            commands_by_priority[priority_key] = commands_by_priority.get(priority_key, 0) + 1

        # Calculate average wait time for completed commands
        completed_commands = [
            cmd for cmd in self.commands.values()
            if cmd.status in [CommandStatus.COMPLETED, CommandStatus.FAILED]
        ]

        avg_wait_time = 0
        avg_execution_time = 0

        if completed_commands:
            avg_wait_time = sum(cmd.wait_time for cmd in completed_commands) / len(completed_commands)
            durations = [cmd.duration for cmd in completed_commands if cmd.duration]
            if durations:
                avg_execution_time = sum(durations) / len(durations)

        return {
            "total_commands": len(self.commands),
            "commands_by_status": commands_by_status,
            "commands_by_priority": commands_by_priority,
            "running_commands": len(self.running_commands),
            "max_concurrent": self.max_concurrent_commands,
            "avg_wait_time_seconds": round(avg_wait_time, 2),
            "avg_execution_time_seconds": round(avg_execution_time, 2),
            "auto_execute": self.auto_execute
        }

    def register_command_handler(self, command: str, handler: Callable):
        """Register a command handler.

        Args:
            command: Command name
            handler: Async callable that handles the command
        """
        self.command_handlers[command] = handler
        logger.debug(f"Registered command handler: {command}")

    async def execute_command(self, command_id: str) -> bool:
        """Execute a specific command.

        Args:
            command_id: Command ID to execute

        Returns:
            True if execution started successfully
        """
        command = self.commands.get(command_id)
        if not command:
            logger.error(f"Command not found: {command_id}")
            return False

        if command.status != CommandStatus.QUEUED:
            logger.warning(f"Command {command_id} is not in queued status: {command.status}")
            return False

        # Check concurrent execution limit
        if len(self.running_commands) >= self.max_concurrent_commands:
            logger.warning(f"Maximum concurrent commands ({self.max_concurrent_commands}) reached")
            return False

        async with self.execution_lock:
            # Start execution
            command.status = CommandStatus.RUNNING
            command.started_at = time.time()
            self._save_queue()

            # Create execution task
            task = asyncio.create_task(self._execute_command_impl(command))
            self.running_commands[command_id] = task

            logger.info(f"Started executing command: {command_id} - {command.description}")

        return True

    async def _execute_command_impl(self, command: QueuedCommand):
        """Internal command execution implementation."""
        try:
            # Get command handler
            handler = self.command_handlers.get(command.command)
            if not handler:
                raise RuntimeError(f"No handler registered for command: {command.command}")

            # Execute command
            result = await handler(command.args)

            # Update command status
            command.status = CommandStatus.COMPLETED
            command.result = result if isinstance(result, dict) else {"result": result}
            command.completed_at = time.time()

            logger.info(f"Command completed successfully: {command.id}")

        except asyncio.CancelledError:
            command.status = CommandStatus.CANCELLED
            command.completed_at = time.time()
            logger.info(f"Command cancelled: {command.id}")

        except Exception as e:
            command.status = CommandStatus.FAILED
            command.error = str(e)
            command.completed_at = time.time()
            logger.error(f"Command failed: {command.id} - {e}")

        finally:
            # Clean up
            if command.id in self.running_commands:
                del self.running_commands[command.id]

            self._save_queue()

    def _register_builtin_handlers(self):
        """Register built-in command handlers."""
        # Agent command handler
        async def agent_handler(args: Dict[str, Any]):
            from ..agent_system import agent_tool
            from ..acp_integration import create_acp_message

            message = create_acp_message("Agent", args)
            result = await agent_tool.execute(message)

            if result.is_success():
                return {"success": True, "result": result.result, "metadata": result.metadata}
            else:
                raise RuntimeError(result.error)

        self.register_command_handler("agent", agent_handler)

        # Git command handler
        async def git_handler(args: Dict[str, Any]):
            from ..enhanced_git import smart_commit_tool
            from ..acp_integration import create_acp_message

            # Default to smart commit if no specific git command
            git_command = args.pop("git_command", "commit")

            if git_command == "commit":
                message = create_acp_message("SmartCommit", args)
                result = await smart_commit_tool.execute(message)

                if result.is_success():
                    return {"success": True, "result": result.result}
                else:
                    raise RuntimeError(result.error)
            else:
                raise RuntimeError(f"Git command not supported: {git_command}")

        self.register_command_handler("git", git_handler)

        # Tool execution handler
        async def tool_handler(args: Dict[str, Any]):
            from ..acp_integration import acp_registry, create_acp_message

            tool_name = args.pop("tool_name")
            tool = acp_registry.get_tool(tool_name)

            if not tool:
                raise RuntimeError(f"Tool not found: {tool_name}")

            message = create_acp_message(tool_name, args)
            result = await tool.execute(message)

            if result.is_success():
                return {"success": True, "result": result.result, "metadata": result.metadata}
            else:
                raise RuntimeError(result.error)

        self.register_command_handler("tool", tool_handler)

    def _cleanup_completed_commands(self, max_keep: int = 20):
        """Clean up old completed commands to free space."""
        completed_commands = [
            cmd for cmd in self.commands.values()
            if cmd.status in [CommandStatus.COMPLETED, CommandStatus.FAILED, CommandStatus.CANCELLED]
        ]

        if len(completed_commands) <= max_keep:
            return

        # Sort by completion time and remove oldest
        completed_commands.sort(key=lambda x: x.completed_at or 0)
        to_remove = completed_commands[:-max_keep]

        for command in to_remove:
            del self.commands[command.id]

        logger.info(f"Cleaned up {len(to_remove)} completed commands")

    def _save_queue(self):
        """Save queue to disk."""
        try:
            data = {
                "commands": [cmd.to_dict() for cmd in self.commands.values()],
                "config": {
                    "max_queue_size": self.max_queue_size,
                    "max_concurrent_commands": self.max_concurrent_commands,
                    "auto_execute": self.auto_execute
                }
            }

            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving queue: {e}")

    def _load_queue(self):
        """Load queue from disk."""
        try:
            if not self.queue_file.exists():
                return

            with open(self.queue_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load commands
            for cmd_data in data.get("commands", []):
                try:
                    command = QueuedCommand.from_dict(cmd_data)
                    # Reset running commands to queued on startup
                    if command.status == CommandStatus.RUNNING:
                        command.status = CommandStatus.QUEUED
                    self.commands[command.id] = command
                except Exception as e:
                    logger.warning(f"Error loading command: {e}")

            # Load config
            config = data.get("config", {})
            self.max_queue_size = config.get("max_queue_size", self.max_queue_size)
            self.max_concurrent_commands = config.get("max_concurrent_commands", self.max_concurrent_commands)
            self.auto_execute = config.get("auto_execute", self.auto_execute)

            logger.info(f"Loaded {len(self.commands)} commands from queue")

        except Exception as e:
            logger.error(f"Error loading queue: {e}")


# Global queue manager instance
_queue_manager = None


def get_queue_manager() -> CommandQueueManager:
    """Get the global command queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = CommandQueueManager()
    return _queue_manager