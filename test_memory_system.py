#!/usr/bin/env python3
"""
Test suite for memory and session management system.

Tests memory persistence, session management, and auto-memory functionality.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.tools import (
    auto_memory_tool,
    create_acp_message
)
from src.core.tools.memory_system.memory_manager import get_memory_manager, MemoryTopic
from src.core.tools.memory_system.session_manager import get_session_manager


class MemorySystemTestSuite:
    """Test suite for memory and session management."""

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

    async def test_memory_manager_basic_operations(self):
        """Test basic memory manager operations."""
        memory_manager = get_memory_manager()

        # Add a memory
        entry = memory_manager.add_memory(
            content="Test pattern: Always use descriptive variable names",
            topic=MemoryTopic.PATTERNS,
            priority=2,
            tags={"coding", "best-practices"},
            verified=True
        )

        assert entry.content == "Test pattern: Always use descriptive variable names"
        assert entry.topic == MemoryTopic.PATTERNS
        assert entry.priority == 2
        assert "coding" in entry.tags

        # Search for the memory
        results = memory_manager.search_memories("descriptive variable names")
        assert len(results) > 0
        assert any("descriptive variable names" in r.content for r in results)

        # Get topic memories
        pattern_memories = memory_manager.get_topic_memories(MemoryTopic.PATTERNS)
        assert any("descriptive variable names" in m.content for m in pattern_memories)

    async def test_auto_memory_tool_save_and_search(self):
        """Test auto memory tool save and search operations."""
        # Save a memory
        message = create_acp_message("AutoMemory", {
            "action": "save",
            "content": "Always run tests before committing code",
            "topic": "workflows",
            "priority": 3,
            "tags": ["testing", "git"],
            "verified": True
        })

        result = await auto_memory_tool.execute(message)
        assert result.is_success(), f"Save failed: {result.error}"
        assert "Memory saved" in result.result

        # Search for the memory
        message = create_acp_message("AutoMemory", {
            "action": "search",
            "query": "tests before committing"
        })

        result = await auto_memory_tool.execute(message)
        assert result.is_success(), f"Search failed: {result.error}"
        assert "tests before committing" in result.result
        assert "Found" in result.result

    async def test_auto_memory_tool_update_and_remove(self):
        """Test auto memory tool update and remove operations."""
        # Save a memory first
        message = create_acp_message("AutoMemory", {
            "action": "save",
            "content": "Use console.log for debugging",
            "topic": "debugging",
            "priority": 1
        })

        result = await auto_memory_tool.execute(message)
        assert result.is_success()

        # Update the memory
        message = create_acp_message("AutoMemory", {
            "action": "update",
            "content": "Use console.log for debugging",
            "new_content": "Use proper debugging tools instead of console.log"
        })

        result = await auto_memory_tool.execute(message)
        assert result.is_success(), f"Update failed: {result.error}"
        assert "Memory updated" in result.result

        # Verify update
        message = create_acp_message("AutoMemory", {
            "action": "search",
            "query": "proper debugging tools"
        })

        result = await auto_memory_tool.execute(message)
        assert result.is_success()
        assert "proper debugging tools" in result.result

        # Remove the memory
        message = create_acp_message("AutoMemory", {
            "action": "remove",
            "content": "proper debugging tools"
        })

        result = await auto_memory_tool.execute(message)
        assert result.is_success(), f"Remove failed: {result.error}"
        assert "Memory removed" in result.result

    async def test_auto_memory_tool_list_topics(self):
        """Test auto memory tool list topics operation."""
        message = create_acp_message("AutoMemory", {
            "action": "list_topics"
        })

        result = await auto_memory_tool.execute(message)
        assert result.is_success(), f"List topics failed: {result.error}"
        assert "Available Memory Topics" in result.result
        assert "General" in result.result
        assert "Patterns" in result.result
        assert "User Preferences" in result.result

    async def test_session_manager_basic_operations(self):
        """Test basic session manager operations."""
        session_manager = get_session_manager()

        # Create a session
        session = session_manager.create_session("test_session_123", {"test": True})
        assert session.session_id == "test_session_123"
        assert session.metadata["test"] is True

        # Add conversation entry
        session_manager.add_conversation_entry(
            role="user",
            content="Hello, how can I test my code?",
            metadata={"intent": "testing_question"}
        )

        assert len(session.conversation_history) == 1
        assert session.conversation_history[0]["role"] == "user"
        assert "test my code" in session.conversation_history[0]["content"]

        # Update context data
        session_manager.update_context_data("current_project", "test_project")
        assert session.context_data["current_project"] == "test_project"

        # Set user preference
        session_manager.set_user_preference("preferred_editor", "vscode")
        assert session.user_preferences["preferred_editor"] == "vscode"

        # Get preference
        editor = session_manager.get_user_preference("preferred_editor")
        assert editor == "vscode"

    async def test_session_persistence(self):
        """Test session persistence and loading."""
        session_manager = get_session_manager()

        # Create session with data
        session = session_manager.create_session("persistence_test", {"persistent": True})
        session_manager.add_conversation_entry("user", "Test message for persistence")
        session_manager.update_context_data("test_key", "test_value")

        # Save session
        session_manager.save_current_session()

        # Load the session
        loaded_session = session_manager.load_session("persistence_test")
        assert loaded_session is not None
        assert loaded_session.session_id == "persistence_test"
        assert len(loaded_session.conversation_history) == 1
        assert loaded_session.context_data["test_key"] == "test_value"

    async def test_memory_file_generation(self):
        """Test memory file generation and main memory content."""
        memory_manager = get_memory_manager()

        # Add some high-priority memories
        memory_manager.add_memory(
            "High priority pattern: Use dependency injection",
            MemoryTopic.PATTERNS,
            priority=3,
            verified=True
        )

        memory_manager.add_memory(
            "User prefers TypeScript over JavaScript",
            MemoryTopic.USER_PREFERENCES,
            priority=2,
            verified=True
        )

        # Get main memory content
        main_content = memory_manager.get_main_memory_content()
        assert "DevMind Auto Memory" in main_content
        assert len(main_content) > 0

        # Verify memory files exist
        assert memory_manager.main_memory_file.exists()

    async def test_error_handling(self):
        """Test error handling for invalid operations."""
        # Test invalid action
        message = create_acp_message("AutoMemory", {
            "action": "invalid_action"
        })

        result = await auto_memory_tool.execute(message)
        assert not result.is_success()
        assert "Unknown action" in result.error

        # Test missing required parameters
        message = create_acp_message("AutoMemory", {
            "action": "save"
            # Missing content
        })

        result = await auto_memory_tool.execute(message)
        assert not result.is_success()
        assert "content is required" in result.error

    async def run_all_tests(self):
        """Run all memory system tests."""
        print("🧪 Memory and Session Management Test Suite")
        print("=" * 50)

        await self.run_test("Memory Manager Basic Operations", self.test_memory_manager_basic_operations)
        await self.run_test("AutoMemory Save and Search", self.test_auto_memory_tool_save_and_search)
        await self.run_test("AutoMemory Update and Remove", self.test_auto_memory_tool_update_and_remove)
        await self.run_test("AutoMemory List Topics", self.test_auto_memory_tool_list_topics)
        await self.run_test("Session Manager Operations", self.test_session_manager_basic_operations)
        await self.run_test("Session Persistence", self.test_session_persistence)
        await self.run_test("Memory File Generation", self.test_memory_file_generation)
        await self.run_test("Error Handling", self.test_error_handling)

        print("\n" + "="*60)
        print(f"📊 Memory System Tests: {self.passed} passed, {self.failed} failed")
        print("="*60)

        success = self.failed == 0

        if success:
            print("🎉 All memory system tests PASSED!")
            print("✨ Memory and session management system is fully functional!")
        else:
            print(f"⚠️  {self.failed} test(s) failed:")
            for result in self.test_results:
                if result.startswith("❌"):
                    print(f"   {result}")

        return success


async def main():
    """Run the memory system test suite."""
    print("🧪 Starting Memory and Session Management Tests\n")

    suite = MemorySystemTestSuite()
    success = await suite.run_all_tests()

    # Cleanup test data
    try:
        # Clean up test sessions and memories
        import shutil
        test_dirs = ["sessions"]
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                # Only remove test-related files
                for file in os.listdir(test_dir):
                    if "test" in file.lower():
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