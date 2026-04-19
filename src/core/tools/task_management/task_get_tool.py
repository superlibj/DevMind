"""
TaskGet tool for retrieving individual tasks by ID.

Provides detailed task information including dependencies and metadata.
"""
import logging
from typing import Dict, Any, Optional

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .task_store import get_task_store

logger = logging.getLogger(__name__)


class TaskGetTool(ACPTool):
    """Tool for retrieving individual tasks."""

    def __init__(self):
        """Initialize TaskGet tool."""
        spec = ACPToolSpec(
            name="TaskGet",
            description="Use this tool to retrieve a task by its ID from the task list",
            version="1.0.0",
            parameters={
                "required": ["taskId"],
                "properties": {
                    "taskId": {
                        "type": "string",
                        "description": "The ID of the task to retrieve"
                    }
                }
            },
            security_level="standard",
            timeout_seconds=10
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the task retrieval request."""
        payload = message.payload

        if not payload.get("taskId"):
            return "taskId is required"

        task_id = payload["taskId"].strip()
        if not task_id:
            return "taskId cannot be empty"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the task retrieval."""
        payload = message.payload
        task_id = payload["taskId"]

        try:
            task_store = get_task_store()
            task = task_store.get_task(task_id)

            if not task:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Task with ID '{task_id}' not found"
                )

            # Format task details
            result_lines = [
                f"**Task #{task.id}: {task.subject}**",
                "",
                f"**Status:** {task.status.value}",
                f"**Owner:** {task.owner if task.owner else 'Unassigned'}",
                "",
                "**Description:**",
                task.description,
                ""
            ]

            if task.active_form:
                result_lines.extend([
                    f"**Active Form:** {task.active_form}",
                    ""
                ])

            # Show dependencies
            if task.blocks:
                blocking_tasks = []
                for blocked_id in task.blocks:
                    blocked_task = task_store.get_task(blocked_id)
                    if blocked_task:
                        blocking_tasks.append(f"#{blocked_id} ({blocked_task.subject})")
                    else:
                        blocking_tasks.append(f"#{blocked_id} (not found)")

                result_lines.extend([
                    "**Blocks:** " + ", ".join(blocking_tasks),
                    ""
                ])

            if task.blocked_by:
                blocking_tasks = []
                for blocking_id in task.blocked_by:
                    blocking_task = task_store.get_task(blocking_id)
                    if blocking_task:
                        blocking_tasks.append(f"#{blocking_id} ({blocking_task.subject})")
                    else:
                        blocking_tasks.append(f"#{blocking_id} (not found)")

                result_lines.extend([
                    "**Blocked By:** " + ", ".join(blocking_tasks),
                    ""
                ])

            # Show metadata if present
            if task.metadata:
                result_lines.extend([
                    "**Metadata:**",
                    ""
                ])
                for key, value in task.metadata.items():
                    result_lines.append(f"- {key}: {value}")
                result_lines.append("")

            # Timestamps
            import datetime
            created_time = datetime.datetime.fromtimestamp(task.created_at).strftime("%Y-%m-%d %H:%M:%S")
            updated_time = datetime.datetime.fromtimestamp(task.updated_at).strftime("%Y-%m-%d %H:%M:%S")

            result_lines.extend([
                f"**Created:** {created_time}",
                f"**Updated:** {updated_time}"
            ])

            result_text = "\n".join(result_lines)

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=result_text,
                metadata={
                    "task_id": task.id,
                    "subject": task.subject,
                    "status": task.status.value,
                    "owner": task.owner,
                    "blocks_count": len(task.blocks),
                    "blocked_by_count": len(task.blocked_by),
                    "is_blocked": task.is_blocked(task_store),
                    "can_be_claimed": task.can_be_claimed(task_store)
                }
            )

        except Exception as e:
            logger.exception(f"Error retrieving task {task_id}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error retrieving task: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        task_id = message.payload.get("taskId", "")
        self.logger.debug(f"Retrieving task: {task_id}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            task_id = result.metadata.get("task_id")
            self.logger.debug(f"Successfully retrieved task {task_id}")


# Create singleton instance
task_get_tool = TaskGetTool()