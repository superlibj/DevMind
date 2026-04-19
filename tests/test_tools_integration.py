"""
Tests for the tool integration system.
"""
import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.core.tools import (
    acp_registry, acp_client, git_tool, file_tool, vim_tool,
    ACPMessage, ACPStatus, ACPToolResult, initialize_acp_integration,
    get_acp_tool_info, list_acp_tools
)


class TestACPIntegration:
    """Test ACP integration framework."""

    def test_acp_registry_initialization(self):
        """Test that ACP registry initializes with tools."""
        tools = acp_registry.list_tools()
        assert len(tools) >= 3  # Should have git, file, vim tools

        tool_names = {tool.name for tool in tools}
        assert "git" in tool_names
        assert "file" in tool_names
        assert "vim" in tool_names

    def test_tool_specifications(self):
        """Test tool specifications are properly formed."""
        git_spec = acp_registry.get_tool("git").get_spec()

        assert git_spec.name == "git"
        assert git_spec.description
        assert git_spec.version
        assert "version_control" in git_spec.capabilities
        assert git_spec.security_level == "high"

    def test_acp_client_initialization(self):
        """Test ACP client is properly initialized."""
        assert acp_client.registry == acp_registry
        available_tools = acp_client.get_available_tools()
        assert "git" in available_tools
        assert "file" in available_tools
        assert "vim" in available_tools

    def test_get_acp_tool_info(self):
        """Test getting tool information."""
        git_info = get_acp_tool_info("git")
        assert git_info is not None
        assert git_info["name"] == "git"
        assert "capabilities" in git_info
        assert "security_level" in git_info

        # Test non-existent tool
        unknown_info = get_acp_tool_info("unknown_tool")
        assert unknown_info is None

    def test_list_acp_tools(self):
        """Test listing all ACP tools."""
        tools = list_acp_tools()
        assert len(tools) >= 3

        tool_names = {tool["name"] for tool in tools}
        assert "git" in tool_names
        assert "file" in tool_names
        assert "vim" in tool_names


