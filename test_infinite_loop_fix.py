#!/usr/bin/env python3
"""
Test script to verify the infinite loop fix.
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

async def test_loop_fix():
    """Test that the agent doesn't get stuck in infinite loops."""
    print("🧪 Testing DevMind Infinite Loop Fix...")
    print("=" * 60)

    try:
        # Create LLM instance with Deepseek (if available) or fallback
        try:
            llm = llm_factory.create_llm(model="deepseek-chat", timeout=10)
            model_name = "deepseek-chat"
            print(f"✅ Created LLM: {model_name}")
        except Exception as e:
            print(f"⚠️ Deepseek unavailable ({e}), using fallback model")
            llm = llm_factory.create_llm(model="gpt-3.5-turbo", timeout=10)
            model_name = "gpt-3.5-turbo"
            print(f"✅ Created LLM: {model_name}")

        # Create agent with LOW max iterations to test termination
        tools_registry = ToolsRegistry()
        agent = ReActAgent(
            llm=llm,
            tools_registry=tools_registry,
            max_iterations=3  # Very low to test early termination
        )

        print(f"✅ Created agent with max_iterations={agent.max_iterations}")

        # Test request that might cause format issues
        test_request = "Create a file called test.html with hello world"

        print(f"\n🔍 Testing request: {test_request}")
        print("=" * 60)

        import time
        start_time = time.time()

        # Process the request - should terminate quickly
        response = await agent.process_user_message(test_request)

        end_time = time.time()
        duration = end_time - start_time

        print(f"\n📋 Agent Response:")
        print("-" * 40)
        print(response)
        print("-" * 40)

        print(f"\n📊 Performance:")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Iterations used: {agent.iteration_count}/{agent.max_iterations}")

        if duration < 30 and agent.iteration_count <= agent.max_iterations:
            print(f"\n✅ SUCCESS: Agent terminated properly!")
            print(f"   - No infinite loop detected")
            print(f"   - Reasonable execution time ({duration:.2f}s)")
            print(f"   - Stayed within iteration limits ({agent.iteration_count}/{agent.max_iterations})")
        else:
            print(f"\n❌ POTENTIAL ISSUE:")
            if duration >= 30:
                print(f"   - Long execution time: {duration:.2f}s")
            if agent.iteration_count > agent.max_iterations:
                print(f"   - Exceeded max iterations: {agent.iteration_count}/{agent.max_iterations}")

        print("\n🎯 Loop protection test completed!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_loop_fix())