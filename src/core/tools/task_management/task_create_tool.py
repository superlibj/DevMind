"""
TaskCreate tool for creating new tasks in the task management system.

Allows creation of structured tasks with metadata and progress tracking.
"""
import logging
from typing import Dict, Any, Optional

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .task_store import get_task_store, TaskStatus

logger = logging.getLogger(__name__)


class TaskCreateTool(ACPTool):
    """Tool for creating new tasks."""

    def __init__(self):
        """Initialize TaskCreate tool."""
        spec = ACPToolSpec(
            name="TaskCreate",
            description="Use this tool to create a structured task list for your current coding session",
            version="1.0.0",
            parameters={
                "required": ["subject", "description"],
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "A brief title for the task"
                    },
                    "description": {
                        "type": "string",
                        "description": "A detailed description of what needs to be done"
                    },
                    "activeForm": {
                        "type": "string",
                        "description": "Present continuous form shown in spinner when in_progress (e.g., \"Running tests\")"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Arbitrary metadata to attach to the task",
                        "additionalProperties": True
                    }
                }
            },
            security_level="standard",
            timeout_seconds=10
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the task creation request."""
        payload = message.payload

        if not payload.get("subject"):
            return "subject is required"

        if not payload.get("description"):
            return "description is required"

        subject = payload["subject"].strip()
        description = payload["description"].strip()

        if not subject:
            return "subject cannot be empty"

        if not description:
            return "description cannot be empty"

        if len(subject) > 200:
            return "subject is too long (max 200 characters)"

        if len(description) > 2000:
            return "description is too long (max 2000 characters)"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the task creation."""
        payload = message.payload
        subject = payload["subject"]
        description = payload["description"]
        active_form = payload.get("activeForm")
        metadata = payload.get("metadata", {})

        try:
            task_store = get_task_store()

            # Create the task
            task = task_store.create_task(
                subject=subject,
                description=description,
                active_form=active_form,
                metadata=metadata
            )

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=f"Task #{task.id} created successfully: {subject}",
                metadata={
                    "task_id": task.id,
                    "subject": subject,
                    "status": task.status.value,
                    "created_at": task.created_at
                }
            )

        except Exception as e:
            logger.exception("Error creating task")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error creating task: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        subject = message.payload.get("subject", "")
        self.logger.debug(f"Creating task: {subject}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            task_id = result.metadata.get("task_id")
            self.logger.info(f"Successfully created task {task_id}")


# Create singleton instance
task_create_tool = TaskCreateTool()