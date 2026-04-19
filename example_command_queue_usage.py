#!/usr/bin/env python3
"""
Example usage of DevMind Command Queue System.

Demonstrates how to use the command queue functionality similar to Claude Code.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.tools import (
    queue_add_tool, queue_list_tool, queue_execute_tool,
    queue_status_tool, create_acp_message
)


async def demonstrate_queue_usage():
    """Demonstrate command queue usage."""
    print("🚀 DevMind Command Queue System Demo")
    print("=" * 50)

    # 1. Add some commands to the queue with different priorities
    print("\n📋 Adding commands to queue...")

    commands_to_add = [
        {
            "command": "agent",
            "description": "Explore codebase structure",
            "args": {
                "subagent_type": "Explore",
                "prompt": "Quick exploration of the project structure"
            },
            "priority": "high"
        },
        {
            "command": "agent",
            "description": "Plan new feature implementation",
            "args": {
                "subagent_type": "Plan",
                "prompt": "Plan implementation of user authentication system"
            },
            "priority": "normal"
        },
        {
            "command": "tool",
            "description": "Read project documentation",
            "args": {
                "tool_name": "Read",
                "file_path": "README.md"
            },
            "priority": "low"
        },
        {
            "command": "git",
            "description": "Create smart commit",
            "args": {
                "message": "Update command queue system",
                "include_files": ["src/core/tools/command_queue/"]
            },
            "priority": "urgent"
        }
    ]

    added_commands = []
    for cmd_data in commands_to_add:
        message = create_acp_message("QueueAdd", cmd_data)
        result = await queue_add_tool.execute(message)

        if result.is_success():
            command_id = result.metadata["command_id"]
            added_commands.append(command_id)
            print(f"✅ Added: {cmd_data['description']} (Priority: {cmd_data['priority']})")
        else:
            print(f"❌ Failed to add: {cmd_data['description']} - {result.error}")

    # 2. Show queue status
    print(f"\n📊 Queue Status (Added {len(added_commands)} commands)...")

    message = create_acp_message("QueueStatus", {"detailed": True})
    result = await queue_status_tool.execute(message)

    if result.is_success():
        print(result.result)

    # 3. List all commands in priority order
    print("\n📝 Queue Contents (Priority Order)...")

    message = create_acp_message("QueueList", {"show_stats": True})
    result = await queue_list_tool.execute(message)

    if result.is_success():
        print(result.result)

    # 4. Execute commands (demo only - won't actually run since handlers may not be fully configured)
    print("\n🚀 Executing Commands (Demo Mode)...")

    # Execute one command as example
    message = create_acp_message("QueueExecute", {
        "count": 1,
        "wait": False
    })
    result = await queue_execute_tool.execute(message)

    if result.is_success():
        print("✅ Execution started:")
        print(result.result)
    else:
        print(f"❌ Execution failed: {result.error}")
        # This is expected since we don't have full tool environment set up
        print("💡 This is expected in demo mode - handlers may not be configured.")

    # 5. Show final status
    print("\n📊 Final Queue Status...")

    message = create_acp_message("QueueStatus", {})
    result = await queue_status_tool.execute(message)

    if result.is_success():
        print(result.result)

    print("\n✨ Demo completed! The queue system is ready for use.")
    print("\n📖 Key Features Demonstrated:")
    print("• ✅ Command queuing with priorities")
    print("• ✅ Queue status monitoring")
    print("• ✅ Priority-based ordering")
    print("• ✅ Comprehensive queue management")
    print("\n🔗 Similar to Claude Code's command queuing functionality!")


async def main():
    """Main demo function."""
    try:
        await demonstrate_queue_usage()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user.")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())