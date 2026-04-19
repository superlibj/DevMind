#!/usr/bin/env python3
"""
Test suite for background task management system.

Tests background task execution, monitoring, and management capabilities.
"""
import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.tools import (
    bash_tool, task_output_tool, task_stop_tool,
    create_acp_message
)
from src.core.tools.background_tasks.task_manager import get_background_task_manager


class BackgroundTaskTestSuite:
    """Test suite for background task functionality."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_results = []

    async def run_test(self, test_name: str, test_func):
        """Run a single test."""
        print(f"Testing {test_name}...", end=" ")
        try:
            await test_func()
            print("✅ PASSED")
            self.passed += 1
            self.test_results.append(f"✅ {test_name}")
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.failed += 1
            self.test_results.append(f"❌ {test_name}: {str(e)}")

    async def test_background_command_execution(self):
        """Test basic background command execution."""
        # Start a background task
        message = create_acp_message("Bash", {
            "command": "echo 'Background test' && sleep 2 && echo 'Background complete'",
            "description": "Test background execution",
            "run_in_background": True
        })

        result = await bash_tool.execute(message)
        assert result.is_success(), f"Failed to start background task: {result.error}"
        assert "task started" in result.result.lower(), "Background task not started"

        task_id = result.metadata.get("task_id")
        assert task_id, "Task ID not returned"

        return task_id

    async def test_task_output_non_blocking(self):
        """Test non-blocking task output retrieval."""
        # Start a task first
        task_id = await self.test_background_command_execution()

        # Get non-blocking output
        message = create_acp_message("TaskOutput", {
            "task_id": task_id,
            "block": False,
            "timeout": 1000
        })

        result = await task_output_tool.execute(message)
        assert result.is_success(), f"Failed to get task output: {result.error}"
        assert task_id in result.result, "Task ID not in result"

    async def test_task_output_blocking(self):
        """Test blocking task output retrieval."""
        # Start a short task
        message = create_acp_message("Bash", {
            "command": "echo 'Quick task' && sleep 1",
            "description": "Quick background task",
            "run_in_background": True
        })

        result = await bash_tool.execute(message)
        assert result.is_success(), f"Failed to start task: {result.error}"

        task_id = result.metadata.get("task_id")
        assert task_id, "Task ID not returned"

        # Wait for completion
        message = create_acp_message("TaskOutput", {
            "task_id": task_id,
            "block": True,
            "timeout": 5000
        })

        result = await task_output_tool.execute(message)
        assert result.is_success(), f"Failed to get blocking output: {result.error}"
        assert "Quick task" in result.result, "Task output not found"

    async def test_task_stopping(self):
        """Test stopping a running background task."""
        # Start a long-running task
        message = create_acp_message("Bash", {
            "command": "sleep 10 && echo 'Should not see this'",
            "description": "Long running task for stop test",
            "run_in_background": True
        })

        result = await bash_tool.execute(message)
        assert result.is_success(), f"Failed to start long task: {result.error}"

        task_id = result.metadata.get("task_id")
        assert task_id, "Task ID not returned"

        # Give it a moment to start
        await asyncio.sleep(0.5)

        # Stop the task
        message = create_acp_message("TaskStop", {"task_id": task_id})
        result = await task_stop_tool.execute(message)
        assert result.is_success(), f"Failed to stop task: {result.error}"
        assert "stopped" in result.result.lower(), "Task stop confirmation not found"

    async def test_task_manager_functionality(self):
        """Test background task manager directly."""
        task_manager = get_background_task_manager()

        # Execute a background command
        task_id = await task_manager.execute_background_command(
            command="echo 'Direct manager test' && sleep 1",
            description="Direct manager test",
            timeout_seconds=10
        )

        assert task_id, "Task ID not returned"

        # Get task
        task = task_manager.get_task(task_id)
        assert task, "Task not found in manager"
        assert task.command, "Task command not set"
        assert task.description == "Direct manager test", "Task description mismatch"

        # Wait for completion
        output = await task_manager.get_task_output(task_id, block=True, timeout=5.0)
        assert output["success"], "Failed to get task output"
        assert "Direct manager test" in output["output"], "Task output not found"

    async def test_error_handling(self):
        """Test error handling for invalid operations."""
        # Test getting output from non-existent task
        message = create_acp_message("TaskOutput", {
            "task_id": "non-existent-task",
            "block": False,
            "timeout": 1000
        })

        result = await task_output_tool.execute(message)
        assert not result.is_success(), "Should fail for non-existent task"
        assert "not found" in result.error.lower(), "Error message should mention 'not found'"

        # Test stopping non-existent task
        message = create_acp_message("TaskStop", {"task_id": "non-existent-task"})
        result = await task_stop_tool.execute(message)
        assert not result.is_success(), "Should fail for non-existent task"

    async def run_all_tests(self):
        """Run all background task tests."""
        print("🧪 Background Task Management Test Suite")
        print("=" * 50)

        await self.run_test("Background Command Execution", self.test_background_command_execution)
        await self.run_test("Non-blocking Task Output", self.test_task_output_non_blocking)
        await self.run_test("Blocking Task Output", self.test_task_output_blocking)
        await self.run_test("Task Stopping", self.test_task_stopping)
        await self.run_test("Task Manager Functionality", self.test_task_manager_functionality)
        await self.run_test("Error Handling", self.test_error_handling)

        print("\n" + "="*60)
        print(f"📊 Background Task Tests: {self.passed} passed, {self.failed} failed")
        print("="*60)

        success = self.failed == 0

        if success:
            print("🎉 All background task tests PASSED!")
            print("✨ Background task management system is fully functional!")
        else:
            print(f"⚠️  {self.failed} test(s) failed:")
            for result in self.test_results:
                if result.startswith("❌"):
                    print(f"   {result}")

        return success


async def main():
    """Run the background task test suite."""
    print("🧪 Starting Background Task Management Tests\n")

    suite = BackgroundTaskTestSuite()
    success = await suite.run_all_tests()

    # Cleanup - stop any remaining tasks
    try:
        task_manager = get_background_task_manager()
        running_tasks = task_manager.list_tasks()
        for task in running_tasks:
            if task.is_running:
                await task_manager.stop_task(task.task_id)
        await task_manager.shutdown()
    except:
        pass

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())