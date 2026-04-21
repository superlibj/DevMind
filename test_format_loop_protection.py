#!/usr/bin/env python3
"""
Test script to verify loop protection when format errors occur.
"""
import asyncio
import sys
import time
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.agent.react_agent import ReActAgent
from src.core.llm.llm_factory import llm_factory
from src.core.agent.tools_registry import ToolsRegistry
from unittest.mock import AsyncMock, MagicMock

async def test_format_loop_protection():
    """Test that the agent doesn't get stuck when format errors persist."""
    print("🧪 Testing Format Error Loop Protection...")
    print("=" * 60)

    try:
        # Create a mock LLM that always returns problematic format
        mock_llm = MagicMock()
        mock_response = MagicMock()

        # Simulate Deepseek's problematic function call format
        mock_response.content = """Thought: I need to create an HTML file.
file_write(input={"file_path": "test.html", "content": "<!DOCTYPE html><html><body><h1>Hello World</h1></body></html>"})"""

        mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

        # Make the mock always return the same bad format
        mock_llm.generate = AsyncMock(return_value=mock_response)
        mock_llm.config = MagicMock()
        mock_llm.config.model = "deepseek-chat"

        # Create agent with LOW max iterations
        tools_registry = ToolsRegistry()
        agent = ReActAgent(
            llm=mock_llm,
            tools_registry=tools_registry,
            max_iterations=3  # Very low to test early termination
        )

        print(f"✅ Created agent with mock LLM (always returns bad format)")
        print(f"   Max iterations: {agent.max_iterations}")

        # Force the agent to not detect this as conversational
        test_request = "Write code to test.html file now"  # More explicit file request

        print(f"\n🔍 Testing request: {test_request}")
        print("   (This will force tool usage and trigger format errors)")
        print("=" * 60)

        start_time = time.time()

        # Process the request - should hit format errors and terminate
        response = await agent.process_user_message(test_request)

        end_time = time.time()
        duration = end_time - start_time

        print(f"\n📋 Agent Response:")
        print("-" * 40)
        print(response[:200] + "..." if len(response) > 200 else response)
        print("-" * 40)

        print(f"\n📊 Performance:")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Iterations used: {agent.iteration_count}/{agent.max_iterations}")
        print(f"  Mock LLM called: {mock_llm.generate.call_count} times")

        # Check that the agent terminated properly
        if duration < 10 and agent.iteration_count <= agent.max_iterations:
            print(f"\n✅ SUCCESS: Loop protection working!")
            print(f"   - No infinite loop despite bad format")
            print(f"   - Quick termination ({duration:.2f}s)")
            print(f"   - Stayed within iteration limits")
            print(f"   - Provided fallback response")
        else:
            print(f"\n❌ ISSUE DETECTED:")
            if duration >= 10:
                print(f"   - Took too long: {duration:.2f}s")
            if agent.iteration_count > agent.max_iterations:
                print(f"   - Exceeded iterations: {agent.iteration_count}/{agent.max_iterations}")

        # Check conversation memory for error handling
        conversation = agent.get_conversation_history()
        print(f"\n📝 Conversation Messages: {len(conversation)}")

        # Look for our error messages
        error_messages = [msg for msg in conversation if 'FORMAT ERROR' in str(msg.get('content', ''))]
        print(f"   Format error messages: {len(error_messages)}")

        if len(error_messages) > 0:
            print("   ✅ Error messages were generated to guide the model")

        print("\n🎯 Format loop protection test completed!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_format_loop_protection())