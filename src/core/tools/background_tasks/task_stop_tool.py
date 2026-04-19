"""
TaskStop tool for stopping running background tasks.

Provides safe termination of long-running background tasks with
proper cleanup and resource management.
"""
import logging
from typing import Dict, Any, Optional

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .task_manager import get_background_task_manager, TaskState

logger = logging.getLogger(__name__)


class TaskStopTool(ACPTool):
    """Tool for stopping background tasks."""

    def __init__(self):
        """Initialize TaskStop tool."""
        spec = ACPToolSpec(
            name="TaskStop",
            description="Stops a running background task by its ID",
            version="1.0.0",
            parameters={
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the background task to stop"
                    },
                    "shell_id": {
                        "type": "string",
                        "description": "Deprecated: use task_id instead"
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30,
            requires_confirmation=True  # Stopping tasks might interrupt important work
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the task stop request."""
        payload = message.payload

        # Support legacy shell_id parameter
        task_id = payload.get("task_id") or payload.get("shell_id")

        if not task_id:
            return "task_id is required (or use deprecated shell_id)"

        task_id = task_id.strip()
        if not task_id:
            return "task_id cannot be empty"

        # Check if task exists
        task_manager = get_background_task_manager()
        task = task_manager.get_task(task_id)
        if not task:
            return f"Task {task_id} not found"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the task stop operation."""
        payload = message.payload

        # Support legacy shell_id parameter
        task_id = payload.get("task_id") or payload.get("shell_id")

        try:
            # Get task manager
            task_manager = get_background_task_manager()

            # Get task info before stopping
            task = task_manager.get_task(task_id)
            if not task:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Task {task_id} not found"
                )

            original_state = task.state
            task_description = task.description or "No description"

            # Check if task is actually running
            if not task.is_running:
                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result=f"Task {task_id} is not running (current state: {original_state.value})",
                    metadata={
                        "task_id": task_id,
                        "original_state": original_state.value,
                        "action": "no_action_needed"
                    }
                )

            # Attempt to stop the task
            success = await task_manager.stop_task(task_id)

            if success:
                # Get updated task state
                updated_task = task_manager.get_task(task_id)
                new_state = updated_task.state if updated_task else TaskState.CANCELLED

                result_message = f"✅ Successfully stopped task {task_id}\n\n"
                result_message += f"**Description:** {task_description}\n"
                result_message += f"**State:** {original_state.value} → {new_state.value}\n"
                result_message += f"**Duration:** {task.duration:.1f} seconds"

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result=result_message,
                    metadata={
                        "task_id": task_id,
                        "original_state": original_state.value,
                        "new_state": new_state.value,
                        "duration": task.duration,
                        "action": "stopped"
                    }
                )
            else:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Failed to stop task {task_id}. The task may have already finished or be unresponsive."
                )

        except Exception as e:
            logger.exception(f"Error stopping task {task_id}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error stopping task: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        task_id = message.payload.get("task_id") or message.payload.get("shell_id")
        self.logger.info(f"Attempting to stop background task: {task_id}")

        # Get task info for logging
        task_manager = get_background_task_manager()
        task = task_manager.get_task(task_id)
        if task:
            self.logger.debug(
                f"Task {task_id} state: {task.state.value}, "
                f"duration: {task.duration:.1f}s"
            )

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            task_id = result.metadata.get("task_id")
            action = result.metadata.get("action")

            if action == "stopped":
                duration = result.metadata.get("duration", 0)
                self.logger.info(f"Successfully stopped task {task_id} after {duration:.1f}s")
            elif action == "no_action_needed":
                self.logger.debug(f"Task {task_id} was not running")
        else:
            self.logger.warning(f"Failed to stop task: {result.error}")


# Create singleton instance
task_stop_tool = TaskStopTool()