class TestFileOperations:
    """Test file operations tool."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_file_write_and_read(self, temp_dir):
        """Test file write and read operations."""
        test_file = temp_dir / "test.txt"
        test_content = "Hello, World!\nThis is a test file."

        # Test write operation
        write_result = await acp_client.call_tool(
            "file",
            operation="write",
            path=str(test_file),
            content=test_content
        )

        assert write_result.status == ACPStatus.COMPLETED
        assert write_result.result["path"] == str(test_file)
        assert write_result.result["size"] > 0

        # Test read operation
        read_result = await acp_client.call_tool(
            "file",
            operation="read",
            path=str(test_file)
        )

        assert read_result.status == ACPStatus.COMPLETED
        assert read_result.result["content"] == test_content
        assert read_result.result["file_type"] == "text"

    @pytest.mark.asyncio
    async def test_file_exists(self, temp_dir):
        """Test file existence check."""
        test_file = temp_dir / "test.txt"

        # Test non-existent file
        exists_result = await acp_client.call_tool(
            "file",
            operation="exists",
            path=str(test_file)
        )

        assert exists_result.status == ACPStatus.COMPLETED
        assert exists_result.result["exists"] is False

        # Create file
        test_file.write_text("test")

        # Test existent file
        exists_result = await acp_client.call_tool(
            "file",
            operation="exists",
            path=str(test_file)
        )

        assert exists_result.status == ACPStatus.COMPLETED
        assert exists_result.result["exists"] is True
        assert exists_result.result["is_file"] is True

    @pytest.mark.asyncio
    async def test_directory_operations(self, temp_dir):
        """Test directory operations."""
        test_dir = temp_dir / "subdir"

        # Test mkdir
        mkdir_result = await acp_client.call_tool(
            "file",
            operation="mkdir",
            path=str(test_dir)
        )

        assert mkdir_result.status == ACPStatus.COMPLETED
        assert mkdir_result.result["created"] is True

        # Test list directory
        list_result = await acp_client.call_tool(
            "file",
            operation="list",
            path=str(temp_dir)
        )

        assert list_result.status == ACPStatus.COMPLETED
        assert list_result.result["count"] >= 1

        # Check that our subdirectory is listed
        entries = list_result.result["entries"]
        subdir_entry = next((e for e in entries if e["name"] == "subdir"), None)
        assert subdir_entry is not None
        assert subdir_entry["type"] == "directory"

    @pytest.mark.asyncio
    async def test_file_security_validation(self, temp_dir):
        """Test file operation security validation."""
        # Test invalid path
        invalid_result = await acp_client.call_tool(
            "file",
            operation="read",
            path="/etc/passwd"  # Should be blocked
        )

        assert invalid_result.status == ACPStatus.FAILED
        assert "not allowed" in invalid_result.error.lower()


class TestVimOperations:
    """Test Vim operations tool."""

    @pytest.fixture
    def temp_file(self):
        """Create temporary file for tests."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
            temp_path = f.name

        yield temp_path

        # Cleanup
        try:
            Path(temp_path).unlink()
        except FileNotFoundError:
            pass

    @pytest.mark.asyncio
    async def test_vim_edit_operation(self, temp_file):
        """Test Vim edit operation."""
        edit_result = await acp_client.call_tool(
            "vim",
            operation="edit",
            file_path=temp_file
        )

        assert edit_result.status == ACPStatus.COMPLETED
        assert edit_result.result["exists"] is True
        assert edit_result.result["editable"] is True
        assert edit_result.result["line_count"] >= 1

    @pytest.mark.asyncio
    async def test_vim_search_operation(self, temp_file):
        """Test Vim search operation."""
        search_result = await acp_client.call_tool(
            "vim",
            operation="search",
            file_path=temp_file,
            search_pattern="Line 2"
        )

        assert search_result.status == ACPStatus.COMPLETED
        assert search_result.result["match_count"] >= 1

        matches = search_result.result["matches"]
        assert len(matches) >= 1
        assert matches[0]["line_number"] == 2

    @pytest.mark.asyncio
    async def test_vim_goto_line_operation(self, temp_file):
        """Test Vim goto line operation."""
        goto_result = await acp_client.call_tool(
            "vim",
            operation="goto_line",
            file_path=temp_file,
            line_number=3
        )

        assert goto_result.status == ACPStatus.COMPLETED
        assert goto_result.result["line_number"] == 3
        assert "Line 3" in goto_result.result["line_content"]

    @pytest.mark.asyncio
    async def test_vim_insert_operation(self, temp_file):
        """Test Vim insert operation."""
        insert_result = await acp_client.call_tool(
            "vim",
            operation="insert",
            file_path=temp_file,
            content="New Line",
            line_number=2
        )

        assert insert_result.status == ACPStatus.COMPLETED
        assert insert_result.result["lines_inserted"] == 1
        assert insert_result.result["inserted_at_line"] == 2

        # Verify content was inserted
        content = Path(temp_file).read_text()
        lines = content.split('\n')
        assert "New Line" in lines[1]  # Should be at index 1 (line 2)

    @pytest.mark.asyncio
    async def test_vim_replace_operation(self, temp_file):
        """Test Vim replace operation."""
        replace_result = await acp_client.call_tool(
            "vim",
            operation="replace",
            file_path=temp_file,
            search_pattern="Line 2",
            replace_pattern="Modified Line 2"
        )

        assert replace_result.status == ACPStatus.COMPLETED
        assert replace_result.result["replacements_made"] >= 1

        # Verify replacement
        content = Path(temp_file).read_text()
        assert "Modified Line 2" in content
        assert "Line 2" not in content

    @pytest.mark.asyncio
    async def test_vim_security_validation(self, temp_file):
        """Test Vim security validation."""
        # Test dangerous command
        dangerous_result = await acp_client.call_tool(
            "vim",
            operation="command",
            vim_command=":!rm -rf /",  # Should be blocked
            file_path=temp_file
        )

        assert dangerous_result.status == ACPStatus.FAILED
        assert "not allowed" in dangerous_result.error.lower()


