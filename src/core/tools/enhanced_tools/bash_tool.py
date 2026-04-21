"""
Enhanced Bash tool for secure command execution.

Provides safe shell command execution with timeout, description requirements,
and comprehensive security controls.
"""
import asyncio
import logging
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType
from ..background_tasks.task_manager import get_background_task_manager

logger = logging.getLogger(__name__)


class BashTool(ACPTool):
    """Enhanced Bash tool for secure command execution."""

    def __init__(self):
        """Initialize Bash tool."""
        spec = ACPToolSpec(
            name="Bash",
            description="Executes shell commands with security controls and timeout",
            version="1.0.0",
            parameters={
                "required": ["command"],
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute"
                    },
                    "description": {
                        "type": "string",
                        "description": "Clear, concise description of what this command does in active voice"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Optional timeout in milliseconds (max 600000)",
                        "maximum": 600000,
                        "minimum": 0
                    },
                    "run_in_background": {
                        "type": "boolean",
                        "description": "Set to true to run this command in the background",
                        "default": False
                    },
                    "dangerouslyDisableSandbox": {
                        "type": "boolean",
                        "description": "Set to true to dangerously override sandbox mode",
                        "default": False
                    }
                }
            },
            security_level="critical",  # Command execution is highest risk
            timeout_seconds=120,  # Default 2 minute timeout
            requires_confirmation=True
        )
        super().__init__(spec)

        # Commands that are dangerous and require extra confirmation
        self.dangerous_commands = {
            'rm', 'rmdir', 'del', 'delete', 'format', 'fdisk',
            'dd', 'sudo', 'su', 'passwd', 'chown', 'chmod',
            'reboot', 'shutdown', 'halt', 'poweroff', 'init'
        }

        # Commands that are generally safe for development
        self.safe_commands = {
            'ls', 'dir', 'pwd', 'cd', 'cat', 'head', 'tail',
            'echo', 'grep', 'find', 'which', 'where', 'whoami',
            'git', 'npm', 'pip', 'python', 'node', 'java',
            'make', 'cmake', 'gcc', 'javac', 'rustc'
        }

    def _extract_payload_params(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from payload, handling both direct and nested input formats."""
        # Handle nested input format: {"input": {"command": "..."}}
        if "input" in payload and isinstance(payload["input"], dict):
            return payload["input"]
        # Handle direct format: {"command": "..."}
        return payload

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the bash command request."""
        payload = message.payload
        params = self._extract_payload_params(payload)

        if not params.get("command"):
            return "command is required"

        command = params["command"].strip()
        if not command:
            return "command cannot be empty"

        # Basic command validation
        try:
            # Parse command to extract the base command
            parsed = shlex.split(command)
            if not parsed:
                return "invalid command format"

            base_command = parsed[0]

            # Check for dangerous commands
            if any(dangerous in base_command.lower() for dangerous in self.dangerous_commands):
                if not payload.get("dangerouslyDisableSandbox", False):
                    return f"Potentially dangerous command detected: {base_command}. " \
                           f"Use dangerouslyDisableSandbox=true if you really need to run this."

            # Validate timeout
            timeout = payload.get("timeout")
            if timeout is not None:
                if not isinstance(timeout, (int, float)) or timeout < 0:
                    return "timeout must be a non-negative number"
                if timeout > 600000:  # 10 minutes max
                    return "timeout cannot exceed 600000ms (10 minutes)"

        except ValueError as e:
            return f"Invalid command format: {str(e)}"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the bash command."""
        payload = message.payload
        params = self._extract_payload_params(payload)

        command = params["command"]
        timeout_ms = params.get("timeout", 120000)  # Default 2 minutes
        run_in_background = params.get("run_in_background", False)
        description = params.get("description", "")

        timeout_seconds = timeout_ms / 1000 if timeout_ms else 120

        try:
            start_time = time.time()

            # If background execution requested
            if run_in_background:
                return await self._execute_background(command, description, timeout_seconds)

            # Execute command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(),
                env=os.environ.copy()
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Command timed out after {timeout_seconds}s",
                    execution_time=time.time() - start_time
                )

            execution_time = time.time() - start_time

            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""

            # Determine status based on exit code
            status = ACPStatus.COMPLETED if process.returncode == 0 else ACPStatus.FAILED

            result_text = stdout_text
            if stderr_text and process.returncode != 0:
                result_text = f"{stdout_text}\nSTDERR:\n{stderr_text}" if stdout_text else stderr_text

            return ACPToolResult(
                status=status,
                result=result_text or "(no output)",
                error=stderr_text if process.returncode != 0 else None,
                stdout=stdout_text,
                stderr=stderr_text,
                exit_code=process.returncode,
                execution_time=execution_time,
                metadata={
                    "command": command,
                    "description": description,
                    "timeout_seconds": timeout_seconds,
                    "working_directory": os.getcwd()
                }
            )

        except FileNotFoundError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Command not found or shell not available"
            )
        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Permission denied executing command"
            )
        except Exception as e:
            logger.exception(f"Error executing command: {command}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error executing command: {str(e)}"
            )

    async def _execute_background(
        self,
        command: str,
        description: str,
        timeout_seconds: float
    ) -> ACPToolResult:
        """Execute command in background and return task information."""
        try:
            # Get background task manager
            task_manager = get_background_task_manager()

            # Execute command in background
            task_id = await task_manager.execute_background_command(
                command=command,
                description=description or f"Background execution: {command[:50]}...",
                timeout_seconds=int(timeout_seconds) if timeout_seconds else None,
                working_dir=os.getcwd(),
                env=os.environ.copy()
            )

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=f"✅ Background task started: {task_id}\n\n"
                       f"**Command:** {command}\n"
                       f"**Description:** {description or 'No description'}\n"
                       f"**Task ID:** {task_id}\n\n"
                       f"Use TaskOutput tool to check progress and get output:\n"
                       f"• Non-blocking check: TaskOutput(task_id=\"{task_id}\", block=false)\n"
                       f"• Wait for completion: TaskOutput(task_id=\"{task_id}\", block=true)",
                metadata={
                    "action": "background_started",
                    "task_id": task_id,
                    "command": command,
                    "description": description,
                    "timeout_seconds": timeout_seconds
                }
            )

        except Exception as e:
            logger.exception(f"Error starting background command: {command}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to start background command: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        command = message.payload.get("command", "")
        description = message.payload.get("description", "")

        if description:
            self.logger.info(f"Executing: {description}")
        else:
            # Log command but truncate if too long
            log_command = command if len(command) <= 100 else command[:97] + "..."
            self.logger.info(f"Executing command: {log_command}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            exec_time = result.execution_time
            exit_code = result.exit_code
            self.logger.debug(f"Command completed in {exec_time:.2f}s with exit code {exit_code}")
        else:
            self.logger.warning(f"Command failed: {result.error}")


# Create singleton instance
bash_tool = BashTool()