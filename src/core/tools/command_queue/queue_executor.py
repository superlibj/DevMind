"""
Queue Executor for DevMind Command Queue System.

Handles automatic queue processing and execution management.
"""
import asyncio
import logging
import time
from enum import Enum
from typing import Optional, Set

from .queue_manager import get_queue_manager, CommandStatus

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Queue execution modes."""
    MANUAL = "manual"
    AUTO = "auto"
    SCHEDULED = "scheduled"


class QueueExecutor:
    """Handles automatic queue execution and processing."""

    def __init__(self):
        """Initialize queue executor."""
        self.queue_manager = get_queue_manager()
        self.execution_mode = ExecutionMode.MANUAL

        # Auto-execution settings
        self.auto_execution_task: Optional[asyncio.Task] = None
        self.auto_execution_interval = 5.0  # seconds
        self.is_running = False

        # Execution statistics
        self.total_executed = 0
        self.total_failed = 0
        self.last_execution_time = 0.0

        # Monitoring
        self.execution_callbacks: Set[callable] = set()

    async def start_auto_execution(self, interval: float = 5.0):
        """Start automatic queue execution.

        Args:
            interval: Execution interval in seconds
        """
        if self.is_running:
            logger.warning("Auto-execution is already running")
            return

        self.execution_mode = ExecutionMode.AUTO
        self.auto_execution_interval = interval
        self.is_running = True

        # Update queue manager setting
        self.queue_manager.auto_execute = True
        self.queue_manager._save_queue()

        # Start background task
        self.auto_execution_task = asyncio.create_task(self._auto_execution_loop())
        logger.info(f"Started auto-execution with {interval}s interval")

    async def stop_auto_execution(self):
        """Stop automatic queue execution."""
        if not self.is_running:
            return

        self.is_running = False
        self.execution_mode = ExecutionMode.MANUAL

        # Update queue manager setting
        self.queue_manager.auto_execute = False
        self.queue_manager._save_queue()

        # Cancel background task
        if self.auto_execution_task:
            self.auto_execution_task.cancel()
            try:
                await self.auto_execution_task
            except asyncio.CancelledError:
                pass
            self.auto_execution_task = None

        logger.info("Stopped auto-execution")

    async def execute_next_batch(self, max_commands: int = None) -> int:
        """Execute the next batch of commands from the queue.

        Args:
            max_commands: Maximum number of commands to execute

        Returns:
            Number of commands started
        """
        if max_commands is None:
            max_commands = self.queue_manager.max_concurrent_commands

        executed_count = 0

        # Check how many commands we can start
        current_running = len(self.queue_manager.running_commands)
        available_slots = self.queue_manager.max_concurrent_commands - current_running

        if available_slots <= 0:
            return 0

        # Execute up to available slots
        max_to_start = min(max_commands, available_slots)

        for _ in range(max_to_start):
            next_command = self.queue_manager.get_next_command()
            if not next_command:
                break

            success = await self.queue_manager.execute_command(next_command.id)
            if success:
                executed_count += 1
                self.total_executed += 1
                self.last_execution_time = time.time()

                # Notify callbacks
                await self._notify_execution_started(next_command)
            else:
                self.total_failed += 1
                break

        return executed_count

    async def wait_for_queue_completion(self, timeout: Optional[float] = None):
        """Wait for all running commands to complete.

        Args:
            timeout: Maximum time to wait in seconds
        """
        start_time = time.time()

        while self.queue_manager.running_commands:
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError(f"Queue completion timeout after {timeout}s")

            await asyncio.sleep(0.5)

    async def process_queue_until_empty(self, max_total_commands: int = 50):
        """Process the entire queue until empty or limit reached.

        Args:
            max_total_commands: Maximum total commands to process
        """
        processed = 0

        while processed < max_total_commands:
            # Execute next batch
            started = await self.execute_next_batch()
            if started == 0:
                # No more commands to start, wait for current to finish
                if not self.queue_manager.running_commands:
                    break
                await asyncio.sleep(1.0)
                continue

            processed += started

            # Brief pause between batches
            await asyncio.sleep(0.1)

        logger.info(f"Processed {processed} commands from queue")

    def add_execution_callback(self, callback: callable):
        """Add callback for execution events.

        Args:
            callback: Async function called when command execution starts
        """
        self.execution_callbacks.add(callback)

    def remove_execution_callback(self, callback: callable):
        """Remove execution callback."""
        self.execution_callbacks.discard(callback)

    def get_execution_stats(self) -> dict:
        """Get execution statistics.

        Returns:
            Dictionary with execution stats
        """
        return {
            "execution_mode": self.execution_mode.value,
            "is_running": self.is_running,
            "auto_execution_interval": self.auto_execution_interval,
            "total_executed": self.total_executed,
            "total_failed": self.total_failed,
            "last_execution_time": self.last_execution_time,
            "current_running": len(self.queue_manager.running_commands),
            "queue_size": len([
                cmd for cmd in self.queue_manager.commands.values()
                if cmd.status == CommandStatus.QUEUED
            ])
        }

    async def _auto_execution_loop(self):
        """Main auto-execution loop."""
        logger.info("Auto-execution loop started")

        try:
            while self.is_running:
                try:
                    # Execute next batch if there's capacity
                    await self.execute_next_batch()

                    # Wait for next interval
                    await asyncio.sleep(self.auto_execution_interval)

                except Exception as e:
                    logger.error(f"Error in auto-execution loop: {e}")
                    await asyncio.sleep(5.0)  # Error recovery delay

        except asyncio.CancelledError:
            logger.info("Auto-execution loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Auto-execution loop failed: {e}")
        finally:
            self.is_running = False
            logger.info("Auto-execution loop stopped")

    async def _notify_execution_started(self, command):
        """Notify callbacks that command execution started."""
        for callback in self.execution_callbacks.copy():
            try:
                await callback(command)
            except Exception as e:
                logger.error(f"Error in execution callback: {e}")

    # Context manager support for auto-execution
    async def __aenter__(self):
        """Enter context manager."""
        await self.start_auto_execution()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        await self.stop_auto_execution()


# Global queue executor instance
_queue_executor = None


def get_queue_executor() -> QueueExecutor:
    """Get the global queue executor instance."""
    global _queue_executor
    if _queue_executor is None:
        _queue_executor = QueueExecutor()
    return _queue_executor