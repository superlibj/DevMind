#!/usr/bin/env python3
"""
Comprehensive test suite for enhanced DevMind functionality.

Tests all the newly implemented tools and systems to ensure they work
correctly and without bugs.
"""
import asyncio
import os
import sys
import tempfile
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.tools import (
    # Enhanced tools
    read_tool, write_tool, edit_tool, bash_tool, glob_tool, grep_tool,
    websearch_tool, webfetch_tool,

    # Task management
    task_create_tool, task_update_tool, task_get_tool, task_list_tool,
    enter_plan_mode_tool, exit_plan_mode_tool,

    # Permission system
    ask_user_question_tool,

    # ACP framework
    create_acp_message, ACPMessageType
)


class TestRunner:
    """Test runner for enhanced functionality."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_results = []

    async def run_test(self, test_name: str, test_func):
        """Run a single test."""
        print(f"Running {test_name}...", end=" ")
        try:
            await test_func()
            print("✅ PASSED")
            self.passed += 1
            self.test_results.append(f"✅ {test_name}")
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.failed += 1
            self.test_results.append(f"❌ {test_name}: {str(e)}")

    async def test_enhanced_tools(self):
        """Test all enhanced tools."""

        # Test Read tool
        async def test_read():
            # Create a test file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write("Line 1\nLine 2\nLine 3\n")
                test_file = f.name

            try:
                message = create_acp_message("Read", {"file_path": test_file})
                result = await read_tool.execute(message)
                assert result.is_success(), f"Read failed: {result.error}"
                assert "Line 1" in result.result, "Read content not found"
                assert "1→Line 1" in result.result, "Line numbering not working"
            finally:
                os.unlink(test_file)

        await self.run_test("Enhanced Read Tool", test_read)

        # Test Write tool
        async def test_write():
            with tempfile.TemporaryDirectory() as temp_dir:
                test_file = os.path.join(temp_dir, "test.txt")
                content = "Hello, World!\nThis is a test."

                message = create_acp_message("Write", {
                    "file_path": test_file,
                    "content": content
                })
                result = await write_tool.execute(message)
                assert result.is_success(), f"Write failed: {result.error}"
                assert os.path.exists(test_file), "File was not created"

                # Verify content
                with open(test_file, 'r') as f:
                    written_content = f.read()
                assert written_content == content, "Written content doesn't match"

        await self.run_test("Enhanced Write Tool", test_write)

        # Test Edit tool
        async def test_edit():
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write("Hello World\nThis is a test\nEnd")
                test_file = f.name

            try:
                message = create_acp_message("Edit", {
                    "file_path": test_file,
                    "old_string": "Hello World",
                    "new_string": "Hello DevMind"
                })
                result = await edit_tool.execute(message)
                assert result.is_success(), f"Edit failed: {result.error}"

                # Verify edit
                with open(test_file, 'r') as f:
                    content = f.read()
                assert "Hello DevMind" in content, "Edit did not work"
                assert "Hello World" not in content, "Old string still present"
            finally:
                os.unlink(test_file)

        await self.run_test("Enhanced Edit Tool", test_edit)

        # Test Bash tool
        async def test_bash():
            message = create_acp_message("Bash", {
                "command": "echo 'Hello DevMind'",
                "description": "Test echo command"
            })
            result = await bash_tool.execute(message)
            assert result.is_success(), f"Bash failed: {result.error}"
            assert "Hello DevMind" in result.result, "Command output not found"

        await self.run_test("Enhanced Bash Tool", test_bash)

        # Test Glob tool
        async def test_glob():
            # Create some test files
            with tempfile.TemporaryDirectory() as temp_dir:
                test_files = [
                    os.path.join(temp_dir, "test1.py"),
                    os.path.join(temp_dir, "test2.py"),
                    os.path.join(temp_dir, "other.txt")
                ]

                for file_path in test_files:
                    with open(file_path, 'w') as f:
                        f.write("test content")

                message = create_acp_message("Glob", {
                    "pattern": "*.py",
                    "path": temp_dir
                })
                result = await glob_tool.execute(message)
                assert result.is_success(), f"Glob failed: {result.error}"
                assert "test1.py" in result.result, "Python file not found"
                assert "test2.py" in result.result, "Python file not found"
                assert "other.txt" not in result.result, "Non-matching file found"

        await self.run_test("Enhanced Glob Tool", test_glob)

        # Test Grep tool
        async def test_grep():
            with tempfile.TemporaryDirectory() as temp_dir:
                test_file = os.path.join(temp_dir, "test.txt")
                with open(test_file, 'w') as f:
                    f.write("Hello World\nThis is DevMind\nAnother line\n")

                message = create_acp_message("Grep", {
                    "pattern": "DevMind",
                    "path": temp_dir,
                    "output_mode": "files_with_matches"
                })
                result = await grep_tool.execute(message)
                assert result.is_success(), f"Grep failed: {result.error}"
                assert test_file in result.result or "test.txt" in result.result, "Match not found"

        await self.run_test("Enhanced Grep Tool", test_grep)

        # Test WebSearch tool (mock)
        async def test_websearch():
            message = create_acp_message("WebSearch", {
                "query": "DevMind AI assistant"
            })
            result = await websearch_tool.execute(message)
            assert result.is_success(), f"WebSearch failed: {result.error}"
            assert "Search results" in result.result, "Search results not found"

        await self.run_test("Enhanced WebSearch Tool", test_websearch)

        # Test WebFetch tool (mock)
        async def test_webfetch():
            message = create_acp_message("WebFetch", {
                "url": "https://example.com",
                "prompt": "Extract main content"
            })
            result = await webfetch_tool.execute(message)
            assert result.is_success(), f"WebFetch failed: {result.error}"
            assert "example.com" in result.result, "URL content not found"

        await self.run_test("Enhanced WebFetch Tool", test_webfetch)

    async def test_task_management(self):
        """Test task management system."""

        # Test TaskCreate
        async def test_task_create():
            message = create_acp_message("TaskCreate", {
                "subject": "Test Task",
                "description": "This is a test task for verification",
                "activeForm": "Testing functionality"
            })
            result = await task_create_tool.execute(message)
            assert result.is_success(), f"TaskCreate failed: {result.error}"
            assert "Task #" in result.result, "Task ID not found"
            return result.metadata.get("task_id")

        task_id = await self.run_test("Task Creation", test_task_create)

        # Test TaskGet
        async def test_task_get():
            message = create_acp_message("TaskGet", {
                "taskId": task_id
            })
            result = await task_get_tool.execute(message)
            assert result.is_success(), f"TaskGet failed: {result.error}"
            assert "Test Task" in result.result, "Task content not found"

        if task_id:
            await self.run_test("Task Retrieval", test_task_get)

        # Test TaskList
        async def test_task_list():
            message = create_acp_message("TaskList", {})
            result = await task_list_tool.execute(message)
            assert result.is_success(), f"TaskList failed: {result.error}"
            assert "Test Task" in result.result or "Found" in result.result, "Task list not working"

        await self.run_test("Task Listing", test_task_list)

        # Test TaskUpdate
        async def test_task_update():
            if task_id:
                message = create_acp_message("TaskUpdate", {
                    "taskId": task_id,
                    "status": "completed"
                })
                result = await task_update_tool.execute(message)
                assert result.is_success(), f"TaskUpdate failed: {result.error}"
                assert "Updated" in result.result, "Task update not working"

        if task_id:
            await self.run_test("Task Update", test_task_update)

    async def test_plan_mode(self):
        """Test plan mode tools."""

        # Test EnterPlanMode
        async def test_enter_plan_mode():
            message = create_acp_message("EnterPlanMode", {})
            result = await enter_plan_mode_tool.execute(message)
            assert result.is_success(), f"EnterPlanMode failed: {result.error}"
            assert "Plan Mode" in result.result, "Plan mode entry not working"

            # Check if plan file was created
            plan_file = Path("sessions/current_plan.md")
            assert plan_file.exists(), "Plan file not created"

        await self.run_test("Enter Plan Mode", test_enter_plan_mode)

        # Test ExitPlanMode
        async def test_exit_plan_mode():
            message = create_acp_message("ExitPlanMode", {
                "allowedPrompts": [
                    {"tool": "Bash", "prompt": "run tests"}
                ]
            })
            result = await exit_plan_mode_tool.execute(message)
            assert result.is_success(), f"ExitPlanMode failed: {result.error}"
            assert "approval" in result.result.lower(), "Plan approval not working"

        await self.run_test("Exit Plan Mode", test_exit_plan_mode)

    async def test_permission_system(self):
        """Test permission system."""

        # Test AskUserQuestion
        async def test_ask_user_question():
            message = create_acp_message("AskUserQuestion", {
                "questions": [
                    {
                        "question": "Which approach should we use?",
                        "header": "Approach",
                        "multiSelect": False,
                        "options": [
                            {
                                "label": "Option A",
                                "description": "First approach"
                            },
                            {
                                "label": "Option B",
                                "description": "Second approach"
                            }
                        ]
                    }
                ]
            })
            result = await ask_user_question_tool.execute(message)
            assert result.is_success(), f"AskUserQuestion failed: {result.error}"
            assert "User Input Required" in result.result, "Question presentation not working"

        await self.run_test("User Question Tool", test_ask_user_question)

    async def run_all_tests(self):
        """Run all test suites."""
        print("🧪 Starting Comprehensive DevMind Enhancement Tests\n")

        await self.test_enhanced_tools()
        await self.test_task_management()
        await self.test_plan_mode()
        await self.test_permission_system()

        print("\n" + "="*60)
        print(f"📊 Test Results: {self.passed} passed, {self.failed} failed")
        print("="*60)

        if self.failed == 0:
            print("🎉 All tests PASSED! DevMind enhancements are working correctly.")
        else:
            print("⚠️  Some tests failed. Please review the errors above.")
            print("\nFailed tests:")
            for result in self.test_results:
                if result.startswith("❌"):
                    print(f"  {result}")

        return self.failed == 0


async def main():
    """Run the test suite."""
    runner = TestRunner()
    success = await runner.run_all_tests()

    # Clean up test files
    try:
        plan_file = Path("sessions/current_plan.md")
        if plan_file.exists():
            plan_file.unlink()
    except:
        pass

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())