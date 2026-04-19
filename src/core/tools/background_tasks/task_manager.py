"""
Background Task Manager for DevMind.

Provides comprehensive background task execution, monitoring, and lifecycle
management with output capture and resource cleanup.
"""
import asyncio
import logging
import os
import signal
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union
import json

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """Background task execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class BackgroundTask:
    """Background task data model."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    command: Optional[str] = None
    description: str = ""
    state: TaskState = TaskState.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    exit_code: Optional[int] = None
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    timeout_seconds: Optional[int] = None
    process_pid: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization."""
        data = asdict(self)
        data['state'] = self.state.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackgroundTask':
        """Create task from dictionary."""
        if isinstance(data.get('state'), str):
            data['state'] = TaskState(data['state'])
        return cls(**data)

    @property
    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self.state == TaskState.RUNNING

    @property
    def is_finished(self) -> bool:
        """Check if task has finished (completed, failed, or cancelled)."""
        return self.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.TIMEOUT]

    @property
    def duration(self) -> float:
        """Get task duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        elif self.is_running:
            return time.time() - self.start_time
        else:
            return 0.0


class BackgroundTaskManager:
    """Manager for background task execution and monitoring."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize background task manager.

        Args:
            output_dir: Directory for task output files
        """
        self.tasks: Dict[str, BackgroundTask] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.output_dir = output_dir or Path("sessions/background_tasks")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Task cleanup settings
        self.max_completed_tasks = 100
        self.cleanup_interval = 300  # 5 minutes

        # Start cleanup task (will be started on first use)
        self._cleanup_task = None
        self._cleanup_started = False

    async def execute_background_command(
        self,
        command: str,
        description: str = "",
        timeout_seconds: Optional[int] = None,
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> str:
        """Execute a command in the background.

        Args:
            command: Command to execute
            description: Human-readable description
            timeout_seconds: Optional timeout
            working_dir: Working directory for command
            env: Environment variables

        Returns:
            Task ID for monitoring the background task
        """
        task = BackgroundTask(
            command=command,
            description=description,
            timeout_seconds=timeout_seconds,
            metadata={
                "working_dir": working_dir,
                "env": env
            }
        )

        # Create output file
        output_file = self.output_dir / f"task_{task.task_id}.out"
        task.output_file = str(output_file)

        # Store task
        self.tasks[task.task_id] = task

        # Ensure cleanup task is running
        self._start_cleanup_task()

        # Start the task asynchronously
        asyncio.create_task(self._run_background_task(task, working_dir, env))

        logger.info(f"Started background task {task.task_id}: {description}")
        return task.task_id

    async def _run_background_task(
        self,
        task: BackgroundTask,
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ):
        """Run a background task."""
        try:
            task.state = TaskState.RUNNING
            task.start_time = time.time()

            # Prepare environment
            task_env = os.environ.copy()
            if env:
                task_env.update(env)

            # Start process
            with open(task.output_file, 'w') as output_file:
                process = subprocess.Popen(
                    task.command,
                    shell=True,
                    stdout=output_file,
                    stderr=subprocess.STDOUT,
                    cwd=working_dir,
                    env=task_env,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )

                task.process_pid = process.pid
                self.processes[task.task_id] = process

                try:
                    # Wait for process with timeout
                    if task.timeout_seconds:
                        exit_code = await asyncio.wait_for(
                            self._wait_for_process(process),
                            timeout=task.timeout_seconds
                        )
                    else:
                        exit_code = await self._wait_for_process(process)

                    task.exit_code = exit_code
                    task.state = TaskState.COMPLETED if exit_code == 0 else TaskState.FAILED

                except asyncio.TimeoutError:
                    # Handle timeout
                    task.state = TaskState.TIMEOUT
                    task.error_message = f"Task timed out after {task.timeout_seconds} seconds"

                    # Kill the process
                    try:
                        if os.name != 'nt':
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        else:
                            process.terminate()
                        process.wait(timeout=5)
                    except:
                        try:
                            if os.name != 'nt':
                                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            else:
                                process.kill()
                        except:
                            pass

        except Exception as e:
            task.state = TaskState.FAILED
            task.error_message = str(e)
            logger.exception(f"Background task {task.task_id} failed")

        finally:
            task.end_time = time.time()

            # Clean up process reference
            if task.task_id in self.processes:
                del self.processes[task.task_id]

            logger.info(
                f"Background task {task.task_id} finished: {task.state.value} "
                f"(duration: {task.duration:.1f}s)"
            )

    async def _wait_for_process(self, process: subprocess.Popen) -> int:
        """Wait for process to complete."""
        while process.poll() is None:
            await asyncio.sleep(0.1)
        return process.returncode

    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def list_tasks(self, state_filter: Optional[TaskState] = None) -> List[BackgroundTask]:
        """List all tasks, optionally filtered by state."""
        tasks = list(self.tasks.values())
        if state_filter:
            tasks = [task for task in tasks if task.state == state_filter]
        return sorted(tasks, key=lambda t: t.start_time, reverse=True)

    async def get_task_output(
        self,
        task_id: str,
        block: bool = True,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Get output from a task.

        Args:
            task_id: Task ID
            block: Whether to wait for completion
            timeout: Maximum wait time

        Returns:
            Dictionary with task status and output
        """
        task = self.get_task(task_id)
        if not task:
            return {
                "success": False,
                "error": f"Task {task_id} not found",
                "state": None,
                "output": "",
                "task_info": None
            }

        # If blocking, wait for completion
        if block and not task.is_finished:
            start_wait = time.time()
            while not task.is_finished and (time.time() - start_wait) < timeout:
                await asyncio.sleep(0.5)

            if not task.is_finished:
                return {
                    "success": False,
                    "error": f"Task {task_id} did not complete within {timeout} seconds",
                    "state": task.state.value,
                    "output": "",
                    "task_info": task.to_dict()
                }

        # Read output file
        output = ""
        if task.output_file and os.path.exists(task.output_file):
            try:
                with open(task.output_file, 'r') as f:
                    output = f.read()
            except Exception as e:
                logger.error(f"Error reading output file for task {task_id}: {e}")

        return {
            "success": True,
            "state": task.state.value,
            "output": output,
            "exit_code": task.exit_code,
            "duration": task.duration,
            "error_message": task.error_message,
            "task_info": task.to_dict()
        }

    async def stop_task(self, task_id: str) -> bool:
        """Stop a running task.

        Args:
            task_id: Task ID to stop

        Returns:
            True if task was stopped, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            logger.warning(f"Cannot stop task {task_id}: task not found")
            return False

        if not task.is_running:
            logger.info(f"Task {task_id} is not running (state: {task.state.value})")
            return False

        # Get process
        process = self.processes.get(task_id)
        if not process:
            logger.warning(f"No process found for running task {task_id}")
            return False

        try:
            # Terminate process
            if os.name != 'nt':
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()

            # Wait for graceful termination
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()

            # Update task state
            task.state = TaskState.CANCELLED
            task.end_time = time.time()
            task.error_message = "Task cancelled by user"

            logger.info(f"Successfully stopped task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping task {task_id}: {e}")
            return False

    def _start_cleanup_task(self):
        """Start the cleanup background task."""
        if self._cleanup_started:
            return

        try:
            # Only start if we have a running event loop
            loop = asyncio.get_running_loop()
            if self._cleanup_task and not self._cleanup_task.done():
                return

            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._cleanup_started = True
        except RuntimeError:
            # No event loop running, will start later
            pass

    async def _cleanup_loop(self):
        """Background cleanup task."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_old_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    async def _cleanup_old_tasks(self):
        """Clean up old completed tasks."""
        completed_tasks = [
            task for task in self.tasks.values()
            if task.is_finished
        ]

        if len(completed_tasks) > self.max_completed_tasks:
            # Sort by end time and remove oldest
            completed_tasks.sort(key=lambda t: t.end_time or 0)
            tasks_to_remove = completed_tasks[:-self.max_completed_tasks]

            for task in tasks_to_remove:
                # Remove output file
                if task.output_file and os.path.exists(task.output_file):
                    try:
                        os.unlink(task.output_file)
                    except Exception as e:
                        logger.warning(f"Could not remove output file {task.output_file}: {e}")

                # Remove from memory
                if task.task_id in self.tasks:
                    del self.tasks[task.task_id]

            logger.info(f"Cleaned up {len(tasks_to_remove)} old background tasks")

    async def shutdown(self):
        """Shutdown the background task manager."""
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Stop all running tasks
        running_tasks = [task for task in self.tasks.values() if task.is_running]
        for task in running_tasks:
            await self.stop_task(task.task_id)

        logger.info("Background task manager shutdown complete")


# Global background task manager instance
_background_task_manager = None


def get_background_task_manager() -> BackgroundTaskManager:
    """Get the global background task manager instance."""
    global _background_task_manager
    if _background_task_manager is None:
        _background_task_manager = BackgroundTaskManager()
    return _background_task_manager