"""
TaskList tool for listing all tasks with summary information.

Provides overview of task status, dependencies, and availability for claiming.
"""
import logging
from typing import Dict, Any, Optional

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .task_store import get_task_store, TaskStatus

logger = logging.getLogger(__name__)


class TaskListTool(ACPTool):
    """Tool for listing all tasks."""

    def __init__(self):
        """Initialize TaskList tool."""
        spec = ACPToolSpec(
            name="TaskList",
            description="Use this tool to list all tasks in the task list",
            version="1.0.0",
            parameters={
                "properties": {}
            },
            security_level="standard",
            timeout_seconds=10
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the task list request."""
        # No validation needed for listing tasks
        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the task listing."""
        try:
            task_store = get_task_store()
            all_tasks = task_store.list_tasks()

            if not all_tasks:
                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result="No tasks found.",
                    metadata={
                        "total_tasks": 0,
                        "by_status": {}
                    }
                )

            # Sort tasks by ID (creation order)
            sorted_tasks = sorted(all_tasks, key=lambda t: t.id)

            # Group by status for statistics
            by_status = {}
            for task in sorted_tasks:
                status = task.status.value
                by_status[status] = by_status.get(status, 0) + 1

            # Format task list
            result_lines = []

            for task in sorted_tasks:
                # Skip deleted tasks
                if task.status == TaskStatus.DELETED:
                    continue

                # Basic task info
                status_indicator = {
                    TaskStatus.PENDING: "[pending]",
                    TaskStatus.IN_PROGRESS: "[in_progress]",
                    TaskStatus.COMPLETED: "[completed]"
                }.get(task.status, f"[{task.status.value}]")

                line = f"#{task.id} {status_indicator} {task.subject}"

                # Add owner if assigned
                if task.owner:
                    line += f" (owner: {task.owner})"

                # Add blocking info
                if task.blocked_by:
                    incomplete_blockers = []
                    for blocking_id in task.blocked_by:
                        blocking_task = task_store.get_task(blocking_id)
                        if blocking_task and blocking_task.status != TaskStatus.COMPLETED:
                            incomplete_blockers.append(blocking_id)

                    if incomplete_blockers:
                        line += f" (blocked by: {', '.join(incomplete_blockers)})"

                result_lines.append(line)

            # Add summary
            if result_lines:
                summary_lines = [
                    f"Found {len(result_lines)} active tasks:",
                    ""
                ] + result_lines
            else:
                summary_lines = ["All tasks completed or deleted."]

            # Add status breakdown
            if by_status:
                summary_lines.extend([
                    "",
                    "**Status Summary:**"
                ])
                for status, count in by_status.items():
                    if status != "deleted":  # Don't show deleted in summary
                        summary_lines.append(f"- {status}: {count}")

            # Show available tasks
            available_tasks = task_store.list_available_tasks()
            if available_tasks:
                summary_lines.extend([
                    "",
                    f"**{len(available_tasks)} task(s) available for claiming** (pending, unowned, not blocked)"
                ])

            result_text = "\n".join(summary_lines)

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=result_text,
                metadata={
                    "total_tasks": len(sorted_tasks),
                    "active_tasks": len(result_lines),
                    "available_tasks": len(available_tasks),
                    "by_status": by_status
                }
            )

        except Exception as e:
            logger.exception("Error listing tasks")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error listing tasks: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        self.logger.debug("Listing all tasks")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            total_tasks = result.metadata.get("total_tasks", 0)
            available_tasks = result.metadata.get("available_tasks", 0)
            self.logger.debug(f"Listed {total_tasks} tasks, {available_tasks} available")


# Create singleton instance
task_list_tool = TaskListTool()