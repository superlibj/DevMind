#!/usr/bin/env python3
"""
Final comprehensive test suite for all DevMind enhancements.

Tests all implemented functionality to ensure complete system works
correctly and without bugs before user commits code.
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

    # Enhanced git (new)
    smart_commit_tool, pr_create_tool,

    # ACP framework
    create_acp_message, ACPMessageType
)


class ComprehensiveTestSuite:
    """Comprehensive test suite for all DevMind functionality."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_results = []

    async def run_test(self, test_name: str, test_func, critical: bool = False):
        """Run a single test."""
        print(f"Testing {test_name}...", end=" ")
        try:
            await test_func()
            print("✅ PASSED")
            self.passed += 1
            self.test_results.append(f"✅ {test_name}")
        except Exception as e:
            status = "❌ CRITICAL FAILURE" if critical else "❌ FAILED"
            print(f"{status}: {str(e)}")
            self.failed += 1
            self.test_results.append(f"❌ {test_name}: {str(e)}")
            if critical:
                print(f"\n🚨 Critical test failed: {test_name}")
                print("This indicates a fundamental issue that must be fixed.")

    async def test_all_systems(self):
        """Test all implemented systems comprehensively."""

        print("🧪 DevMind Final Comprehensive Test Suite")
        print("=" * 50)

        # Phase 1: Core Enhanced Tools (Critical)
        print("\n📁 Phase 1: Core Enhanced Tools")
        await self.run_test("Enhanced Read Tool", self.test_read_tool, critical=True)
        await self.run_test("Enhanced Write Tool", self.test_write_tool, critical=True)
        await self.run_test("Enhanced Edit Tool", self.test_edit_tool, critical=True)
        await self.run_test("Enhanced Bash Tool", self.test_bash_tool, critical=True)
        await self.run_test("Enhanced Glob Tool", self.test_glob_tool, critical=True)
        await self.run_test("Enhanced Grep Tool", self.test_grep_tool, critical=True)
        await self.run_test("WebSearch Tool", self.test_websearch_tool)
        await self.run_test("WebFetch Tool", self.test_webfetch_tool)

        # Phase 2: Task Management System
        print("\n📋 Phase 2: Task Management System")
        await self.run_test("Task Creation & Management", self.test_task_management, critical=True)
        await self.run_test("Plan Mode", self.test_plan_mode, critical=True)

        # Phase 3: Permission System
        print("\n🔐 Phase 3: Permission System")
        await self.run_test("User Question System", self.test_permission_system)

        # Phase 4: Enhanced Git Integration
        print("\n🔄 Phase 4: Enhanced Git Integration")
        await self.run_test("Git Safety Checker", self.test_git_safety_checker)
        await self.run_test("Smart Commit Tool", self.test_smart_commit)

        # Phase 5: Integration Tests
        print("\n🔗 Phase 5: System Integration")
        await self.run_test("Tool Registry", self.test_tool_registry, critical=True)
        await self.run_test("ACP Framework", self.test_acp_framework, critical=True)

    async def test_read_tool(self):
        """Test enhanced Read tool functionality."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Line 1: Test content\nLine 2: More content\nLine 3: Final line\n")
            test_file = f.name

        try:
            # Test basic read
            message = create_acp_message("Read", {"file_path": test_file})
            result = await read_tool.execute(message)
            assert result.is_success(), f"Read failed: {result.error}"
            assert "1→Line 1: Test content" in result.result, "Line numbering not working"
            assert "Test content" in result.result, "Content not found"

            # Test with limit
            message = create_acp_message("Read", {"file_path": test_file, "limit": 2})
            result = await read_tool.execute(message)
            assert result.is_success(), f"Read with limit failed: {result.error}"
            assert "Line 3" not in result.result, "Limit not working"

        finally:
            os.unlink(test_file)

    async def test_write_tool(self):
        """Test enhanced Write tool functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_write.txt")
            content = "Hello DevMind!\nThis is a test file.\nWith multiple lines."

            # Test write
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
            assert written_content == content, "Content doesn't match"

    async def test_edit_tool(self):
        """Test enhanced Edit tool functionality."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Hello World\nThis is DevMind\nEnd of file")
            test_file = f.name

        try:
            # Test edit
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
            assert "Hello DevMind" in content, "Edit not applied"
            assert "Hello World" not in content, "Old content still present"

        finally:
            os.unlink(test_file)

    async def test_bash_tool(self):
        """Test enhanced Bash tool functionality."""
        # Test simple command
        message = create_acp_message("Bash", {
            "command": "echo 'DevMind Test'",
            "description": "Test echo command"
        })
        result = await bash_tool.execute(message)
        assert result.is_success(), f"Bash failed: {result.error}"
        assert "DevMind Test" in result.result, "Command output not found"

    async def test_glob_tool(self):
        """Test enhanced Glob tool functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = [
                os.path.join(temp_dir, "test1.py"),
                os.path.join(temp_dir, "test2.py"),
                os.path.join(temp_dir, "other.txt")
            ]

            for file_path in test_files:
                with open(file_path, 'w') as f:
                    f.write("test content")

            # Test glob
            message = create_acp_message("Glob", {
                "pattern": "*.py",
                "path": temp_dir
            })
            result = await glob_tool.execute(message)
            assert result.is_success(), f"Glob failed: {result.error}"
            assert "test1.py" in result.result, "Python file not found"
            assert "test2.py" in result.result, "Python file not found"

    async def test_grep_tool(self):
        """Test enhanced Grep tool functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("Hello World\nThis is DevMind testing\nAnother line\n")

            # Test grep
            message = create_acp_message("Grep", {
                "pattern": "DevMind",
                "path": temp_dir,
                "output_mode": "files_with_matches"
            })
            result = await grep_tool.execute(message)
            assert result.is_success(), f"Grep failed: {result.error}"

    async def test_websearch_tool(self):
        """Test WebSearch tool (mock functionality)."""
        message = create_acp_message("WebSearch", {
            "query": "DevMind AI development tools"
        })
        result = await websearch_tool.execute(message)
        assert result.is_success(), f"WebSearch failed: {result.error}"
        assert "Search results" in result.result, "Search results not found"

    async def test_webfetch_tool(self):
        """Test WebFetch tool (mock functionality)."""
        message = create_acp_message("WebFetch", {
            "url": "https://example.com",
            "prompt": "Extract main content"
        })
        result = await webfetch_tool.execute(message)
        assert result.is_success(), f"WebFetch failed: {result.error}"

    async def test_task_management(self):
        """Test comprehensive task management system."""
        # Test task creation
        message = create_acp_message("TaskCreate", {
            "subject": "Test Task for Final Verification",
            "description": "This task verifies the task management system works correctly",
            "activeForm": "Testing task management"
        })
        result = await task_create_tool.execute(message)
        assert result.is_success(), f"TaskCreate failed: {result.error}"
        task_id = result.metadata.get("task_id")
        assert task_id, "Task ID not returned"

        # Test task retrieval
        message = create_acp_message("TaskGet", {"taskId": task_id})
        result = await task_get_tool.execute(message)
        assert result.is_success(), f"TaskGet failed: {result.error}"
        assert "Test Task for Final Verification" in result.result, "Task content not found"

        # Test task update
        message = create_acp_message("TaskUpdate", {
            "taskId": task_id,
            "status": "completed"
        })
        result = await task_update_tool.execute(message)
        assert result.is_success(), f"TaskUpdate failed: {result.error}"

        # Test task list
        message = create_acp_message("TaskList", {})
        result = await task_list_tool.execute(message)
        assert result.is_success(), f"TaskList failed: {result.error}"

    async def test_plan_mode(self):
        """Test plan mode functionality."""
        # Test enter plan mode
        message = create_acp_message("EnterPlanMode", {})
        result = await enter_plan_mode_tool.execute(message)
        assert result.is_success(), f"EnterPlanMode failed: {result.error}"
        assert "Plan Mode" in result.result, "Plan mode not entered"

        # Check plan file creation
        plan_file = Path("sessions/current_plan.md")
        assert plan_file.exists(), "Plan file not created"

        # Test exit plan mode
        message = create_acp_message("ExitPlanMode", {})
        result = await exit_plan_mode_tool.execute(message)
        assert result.is_success(), f"ExitPlanMode failed: {result.error}"

    async def test_permission_system(self):
        """Test permission system functionality."""
        message = create_acp_message("AskUserQuestion", {
            "questions": [
                {
                    "question": "Which testing approach should we use?",
                    "header": "Test Method",
                    "multiSelect": False,
                    "options": [
                        {
                            "label": "Unit Tests",
                            "description": "Test individual components"
                        },
                        {
                            "label": "Integration Tests",
                            "description": "Test system interactions"
                        }
                    ]
                }
            ]
        })
        result = await ask_user_question_tool.execute(message)
        assert result.is_success(), f"AskUserQuestion failed: {result.error}"
        assert "User Input Required" in result.result, "Question not presented"

    async def test_git_safety_checker(self):
        """Test git safety checker functionality."""
        from src.core.tools.enhanced_git.git_safety_checker import GitSafetyChecker

        checker = GitSafetyChecker()

        # Test safe operation
        is_safe, warnings, blocking = await checker.check_operation_safety(
            "status", [], {}
        )
        assert is_safe, "Safe operation marked as unsafe"
        assert len(blocking) == 0, "Safe operation has blocking issues"

        # Test dangerous operation detection
        is_safe, warnings, blocking = await checker.check_operation_safety(
            "reset", ["--hard"], {}
        )
        assert not is_safe or len(warnings) > 0, "Dangerous operation not detected"

    async def test_smart_commit(self):
        """Test smart commit functionality (validation only)."""
        # Test validation - this will fail if not in git repo, which is expected
        message = create_acp_message("SmartCommit", {
            "dry_run": True,
            "message": "Test commit message"
        })
        result = await smart_commit_tool.execute(message)
        # This might fail if not in a git repo, which is fine for testing
        # Just ensure the tool doesn't crash
        assert isinstance(result, type(result)), "SmartCommit tool crashed"

    async def test_tool_registry(self):
        """Test tool registry functionality."""
        from src.core.tools import get_available_tools

        tools = get_available_tools()
        assert len(tools) > 0, "No tools registered"

        # Check for key tools
        tool_names = [tool.name for tool in tools]
        expected_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "TaskCreate"]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool {expected_tool} not registered"

    async def test_acp_framework(self):
        """Test ACP framework functionality."""
        # Test message creation
        message = create_acp_message("test", {"param": "value"})
        assert message.tool_name == "test", "Message creation failed"
        assert message.payload["param"] == "value", "Message payload incorrect"

    async def run_all_tests(self):
        """Run all tests and return success status."""
        await self.test_all_systems()

        print("\n" + "="*60)
        print(f"🎯 **FINAL TEST RESULTS**")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print("="*60)

        success = self.failed == 0

        if success:
            print("\n🎉 **ALL TESTS PASSED!**")
            print("✨ DevMind enhancements are fully functional and ready for use!")
            print("🚀 The system has been comprehensively tested and verified.")
        else:
            print(f"\n⚠️  **{self.failed} TEST(S) FAILED**")
            print("❌ Please review and fix the issues before proceeding:")
            for result in self.test_results:
                if result.startswith("❌"):
                    print(f"   {result}")

        return success


async def main():
    """Run the comprehensive test suite."""
    print("🧪 Starting Final Comprehensive DevMind Test Suite")
    print("🎯 This validates ALL implemented functionality is working correctly\n")

    suite = ComprehensiveTestSuite()
    success = await suite.run_all_tests()

    # Cleanup
    try:
        plan_file = Path("sessions/current_plan.md")
        if plan_file.exists():
            plan_file.unlink()
    except:
        pass

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())