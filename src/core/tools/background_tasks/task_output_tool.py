"""
TaskOutput tool for retrieving output from running or completed background tasks.

Provides access to task output with blocking/non-blocking options and
comprehensive status information.
"""
import logging
from typing import Dict, Any, Optional

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .task_manager import get_background_task_manager, TaskState

logger = logging.getLogger(__name__)


class TaskOutputTool(ACPTool):
    """Tool for retrieving output from background tasks."""

    def __init__(self):
        """Initialize TaskOutput tool."""
        spec = ACPToolSpec(
            name="TaskOutput",
            description="Retrieves output from a running or completed task (background shell, agent, or remote session)",
            version="1.0.0",
            parameters={
                "required": ["task_id", "block", "timeout"],
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID to get output from"
                    },
                    "block": {
                        "type": "boolean",
                        "description": "Whether to wait for completion",
                        "default": True
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Max wait time in ms",
                        "minimum": 0,
                        "maximum": 600000,
                        "default": 30000
                    }
                }
            },
            security_level="standard",
            timeout_seconds=60
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the task output request."""
        payload = message.payload

        if not payload.get("task_id"):
            return "task_id is required"

        task_id = payload["task_id"].strip()
        if not task_id:
            return "task_id cannot be empty"

        # Validate timeout
        timeout = payload.get("timeout", 30000)
        if not isinstance(timeout, (int, float)) or timeout < 0:
            return "timeout must be a non-negative number"

        if timeout > 600000:  # 10 minutes max
            return "timeout cannot exceed 600000ms (10 minutes)"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the task output retrieval."""
        payload = message.payload
        task_id = payload["task_id"]
        block = payload.get("block", True)
        timeout_ms = payload.get("timeout", 30000)
        timeout_seconds = timeout_ms / 1000

        try:
            # Get task manager
            task_manager = get_background_task_manager()

            # Get task output
            output_data = await task_manager.get_task_output(
                task_id=task_id,
                block=block,
                timeout=timeout_seconds
            )

            if not output_data["success"]:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=output_data["error"]
                )

            # Format result based on task state
            task_info = output_data["task_info"]
            state = output_data["state"]
            output = output_data["output"]
            duration = output_data.get("duration", 0)

            # Build result message
            result_lines = [
                f"**Task {task_id} Status: {state.upper()}**",
                ""
            ]

            if task_info:
                description = task_info.get("description", "No description")
                command = task_info.get("command", "N/A")

                result_lines.extend([
                    f"**Description:** {description}",
                    f"**Command:** {command}",
                    f"**Duration:** {duration:.1f}s",
                    ""
                ])

            # Add exit code if available
            exit_code = output_data.get("exit_code")
            if exit_code is not None:
                result_lines.append(f"**Exit Code:** {exit_code}")
                result_lines.append("")

            # Add error message if failed
            error_message = output_data.get("error_message")
            if error_message:
                result_lines.extend([
                    f"**Error:** {error_message}",
                    ""
                ])

            # Add output
            if output:
                result_lines.extend([
                    "**Output:**",
                    "```",
                    output.rstrip(),
                    "```"
                ])
            else:
                if state in [TaskState.RUNNING.value, TaskState.PENDING.value]:
                    result_lines.append("*No output yet (task still running)*")
                else:
                    result_lines.append("*No output produced*")

            result_text = "\n".join(result_lines)

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=result_text,
                metadata={
                    "task_id": task_id,
                    "task_state": state,
                    "exit_code": exit_code,
                    "duration": duration,
                    "output_length": len(output) if output else 0,
                    "blocked": block,
                    "timeout_used": timeout_seconds
                }
            )

        except Exception as e:
            logger.exception(f"Error retrieving output for task {task_id}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error retrieving task output: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        task_id = message.payload.get("task_id", "")
        block = message.payload.get("block", True)

        self.logger.debug(f"Retrieving output for task {task_id} (blocking: {block})")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            task_id = result.metadata.get("task_id")
            task_state = result.metadata.get("task_state")
            duration = result.metadata.get("duration", 0)

            self.logger.debug(
                f"Retrieved output for task {task_id}: {task_state} "
                f"(duration: {duration:.1f}s)"
            )


# Create singleton instance
task_output_tool = TaskOutputTool()