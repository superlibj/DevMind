"""
Example of using the ACP tool integration system.

This example demonstrates how to use the integrated tools for
file operations, git commands, and vim editing.
"""
import asyncio
import tempfile
from pathlib import Path

from src.core.tools import acp_client, list_acp_tools, initialize_acp_integration


async def demo_file_operations():
    """Demonstrate file operations."""
    print("\n=== File Operations Demo ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        demo_file = temp_path / "demo.txt"

        # Write a file
        print("1. Writing file...")
        write_result = await acp_client.call_tool(
            "file",
            operation="write",
            path=str(demo_file),
            content="Hello, World!\nThis is a demo file.\nLine 3 content."
        )
        print(f"   Write result: {write_result.result['size']} bytes written")

        # Read the file
        print("2. Reading file...")
        read_result = await acp_client.call_tool(
            "file",
            operation="read",
            path=str(demo_file)
        )
        print(f"   File content:\n   {repr(read_result.result['content'])}")

        # List directory contents
        print("3. Listing directory...")
        list_result = await acp_client.call_tool(
            "file",
            operation="list",
            path=str(temp_path)
        )
        print(f"   Found {list_result.result['count']} entries:")
        for entry in list_result.result["entries"]:
            print(f"     - {entry['name']} ({entry['type']}, {entry['size']} bytes)")

        # Search for pattern
        print("4. Searching in file...")
        search_result = await acp_client.call_tool(
            "file",
            operation="search",
            path=str(demo_file),
            pattern="demo"
        )
        print(f"   Found {len(search_result.result['matches'])} matches")

        # Get file info
        print("5. Getting file info...")
        info_result = await acp_client.call_tool(
            "file",
            operation="info",
            path=str(demo_file)
        )
        print(f"   File info: {info_result.result['size']} bytes, "
              f"modified at {info_result.result['modified']}")


async def demo_vim_operations():
    """Demonstrate Vim operations."""
    print("\n=== Vim Operations Demo ===")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        temp_file = f.name

    try:
        # Edit file (read content)
        print("1. Opening file in Vim...")
        edit_result = await acp_client.call_tool(
            "vim",
            operation="edit",
            file_path=temp_file
        )
        print(f"   File opened: {edit_result.result['line_count']} lines")

        # Search in file
        print("2. Searching for pattern...")
        search_result = await acp_client.call_tool(
            "vim",
            operation="search",
            file_path=temp_file,
            search_pattern="Line 3"
        )
        print(f"   Found {search_result.result['match_count']} matches")
        for match in search_result.result["matches"]:
            print(f"     Line {match['line_number']}: {match['line_content']}")

        # Go to specific line
        print("3. Going to line 3...")
        goto_result = await acp_client.call_tool(
            "vim",
            operation="goto_line",
            file_path=temp_file,
            line_number=3
        )
        print(f"   Line 3 content: {goto_result.result['line_content']}")

        # Insert text
        print("4. Inserting new line...")
        insert_result = await acp_client.call_tool(
            "vim",
            operation="insert",
            file_path=temp_file,
            content="New inserted line",
            line_number=3
        )
        print(f"   Inserted {insert_result.result['lines_inserted']} lines")

        # Replace text
        print("5. Replacing text...")
        replace_result = await acp_client.call_tool(
            "vim",
            operation="replace",
            file_path=temp_file,
            search_pattern="Line 4",
            replace_pattern="Modified Line 4"
        )
        print(f"   Made {replace_result.result['replacements_made']} replacements")

        # Read final content
        final_read = await acp_client.call_tool(
            "file",
            operation="read",
            path=temp_file
        )
        print(f"   Final content:\n{final_read.result['content']}")

    finally:
        # Clean up
        Path(temp_file).unlink(missing_ok=True)


async def demo_git_operations():
    """Demonstrate Git operations (if in a git repository)."""
    print("\n=== Git Operations Demo ===")

    try:
        # Check git status
        print("1. Checking git status...")
        status_result = await acp_client.call_tool("git", operation="status")

        if status_result.status.value == "completed":
            status = status_result.result["status"]
            print(f"   Current branch: {status['branch']}")
            print(f"   Repository dirty: {status['is_dirty']}")
            print(f"   Staged files: {len(status['staged_files'])}")
            print(f"   Unstaged files: {len(status['unstaged_files'])}")
            print(f"   Untracked files: {len(status['untracked_files'])}")

            # List branches
            print("2. Listing branches...")
            branch_result = await acp_client.call_tool(
                "git",
                operation="branch",
                type="list"
            )

            if branch_result.status.value == "completed":
                branches = branch_result.result["branches"]
                print(f"   Found {len(branches)} branches:")
                for branch in branches[:5]:  # Show first 5
                    marker = " (current)" if branch["current"] else ""
                    print(f"     - {branch['name']}{marker}")

            # Show recent commits
            print("3. Getting recent commits...")
            log_result = await acp_client.call_tool(
                "git",
                operation="log",
                max_count=3,
                format="oneline"
            )

            if log_result.status.value == "completed":
                commits = log_result.result["commits"]
                print(f"   Recent commits:")
                for commit in commits:
                    print(f"     {commit['hash_short']}: {commit['message']}")

        else:
            print(f"   Git operation failed: {status_result.error}")
            print("   (This is normal if not in a git repository)")

    except Exception as e:
        print(f"   Git demo failed: {e}")
        print("   (This is normal if not in a git repository)")


async def demo_tool_discovery():
    """Demonstrate tool discovery and information."""
    print("\n=== Tool Discovery Demo ===")

    # List all available tools
    print("1. Available tools:")
    tools = list_acp_tools()
    for tool in tools:
        print(f"   - {tool['name']}: {tool['description']}")
        print(f"     Capabilities: {', '.join(tool['capabilities'])}")
        print(f"     Security Level: {tool['security_level']}")
        print()

    # Get tool manifest
    from src.core.tools import acp_registry
    manifest = acp_registry.get_tool_manifest()
    print(f"2. Tool manifest:")
    print(f"   Protocol version: {manifest['version']}")
    print(f"   Total tools: {manifest['count']}")
    print(f"   Available capabilities: {', '.join(manifest['capabilities'])}")


async def main():
    """Run all demonstrations."""
    print("ACP Tool Integration System Demo")
    print("=" * 50)

    try:
        # Initialize tool integration
        print("Initializing tool integration...")
        initialize_acp_integration()
        print("✓ Tool integration initialized successfully")

        # Run demonstrations
        await demo_tool_discovery()
        await demo_file_operations()
        await demo_vim_operations()
        await demo_git_operations()

        print("\n" + "=" * 50)
        print("Demo completed successfully!")

    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())