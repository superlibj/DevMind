#!/usr/bin/env python3
"""
Test script to verify tool format fixes with Deepseek model.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.agent.react_agent import ReActAgent
from src.core.llm.llm_factory import llm_factory
from src.core.agent.tools_registry import ToolsRegistry

async def test_tool_format():
    """Test the ReAct agent with a tool-requiring request."""
    print("🧪 Testing DevMind ReAct Agent Tool Format Fixes...")
    print("=" * 60)

    try:
        # Create LLM instance with Deepseek
        llm = llm_factory.create_llm(model="deepseek-chat", timeout=30)
        print(f"✅ Created LLM: deepseek-chat")

        # Create agent components
        tools_registry = ToolsRegistry()

        # Create ReAct agent (it will auto-register tools)
        agent = ReActAgent(
            llm=llm,
            tools_registry=tools_registry,
            max_iterations=3  # Limit iterations for testing
        )

        print(f"✅ Registered {len(tools_registry.list_tools())} tools")
        print("✅ Created ReAct agent")

        # Test request that requires file writing (should trigger tool usage)
        test_request = "Create a simple HTML file called test.html with a basic webpage structure"

        print(f"\n🔍 Testing request: {test_request}")
        print("=" * 60)

        # Process the request
        response = await agent.process_user_message(test_request)

        print(f"\n📋 Agent Response:")
        print("-" * 40)
        print(response)
        print("-" * 40)

        # Check if a file was created
        test_file = Path("test.html")
        if test_file.exists():
            print(f"\n✅ SUCCESS: File created successfully!")
            print(f"File size: {test_file.stat().st_size} bytes")
            print(f"Content preview:")
            content = test_file.read_text()[:200]
            print(f"{content}...")
        else:
            print(f"\n❌ File was not created")

        # Show conversation history to see tool usage
        history = agent.get_conversation_history()
        print(f"\n📝 Conversation History ({len(history)} messages):")
        for i, msg in enumerate(history[-5:], 1):  # Show last 5 messages
            role = msg.get('role', 'unknown').upper()
            content = str(msg.get('content', ''))[:100]
            print(f"  {i}. [{role}] {content}...")

        print("\n🎯 Test completed!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tool_format())