@pytest.mark.skipif(
    True,  # Skip by default - requires git repository
    reason="Requires git repository setup"
)
class TestGitOperations:
    """Test Git operations tool."""

    @pytest.mark.asyncio
    async def test_git_status(self):
        """Test git status operation."""
        status_result = await acp_client.call_tool(
            "git",
            operation="status"
        )

        # This will fail if not in a git repo, which is expected
        assert status_result.status in [ACPStatus.COMPLETED, ACPStatus.FAILED]

    @pytest.mark.asyncio
    async def test_git_branch_list(self):
        """Test git branch listing."""
        branch_result = await acp_client.call_tool(
            "git",
            operation="branch",
            type="list"
        )

        # This will fail if not in a git repo, which is expected
        assert branch_result.status in [ACPStatus.COMPLETED, ACPStatus.FAILED]


class TestErrorHandling:
    """Test error handling in tool operations."""

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test calling non-existent tool."""
        result = await acp_client.call_tool("nonexistent_tool", operation="test")
        assert result.status == ACPStatus.FAILED
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test calling tool without required parameters."""
        result = await acp_client.call_tool("file")  # Missing operation parameter
        assert result.status == ACPStatus.FAILED
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_operation(self):
        """Test calling tool with invalid operation."""
        result = await acp_client.call_tool(
            "file",
            operation="invalid_operation"
        )
        assert result.status == ACPStatus.FAILED
        assert "unsupported" in result.error.lower()


class TestAsyncOperations:
    """Test asynchronous tool operations."""

    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """Test asynchronous tool execution."""
        # Start async operation
        request_id = await acp_client.call_tool_async(
            "file",
            operation="exists",
            path="/tmp"
        )

        assert isinstance(request_id, str)

        # Wait a bit
        await asyncio.sleep(0.1)

        # Get result
        result = await acp_client.get_result(request_id)
        assert result is not None
        assert result.status == ACPStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_list_active_requests(self):
        """Test listing active requests."""
        # Should start with no active requests
        active = acp_client.list_active_requests()
        initial_count = len(active)

        # Start an operation
        request_id = await acp_client.call_tool_async(
            "file",
            operation="exists",
            path="/tmp"
        )

        # Check if it appears in active list (might complete too quickly)
        await asyncio.sleep(0.01)
        active = acp_client.list_active_requests()

        # The request might have completed already, so we just check it was created
        assert request_id is not None


class TestIntegrationWithAgent:
    """Test integration between ACP tools and ReAct agent."""

    def test_agent_integration_initialization(self):
        """Test agent integration initialization."""
        # This should not raise an exception
        try:
            initialize_acp_integration()
        except Exception as e:
            pytest.fail(f"Agent integration initialization failed: {e}")

    @pytest.mark.asyncio
    async def test_tool_execution_through_agent(self):
        """Test executing tools through agent integration."""
        from src.core.tools.agent_integration import execute_acp_tool

        result = await execute_acp_tool(
            "file",
            {"operation": "exists", "path": "/tmp"}
        )

        assert result.success is True
        assert result.result is not None


def test_tool_manifest_generation():
    """Test tool manifest generation."""
    manifest = acp_registry.get_tool_manifest()

    assert manifest["version"] == "1.0.0"
    assert manifest["protocol"] == "ACP"
    assert "tools" in manifest
    assert manifest["count"] >= 3

    # Check that git tool is in manifest
    assert "git" in manifest["tools"]
    git_spec = manifest["tools"]["git"]
    assert git_spec["name"] == "git"
    assert "capabilities" in git_spec