"""
TaskUpdate tool for updating existing tasks in the task management system.

Allows modification of task status, dependencies, and metadata.
"""
import logging
from typing import Dict, Any, Optional, List

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .task_store import get_task_store, TaskStatus

logger = logging.getLogger(__name__)


class TaskUpdateTool(ACPTool):
    """Tool for updating existing tasks."""

    def __init__(self):
        """Initialize TaskUpdate tool."""
        spec = ACPToolSpec(
            name="TaskUpdate",
            description="Use this tool to update a task in the task list",
            version="1.0.0",
            parameters={
                "required": ["taskId"],
                "properties": {
                    "taskId": {
                        "type": "string",
                        "description": "The ID of the task to update"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "deleted"],
                        "description": "New status for the task"
                    },
                    "subject": {
                        "type": "string",
                        "description": "New subject for the task"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description for the task"
                    },
                    "activeForm": {
                        "type": "string",
                        "description": "Present continuous form shown in spinner when in_progress (e.g., \"Running tests\")"
                    },
                    "owner": {
                        "type": "string",
                        "description": "New owner for the task"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Metadata keys to merge into the task. Set a key to null to delete it.",
                        "additionalProperties": True
                    },
                    "addBlocks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs that this task blocks"
                    },
                    "addBlockedBy": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs that block this task"
                    }
                }
            },
            security_level="standard",
            timeout_seconds=10
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the task update request."""
        payload = message.payload

        if not payload.get("taskId"):
            return "taskId is required"

        task_id = payload["taskId"]
        task_store = get_task_store()
        task = task_store.get_task(task_id)

        if not task:
            return f"Task with ID '{task_id}' not found"

        # Validate status if provided
        status_str = payload.get("status")
        if status_str:
            try:
                TaskStatus(status_str)
            except ValueError:
                return f"Invalid status: {status_str}. Valid values are: pending, in_progress, completed, deleted"

        # Validate dependency task IDs
        add_blocks = payload.get("addBlocks", [])
        add_blocked_by = payload.get("addBlockedBy", [])

        for dep_id in add_blocks + add_blocked_by:
            if not isinstance(dep_id, str) or not dep_id.strip():
                return "Dependency task IDs must be non-empty strings"

            # Check for circular dependencies
            if dep_id == task_id:
                return "Task cannot depend on itself"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the task update."""
        payload = message.payload
        task_id = payload["taskId"]

        try:
            task_store = get_task_store()

            # Parse status if provided
            status = None
            status_str = payload.get("status")
            if status_str:
                if status_str == "deleted":
                    # Special handling for deletion
                    success = task_store.delete_task(task_id)
                    if success:
                        return ACPToolResult(
                            status=ACPStatus.COMPLETED,
                            result=f"Task #{task_id} deleted successfully",
                            metadata={"task_id": task_id, "action": "deleted"}
                        )
                    else:
                        return ACPToolResult(
                            status=ACPStatus.FAILED,
                            error=f"Failed to delete task {task_id}"
                        )
                else:
                    status = TaskStatus(status_str)

            # Update the task
            updated_task = task_store.update_task(
                task_id=task_id,
                status=status,
                subject=payload.get("subject"),
                description=payload.get("description"),
                active_form=payload.get("activeForm"),
                owner=payload.get("owner"),
                metadata=payload.get("metadata"),
                add_blocks=payload.get("addBlocks"),
                add_blocked_by=payload.get("addBlockedBy")
            )

            if updated_task:
                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result=f"Updated task #{task_id} status",
                    metadata={
                        "task_id": task_id,
                        "status": updated_task.status.value,
                        "subject": updated_task.subject,
                        "owner": updated_task.owner,
                        "updated_at": updated_task.updated_at
                    }
                )
            else:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Failed to update task {task_id}"
                )

        except Exception as e:
            logger.exception(f"Error updating task {task_id}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error updating task: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        task_id = message.payload.get("taskId", "")
        status = message.payload.get("status", "")
        self.logger.debug(f"Updating task {task_id}" + (f" to {status}" if status else ""))

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            task_id = result.metadata.get("task_id")
            action = result.metadata.get("action", "updated")
            self.logger.info(f"Successfully {action} task {task_id}")


# Create singleton instance
task_update_tool = TaskUpdateTool()