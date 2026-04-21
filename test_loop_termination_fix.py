#!/usr/bin/env python3
"""
Test that the loop termination fix actually works.
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

async def test_loop_termination_fix():
    """Test that the loop actually terminates at the hard limit."""
    print("🧪 Testing Loop Termination Fix...")
    print("=" * 60)

    try:
        # Create a mock LLM that always returns bad format (infinite loop scenario)
        mock_llm = MagicMock()
        mock_response = MagicMock()

        # This format will trigger "invalid function call pattern"
        mock_response.content = """Thought: I need to fix this code.
file_write(input={"file_path": "test.html", "content": "test"})"""

        mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        mock_llm.generate = AsyncMock(return_value=mock_response)
        mock_llm.config = MagicMock()
        mock_llm.config.model = "test-model"

        # Create agent with very low max iterations for testing
        tools_registry = ToolsRegistry()
        agent = ReActAgent(
            llm=mock_llm,
            tools_registry=tools_registry,
            max_iterations=5  # Low limit for testing
        )

        print(f"✅ Created agent with max_iterations={agent.max_iterations}")

        # Force a file operation request (won't be detected as conversational)
        test_request = "Write HTML file called index.html with content"

        print(f"\n🔍 Testing request: {test_request}")
        print("   (Mock LLM will always return invalid format)")
        print("=" * 60)

        start_time = time.time()

        # This should terminate at max_loop_iterations (8) or max_iterations (5)
        response = await agent.process_user_message(test_request)

        end_time = time.time()
        duration = end_time - start_time

        print(f"\n📋 Agent Response:")
        print("-" * 40)
        print(response[:300] + "..." if len(response) > 300 else response)
        print("-" * 40)

        print(f"\n📊 Results:")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Final iteration count: {agent.iteration_count}")
        print(f"  Max iterations setting: {agent.max_iterations}")
        print(f"  Mock LLM calls: {mock_llm.generate.call_count}")

        # Check if termination worked properly
        success_indicators = [
            duration < 5,  # Should be very fast
            agent.iteration_count <= 8,  # Should not exceed hard limit
            "formatting issues" in response or "different model" in response,  # Should have helpful message
            mock_llm.generate.call_count <= 8  # Should not call LLM excessively
        ]

        if all(success_indicators):
            print(f"\n✅ SUCCESS: Loop termination working correctly!")
            print(f"   - Fast termination ({duration:.2f}s)")
            print(f"   - Respected iteration limits ({agent.iteration_count}/8)")
            print(f"   - Provided helpful guidance")
            print(f"   - Limited LLM calls ({mock_llm.generate.call_count})")
        else:
            print(f"\n❌ ISSUES DETECTED:")
            if duration >= 5:
                print(f"   - Slow termination: {duration:.2f}s")
            if agent.iteration_count > 8:
                print(f"   - Exceeded hard limit: {agent.iteration_count}/8")
            if not ("formatting issues" in response or "different model" in response):
                print(f"   - Missing helpful guidance")
            if mock_llm.generate.call_count > 8:
                print(f"   - Too many LLM calls: {mock_llm.generate.call_count}")

        print(f"\n🎯 Loop termination test completed!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_loop_termination_fix())