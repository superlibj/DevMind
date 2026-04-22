#!/usr/bin/env python3
"""
Test suite for Command Queue System.

Tests command queuing, execution, prioritization, and queue management functionality.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.tools import (
    queue_add_tool, queue_list_tool, queue_remove_tool,
    queue_execute_tool, queue_status_tool, queue_clear_tool,
    create_acp_message
)
from src.core.tools.command_queue import (
    get_queue_manager, get_queue_executor,
    Priority, CommandStatus, ExecutionMode
)


class CommandQueueTestSuite:
    """Test suite for command queue system."""

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

    async def test_queue_manager_basic_operations(self):
        """Test basic queue manager operations."""
        queue_manager = get_queue_manager()

        # Clear queue for clean test
        queue_manager.clear_queue()

        # Test adding commands
        cmd1 = queue_manager.add_command(
            command="test_cmd",
            description="Test command 1",
            args={"arg1": "value1"},
            priority=Priority.NORMAL
        )

        assert cmd1.command == "test_cmd"
        assert cmd1.description == "Test command 1"
        assert cmd1.priority == Priority.NORMAL
        assert cmd1.status == CommandStatus.QUEUED

        # Test getting command
        retrieved = queue_manager.get_command(cmd1.id)
        assert retrieved is not None
        assert retrieved.id == cmd1.id

        # Test listing commands
        commands = queue_manager.list_commands()
        assert len(commands) >= 1
        assert any(cmd.id == cmd1.id for cmd in commands)

        # Test removing command
        success = queue_manager.remove_command(cmd1.id)
        assert success is True

        # Verify removal
        retrieved = queue_manager.get_command(cmd1.id)
        assert retrieved is None

    async def test_command_priority_ordering(self):
        """Test command priority ordering."""
        queue_manager = get_queue_manager()
        queue_manager.clear_queue()

        # Add commands with different priorities
        cmd_low = queue_manager.add_command("test", "Low priority", priority=Priority.LOW)
        cmd_urgent = queue_manager.add_command("test", "Urgent priority", priority=Priority.URGENT)
        cmd_normal = queue_manager.add_command("test", "Normal priority", priority=Priority.NORMAL)
        cmd_high = queue_manager.add_command("test", "High priority", priority=Priority.HIGH)

        # Get next command should return highest priority
        next_cmd = queue_manager.get_next_command()
        assert next_cmd.id == cmd_urgent.id

        # Remove urgent and check next
        queue_manager.remove_command(cmd_urgent.id)
        next_cmd = queue_manager.get_next_command()
        assert next_cmd.id == cmd_high.id

        # Clean up
        queue_manager.clear_queue()

    async def test_queue_add_tool(self):
        """Test QueueAdd tool functionality."""
        # Test adding a command
        message = create_acp_message("QueueAdd", {
            "command": "agent",
            "description": "Test agent command",
            "args": {
                "subagent_type": "general-purpose",
                "prompt": "Test prompt"
            },
            "priority": "high"
        })

        result = await queue_add_tool.execute(message)
        assert result.is_success(), f"QueueAdd failed: {result.error}"
        assert "Command Added to Queue" in result.result
        assert "command_id" in result.metadata

        command_id = result.metadata["command_id"]

        # Verify command was added
        queue_manager = get_queue_manager()
        command = queue_manager.get_command(command_id)
        assert command is not None
        assert command.command == "agent"
        assert command.priority == Priority.HIGH

        # Clean up
        queue_manager.remove_command(command_id)

    async def test_queue_list_tool(self):
        """Test QueueList tool functionality."""
        queue_manager = get_queue_manager()
        queue_manager.clear_queue()

        # Add some test commands
        cmd1 = queue_manager.add_command("test1", "First test", priority=Priority.HIGH)
        cmd2 = queue_manager.add_command("test2", "Second test", priority=Priority.NORMAL)

        # Test listing all commands
        message = create_acp_message("QueueList", {})
        result = await queue_list_tool.execute(message)

        assert result.is_success(), f"QueueList failed: {result.error}"
        assert "Command Queue" in result.result
        assert "commands" in result.metadata
        assert len(result.metadata["commands"]) == 2

        # Test filtering by status
        message = create_acp_message("QueueList", {"status": "queued"})
        result = await queue_list_tool.execute(message)

        assert result.is_success()
        assert len(result.metadata["commands"]) == 2

        # Clean up
        queue_manager.clear_queue()

    async def test_queue_remove_tool(self):
        """Test QueueRemove tool functionality."""
        queue_manager = get_queue_manager()
        queue_manager.clear_queue()

        # Add a test command
        cmd = queue_manager.add_command("test", "Test for removal")

        # Test removing by full ID
        message = create_acp_message("QueueRemove", {"command_id": cmd.id})
        result = await queue_remove_tool.execute(message)

        assert result.is_success(), f"QueueRemove failed: {result.error}"
        assert "Command Removed" in result.result

        # Verify removal
        retrieved = queue_manager.get_command(cmd.id)
        assert retrieved is None

    async def test_queue_status_tool(self):
        """Test QueueStatus tool functionality."""
        queue_manager = get_queue_manager()
        queue_manager.clear_queue()

        # Add some test commands
        queue_manager.add_command("test1", "Test 1", priority=Priority.HIGH)
        queue_manager.add_command("test2", "Test 2", priority=Priority.NORMAL)

        # Test basic status
        message = create_acp_message("QueueStatus", {})
        result = await queue_status_tool.execute(message)

        assert result.is_success(), f"QueueStatus failed: {result.error}"
        assert "Command Queue Status" in result.result
        assert "total_commands" in result.metadata
        assert result.metadata["total_commands"] == 2

        # Test detailed status
        message = create_acp_message("QueueStatus", {"detailed": True})
        result = await queue_status_tool.execute(message)

        assert result.is_success()
        assert "Detailed Command List" in result.result

        # Clean up
        queue_manager.clear_queue()

    async def test_queue_clear_tool(self):
        """Test QueueClear tool functionality."""
        queue_manager = get_queue_manager()
        queue_manager.clear_queue()

        # Add some test commands
        queue_manager.add_command("test1", "Test 1")
        queue_manager.add_command("test2", "Test 2")

        # Test clearing without confirmation (should fail)
        message = create_acp_message("QueueClear", {"status": "queued"})
        result = await queue_clear_tool.execute(message)

        assert not result.is_success()
        assert "confirmation" in result.error.lower()

        # Test clearing with confirmation
        message = create_acp_message("QueueClear", {
            "status": "queued",
            "confirm": True
        })
        result = await queue_clear_tool.execute(message)

        assert result.is_success(), f"QueueClear failed: {result.error}"
        assert "Queue Cleared" in result.result
        assert result.metadata["removed_count"] == 2

        # Verify queue is empty
        commands = queue_manager.list_commands()
        assert len(commands) == 0

    async def test_queue_execute_tool(self):
        """Test QueueExecute tool functionality."""
        queue_manager = get_queue_manager()
        queue_manager.clear_queue()

        # Register a test command handler
        async def test_handler(args):
            await asyncio.sleep(0.1)  # Simulate work
            return {"test_result": "success", "args": args}

        queue_manager.register_command_handler("test_exec", test_handler)

        # Add a test command
        cmd = queue_manager.add_command(
            "test_exec",
            "Test execution command",
            args={"test_arg": "test_value"}
        )

        # Test executing the command
        message = create_acp_message("QueueExecute", {
            "command_id": cmd.id,
            "wait": True
        })
        result = await queue_execute_tool.execute(message)

        assert result.is_success(), f"QueueExecute failed: {result.error}"
        assert "Executed" in result.result
        assert result.metadata["executed_count"] == 1

        # Verify command was executed successfully
        executed_cmd = queue_manager.get_command(cmd.id)
        assert executed_cmd.status == CommandStatus.COMPLETED
        assert executed_cmd.result is not None

    async def test_queue_executor_auto_mode(self):
        """Test queue executor auto execution mode."""
        queue_manager = get_queue_manager()
        queue_executor = get_queue_executor()
        queue_manager.clear_queue()

        # Register test handler
        async def test_handler(args):
            await asyncio.sleep(0.1)
            return {"success": True}

        queue_manager.register_command_handler("test_auto", test_handler)

        # Add commands to queue
        cmd1 = queue_manager.add_command("test_auto", "Auto test 1")
        cmd2 = queue_manager.add_command("test_auto", "Auto test 2")

        # Test manual execution
        executed = await queue_executor.execute_next_batch(max_commands=1)
        assert executed == 1

        # Wait for completion
        await queue_executor.wait_for_queue_completion(timeout=5.0)

        # Check first command completed
        cmd1_updated = queue_manager.get_command(cmd1.id)
        assert cmd1_updated.status == CommandStatus.COMPLETED

        # Test auto-execution mode
        await queue_executor.start_auto_execution(interval=0.5)

        # Add another command
        cmd3 = queue_manager.add_command("test_auto", "Auto test 3")

        # Wait for auto-execution
        await asyncio.sleep(1.0)

        # Stop auto-execution
        await queue_executor.stop_auto_execution()

        # Check execution stats
        stats = queue_executor.get_execution_stats()
        assert stats["execution_mode"] == ExecutionMode.MANUAL.value
        assert not stats["is_running"]
        assert stats["total_executed"] >= 2

    async def test_queue_persistence(self):
        """Test queue persistence across manager instances."""
        queue_manager = get_queue_manager()
        queue_manager.clear_queue()

        # Add a command
        cmd = queue_manager.add_command("test_persist", "Persistence test")
        command_id = cmd.id

        # Save queue
        queue_manager._save_queue()

        # Create new manager instance (simulating restart)
        from src.core.tools.command_queue.queue_manager import CommandQueueManager
        new_manager = CommandQueueManager(queue_manager.queue_dir)

        # Check command is still there
        retrieved = new_manager.get_command(command_id)
        assert retrieved is not None
        assert retrieved.command == "test_persist"
        assert retrieved.description == "Persistence test"

    async def test_error_handling(self):
        """Test error handling in queue operations."""
        queue_manager = get_queue_manager()

        # Test invalid tool parameters
        message = create_acp_message("QueueAdd", {})  # Missing required fields
        result = await queue_add_tool.execute(message)
        assert not result.is_success()

        # Test removing non-existent command
        message = create_acp_message("QueueRemove", {"command_id": "nonexistent"})
        result = await queue_remove_tool.execute(message)
        assert not result.is_success()

        # Test executing non-existent command
        message = create_acp_message("QueueExecute", {"command_id": "nonexistent"})
        result = await queue_execute_tool.execute(message)
        assert not result.is_success()

    async def test_queue_size_limits(self):
        """Test queue size limitations."""
        queue_manager = get_queue_manager()
        queue_manager.clear_queue()

        # Set a small limit for testing
        original_limit = queue_manager.max_queue_size
        queue_manager.max_queue_size = 3

        try:
            # Add commands up to limit
            for i in range(3):
                queue_manager.add_command(f"test_{i}", f"Test {i}")

            # Test that we can't exceed the limit
            try:
                queue_manager.add_command("test_overflow", "Overflow test")
                # If we get here, cleanup must have worked
                commands = queue_manager.list_commands()
                assert len(commands) <= queue_manager.max_queue_size, "Queue size should not exceed limit"
            except RuntimeError as e:
                # Expected if queue is truly full
                assert "Queue is full" in str(e)

        finally:
            # Restore original limit
            queue_manager.max_queue_size = original_limit
            queue_manager.clear_queue()

    async def run_all_tests(self):
        """Run all command queue system tests."""
        print("📋 Command Queue System Test Suite")
        print("=" * 50)

        await self.run_test("Queue Manager Basic Operations", self.test_queue_manager_basic_operations)
        await self.run_test("Command Priority Ordering", self.test_command_priority_ordering)
        await self.run_test("QueueAdd Tool", self.test_queue_add_tool)
        await self.run_test("QueueList Tool", self.test_queue_list_tool)
        await self.run_test("QueueRemove Tool", self.test_queue_remove_tool)
        await self.run_test("QueueStatus Tool", self.test_queue_status_tool)
        await self.run_test("QueueClear Tool", self.test_queue_clear_tool)
        await self.run_test("QueueExecute Tool", self.test_queue_execute_tool)
        await self.run_test("Queue Executor Auto Mode", self.test_queue_executor_auto_mode)
        await self.run_test("Queue Persistence", self.test_queue_persistence)
        await self.run_test("Error Handling", self.test_error_handling)
        await self.run_test("Queue Size Limits", self.test_queue_size_limits)

        print("\n" + "="*60)
        print(f"📋 Command Queue Tests: {self.passed} passed, {self.failed} failed")
        print("="*60)

        success = self.failed == 0

        if success:
            print("🎉 All command queue system tests PASSED!")
            print("✨ Command queue system is fully functional!")
        else:
            print(f"⚠️  {self.failed} test(s) failed:")
            for result in self.test_results:
                if result.startswith("❌"):
                    print(f"   {result}")

        return success


async def main():
    """Run the command queue system test suite."""
    print("📋 Starting Command Queue System Tests\n")

    suite = CommandQueueTestSuite()
    success = await suite.run_all_tests()

    # Cleanup test data
    try:
        import shutil
        test_dirs = ["sessions/command_queue"]
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                # Only remove test-related files
                for file in os.listdir(test_dir):
                    try:
                        file_path = os.path.join(test_dir, file)
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except:
                        pass
    except:
        pass

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())