#!/usr/bin/env python3
"""
Complete test of the Deepseek fixes: loop protection + enhanced error messages.
"""
import asyncio
import sys
import time
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.cli.streaming_agent import StreamingReActAgent
from src.core.agent.react_agent import ReActAgent
from src.core.llm.llm_factory import llm_factory
from src.core.agent.tools_registry import ToolsRegistry
from src.cli.output_formatter import OutputFormatter
from unittest.mock import AsyncMock, MagicMock

async def test_complete_deepseek_fix():
    """Test the complete Deepseek solution."""
    print("🧪 Testing Complete Deepseek Fix...")
    print("   (Loop Protection + Enhanced Error Messages)")
    print("=" * 70)

    try:
        # Create mock LLM that simulates Deepseek's problematic behavior
        mock_llm = MagicMock()
        mock_response = MagicMock()

        # This is the exact pattern Deepseek generates that causes problems
        mock_response.content = """Thought: I need to create an HTML file with the content.
file_write(input={"file_path": "test.html", "content": "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello World</h1></body></html>"})"""

        mock_response.usage = {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}
        mock_llm.generate = AsyncMock(return_value=mock_response)
        mock_llm.config = MagicMock()
        mock_llm.config.model = "deepseek-chat"  # Trigger Deepseek-specific handling

        # Create agent system
        tools_registry = ToolsRegistry()
        react_agent = ReActAgent(
            llm=mock_llm,
            tools_registry=tools_registry,
            max_iterations=5
        )

        output_formatter = OutputFormatter()
        streaming_agent = StreamingReActAgent(react_agent, output_formatter)

        print(f"✅ Created complete agent system with Deepseek model")
        print(f"   Base agent max iterations: {react_agent.max_iterations}")

        # Test request that would trigger file operations
        test_request = "Create a simple HTML file called test.html"

        print(f"\n🔍 Testing request: '{test_request}'")
        print("   Mock LLM will always return Deepseek-style function calls")
        print("   Expected: Quick termination with Deepseek-specific error messages")
        print("-" * 70)

        start_time = time.time()
        event_count = 0
        deepseek_errors = []
        termination_events = []

        # Process with streaming and collect events
        async for event in streaming_agent.process_user_message_stream(test_request):
            event_count += 1

            # Show key events
            if event.type in ["iteration_start", "error", "observation"]:
                print(f"   {event.type:15} | {event.content[:60]}...")

                # Collect Deepseek-specific error messages
                if event.type == "observation" and "DEEPSEEK" in event.content:
                    deepseek_errors.append(event.content)

            # Collect termination events
            if event.type == "error" and "Multiple format errors" in event.content:
                termination_events.append(event)
                break

            # Safety break
            if event_count > 15:
                print(f"   Breaking after {event_count} events (safety limit)")
                break

        end_time = time.time()
        duration = end_time - start_time

        print("\n" + "=" * 70)
        print("📊 RESULTS SUMMARY:")
        print("-" * 30)
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"🔄 Total events: {event_count}")
        print(f"🚨 Deepseek error messages: {len(deepseek_errors)}")
        print(f"🛑 Termination events: {len(termination_events)}")
        print(f"🔧 Final iteration count: {react_agent.iteration_count}")
        print(f"📞 Mock LLM calls: {mock_llm.generate.call_count}")

        # Analyze results
        success_criteria = {
            "Fast termination": duration < 5,
            "Limited events": event_count < 15,
            "Loop protection": react_agent.iteration_count <= 8,
            "Deepseek error messages": len(deepseek_errors) > 0,
            "Proper termination": len(termination_events) > 0,
            "Limited LLM calls": mock_llm.generate.call_count <= 8
        }

        print(f"\n✅ SUCCESS CRITERIA:")
        print("-" * 30)
        all_passed = True
        for criterion, passed in success_criteria.items():
            status = "✅" if passed else "❌"
            print(f"{status} {criterion}")
            if not passed:
                all_passed = False

        if deepseek_errors:
            print(f"\n📝 DEEPSEEK ERROR MESSAGE SAMPLE:")
            print("-" * 30)
            print(deepseek_errors[0][:200] + "..." if len(deepseek_errors[0]) > 200 else deepseek_errors[0])

        print(f"\n🎯 OVERALL RESULT:")
        print("-" * 30)
        if all_passed:
            print("✅ COMPLETE SUCCESS!")
            print("   🛡️  Infinite loop protection: WORKING")
            print("   💬 Deepseek error messages: ENHANCED")
            print("   ⚡ Fast termination: WORKING")
            print("   💰 Cost control: WORKING")
            print()
            print("🎉 Deepseek infinite loop issue is COMPLETELY FIXED!")
            print("   The agent now terminates quickly with helpful guidance.")
        else:
            print("❌ SOME ISSUES REMAIN")
            print("   Check the failed criteria above.")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complete_deepseek_fix())