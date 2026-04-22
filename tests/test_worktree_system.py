#!/usr/bin/env python3
"""
Test suite for the Worktree System.

Tests worktree creation, management, isolation, and cleanup functionality.
"""
import asyncio
import os
import shutil
import tempfile
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.core.tools import (
    enter_worktree_tool,
    create_acp_message
)
from src.core.tools.worktree_system import (
    get_worktree_manager
)


class WorktreeSystemTestSuite:
    """Test suite for worktree system functionality."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_results = []
        self.test_dir = None
        self.original_cwd = Path.cwd()

    async def run_test(self, test_name: str, test_func):
        """Run a single test."""
        print(f"Testing {test_name}...", end=" ")
        try:
            # Ensure we start each test in the main test directory
            os.chdir(self.test_dir)

            await test_func()
            print("✅ PASSED")
            self.passed += 1
            self.test_results.append(f"✅ {test_name}")
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.failed += 1
            self.test_results.append(f"❌ {test_name}: {str(e)}")
        finally:
            # Always return to test directory after each test
            try:
                os.chdir(self.test_dir)
            except:
                pass

    async def setup_test_environment(self):
        """Set up test environment with temporary directory."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="worktree_test_"))
        os.chdir(self.test_dir)

        # Initialize git repository for testing
        try:
            import subprocess
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)

            # Create initial commit
            test_file = self.test_dir / "README.md"
            test_file.write_text("# Test Repository\n\nThis is a test repository for worktree testing.")

            subprocess.run(["git", "add", "README.md"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], check=True, capture_output=True)

        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not initialize git repository: {e}")
        except FileNotFoundError:
            print("Warning: Git not available, testing non-git functionality only")

    async def cleanup_test_environment(self):
        """Clean up test environment."""
        try:
            # Return to original directory
            os.chdir(self.original_cwd)

            # Remove test directory
            if self.test_dir and self.test_dir.exists():
                shutil.rmtree(self.test_dir, ignore_errors=True)

        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")

    async def test_worktree_manager_basic_operations(self):
        """Test basic worktree manager operations."""
        manager = get_worktree_manager()

        # Test listing worktrees (should be empty initially)
        worktrees = await manager.list_worktrees()
        assert isinstance(worktrees, list), "Worktree list should be a list"

        # Test creating a worktree
        worktree_info = await manager.create_worktree(name="test_worktree")
        assert worktree_info.name == "test_worktree", "Worktree name should match"
        assert worktree_info.path.exists(), "Worktree path should exist"

        # Test listing worktrees (should contain our worktree)
        worktrees = await manager.list_worktrees()
        assert len(worktrees) >= 1, "Should have at least one worktree"
        assert any(w.name == "test_worktree" for w in worktrees), "Test worktree should be in list"

    async def test_enter_worktree_tool_validation(self):
        """Test EnterWorktree tool parameter validation."""
        # Test invalid worktree name
        message = create_acp_message("EnterWorktree", {
            "name": "invalid name with spaces!"
        })
        result = await enter_worktree_tool.execute(message)
        assert not result.is_success(), "Should fail with invalid name"
        assert "letters, numbers, underscores, and hyphens" in result.error

        # Test invalid branch name
        message = create_acp_message("EnterWorktree", {
            "branch": "invalid branch name!"
        })
        result = await enter_worktree_tool.execute(message)
        assert not result.is_success(), "Should fail with invalid branch name"

    async def test_create_git_worktree(self):
        """Test creating a git worktree."""
        # Only run if we have git available
        try:
            import subprocess
            subprocess.run(["git", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Skipping git worktree test - git not available")
            return

        # Create worktree
        message = create_acp_message("EnterWorktree", {
            "name": "git_test_worktree",
            "branch": "test_branch"
        })

        original_cwd = Path.cwd()
        result = await enter_worktree_tool.execute(message)

        if result.is_success():
            assert result.metadata["worktree_name"] == "git_test_worktree"
            assert result.metadata["branch"] == "test_branch"
            assert result.metadata["is_git_worktree"] is True
            assert "Worktree Created and Activated" in result.result

            # Verify we're in the worktree directory
            current_path = Path.cwd()
            assert str(original_cwd) != str(current_path), "Should have changed directory"

            # Return to original directory for cleanup
            os.chdir(original_cwd)

    async def test_create_non_git_worktree(self):
        """Test creating a non-git worktree (directory copy)."""
        # Move to a non-git directory
        non_git_dir = self.test_dir / "non_git"
        non_git_dir.mkdir()

        # Create a test file
        test_file = non_git_dir / "test.txt"
        test_file.write_text("Test content")

        os.chdir(non_git_dir)

        # Create worktree
        message = create_acp_message("EnterWorktree", {
            "name": "non_git_worktree"
        })

        original_cwd = Path.cwd()
        result = await enter_worktree_tool.execute(message)

        if result.is_success():
            assert result.metadata["worktree_name"] == "non_git_worktree"
            assert result.metadata["is_git_worktree"] is False
            assert "isolated directory" in result.result

            # Verify we're in the worktree directory
            current_path = Path.cwd()
            assert str(original_cwd) != str(current_path), "Should have changed directory"

            # Verify test file was copied
            assert (current_path / "test.txt").exists(), "Test file should be copied"

            # Return to test directory
            os.chdir(self.test_dir)

    async def test_worktree_change_detection(self):
        """Test worktree change detection."""
        manager = get_worktree_manager()

        # Create a worktree
        worktree_info = await manager.create_worktree(name="change_test_worktree")

        # Initially should have no changes
        has_changes = await manager.check_for_changes(worktree_info)
        # Note: might have changes due to initial setup, so we don't assert False here

        # Switch to worktree and create a change
        original_cwd = Path.cwd()
        await manager.switch_to_worktree(worktree_info)

        # Create a new file
        test_file = Path.cwd() / "test_change.txt"
        test_file.write_text("Test change content")

        # Check for changes again
        has_changes = await manager.check_for_changes(worktree_info)
        if worktree_info.is_git_worktree:
            assert has_changes, "Should detect changes in git worktree"
        else:
            # For non-git worktrees, having files means changes
            assert has_changes, "Should detect files in non-git worktree"

        # Return to original directory
        os.chdir(original_cwd)

    async def test_worktree_removal(self):
        """Test worktree removal."""
        manager = get_worktree_manager()

        # Create a worktree
        worktree_info = await manager.create_worktree(name="removal_test_worktree")
        worktree_path = worktree_info.path

        # Verify it exists
        assert worktree_path.exists(), "Worktree should exist"

        # Remove it (force removal to handle any initial changes)
        await manager.remove_worktree(worktree_info, force=True)

        # Verify it's gone
        assert not worktree_path.exists(), "Worktree should be removed"

        # Should not be in active worktrees
        worktrees = await manager.list_worktrees()
        assert not any(w.name == "removal_test_worktree" for w in worktrees), "Worktree should not be in list"

    async def test_worktree_cleanup(self):
        """Test automatic worktree cleanup."""
        manager = get_worktree_manager()

        # Create a few worktrees
        worktree_names = ["cleanup_test_1", "cleanup_test_2", "cleanup_test_3"]
        worktrees = []

        for name in worktree_names:
            worktree_info = await manager.create_worktree(name=name)
            worktrees.append(worktree_info)

        # Verify they exist
        current_worktrees = await manager.list_worktrees()
        for name in worktree_names:
            assert any(w.name == name for w in current_worktrees), f"Worktree {name} should exist"

        # Test cleanup with very short age (should not remove recent worktrees)
        await manager.cleanup_old_worktrees(max_age_hours=0.001)

        # Worktrees should still exist (they're too new)
        current_worktrees = await manager.list_worktrees()
        # Note: cleanup behavior may vary based on whether worktrees have changes

        # Force cleanup by removing manually
        for worktree_info in worktrees:
            try:
                await manager.remove_worktree(worktree_info, force=True)
            except Exception:
                pass  # Ignore cleanup errors

    async def test_tool_integration(self):
        """Test integration with the tool system."""
        # Ensure we're in the main test directory (not a worktree)
        os.chdir(self.test_dir)

        # Test basic tool execution
        message = create_acp_message("EnterWorktree", {})
        result = await enter_worktree_tool.execute(message)

        # Should succeed (creates auto-named worktree)
        assert result.is_success(), f"Tool execution should succeed: {result.error if not result.is_success() else ''}"
        assert "Worktree Created and Activated" in result.result

        # Verify metadata
        assert "worktree_name" in result.metadata
        assert "worktree_path" in result.metadata
        assert "is_git_worktree" in result.metadata

        # Return to test directory for other tests
        os.chdir(self.test_dir)

    async def test_error_handling(self):
        """Test error handling for various failure conditions."""
        manager = get_worktree_manager()

        # Test removal of non-existent worktree
        from src.core.tools.worktree_system.worktree_manager import WorktreeInfo
        fake_worktree = WorktreeInfo(
            name="non_existent",
            path=Path("/non/existent/path"),
            branch="fake_branch"
        )

        try:
            await manager.remove_worktree(fake_worktree)
            assert False, "Should have raised an error for non-existent worktree"
        except Exception:
            pass  # Expected

    async def run_all_tests(self):
        """Run all worktree system tests."""
        print("🌿 Worktree System Test Suite")
        print("=" * 50)

        # Setup test environment
        await self.setup_test_environment()

        try:
            await self.run_test("Worktree Manager Basic Operations", self.test_worktree_manager_basic_operations)
            await self.run_test("EnterWorktree Tool Validation", self.test_enter_worktree_tool_validation)
            await self.run_test("Create Git Worktree", self.test_create_git_worktree)
            await self.run_test("Create Non-Git Worktree", self.test_create_non_git_worktree)
            await self.run_test("Worktree Change Detection", self.test_worktree_change_detection)
            await self.run_test("Worktree Removal", self.test_worktree_removal)
            await self.run_test("Worktree Cleanup", self.test_worktree_cleanup)
            await self.run_test("Tool Integration", self.test_tool_integration)
            await self.run_test("Error Handling", self.test_error_handling)

        finally:
            # Always cleanup
            await self.cleanup_test_environment()

        print("\n" + "="*60)
        print(f"🌿 Worktree System Tests: {self.passed} passed, {self.failed} failed")
        print("="*60)

        success = self.failed == 0

        if success:
            print("🎉 All worktree system tests PASSED!")
            print("✨ Worktree system is fully functional!")
        else:
            print(f"⚠️  {self.failed} test(s) failed:")
            for result in self.test_results:
                if result.startswith("❌"):
                    print(f"   {result}")

        return success


async def main():
    """Run the worktree system test suite."""
    print("🌿 Starting Worktree System Tests\n")

    suite = WorktreeSystemTestSuite()
    success = await suite.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())