#!/usr/bin/env python3
"""
Test that the streaming agent infinite loop fix works.
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

async def test_streaming_loop_fix():
    """Test that the streaming agent loop actually terminates."""
    print("🧪 Testing Streaming Agent Loop Termination Fix...")
    print("=" * 60)

    try:
        # Create a mock LLM that always returns bad format
        mock_llm = MagicMock()
        mock_response = MagicMock()

        # This format will trigger "invalid function call pattern"
        mock_response.content = """Thought: I need to create a file.
file_write(input={"file_path": "test.html", "content": "test content"})"""

        mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        mock_llm.generate = AsyncMock(return_value=mock_response)
        mock_llm.config = MagicMock()
        mock_llm.config.model = "test-model"

        # Create react agent and streaming wrapper
        tools_registry = ToolsRegistry()
        react_agent = ReActAgent(
            llm=mock_llm,
            tools_registry=tools_registry,
            max_iterations=5  # Low limit for testing
        )

        # Create streaming agent wrapper
        output_formatter = OutputFormatter()
        streaming_agent = StreamingReActAgent(react_agent, output_formatter)

        print(f"✅ Created streaming agent with max_iterations={react_agent.max_iterations}")

        # Force a file operation request (won't be detected as conversational)
        test_request = "Create an HTML file with content"

        print(f"\n🔍 Testing request: {test_request}")
        print("   (Mock LLM will always return invalid format)")
        print("=" * 60)

        start_time = time.time()
        event_count = 0
        termination_events = []

        # Collect streaming events
        async for event in streaming_agent.process_user_message_stream(test_request):
            event_count += 1
            print(f"   Event {event_count}: {event.type} - {event.content[:60]}...")

            if event.type in ["error", "max_iterations"]:
                termination_events.append(event)
                # Stream should end soon after termination event
                break

            # Safety break to prevent real infinite loops during testing
            if event_count > 20:
                print(f"   ⚠️ Breaking test after {event_count} events (safety limit)")
                break

        end_time = time.time()
        duration = end_time - start_time

        print(f"\n📋 Results:")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Total events: {event_count}")
        print(f"  Termination events: {len(termination_events)}")
        print(f"  Mock LLM calls: {mock_llm.generate.call_count}")
        print(f"  Final iteration count: {react_agent.iteration_count}")

        if termination_events:
            print(f"  Termination reason: {termination_events[0].metadata.get('termination_reason', 'unknown')}")

        # Check success criteria
        success_indicators = [
            duration < 10,  # Should terminate quickly
            event_count < 20,  # Should not generate excessive events
            len(termination_events) > 0,  # Should have termination event
            react_agent.iteration_count <= 8,  # Should respect hard limit
            mock_llm.generate.call_count <= 8  # Should limit LLM calls
        ]

        if all(success_indicators):
            print(f"\n✅ SUCCESS: Streaming loop termination working!")
            print(f"   - Quick termination ({duration:.2f}s)")
            print(f"   - Limited events ({event_count})")
            print(f"   - Proper termination event")
            print(f"   - Respected iteration limits")
        else:
            print(f"\n❌ ISSUES DETECTED:")
            if duration >= 10:
                print(f"   - Slow termination: {duration:.2f}s")
            if event_count >= 20:
                print(f"   - Too many events: {event_count}")
            if len(termination_events) == 0:
                print(f"   - No termination event")
            if react_agent.iteration_count > 8:
                print(f"   - Exceeded hard limit: {react_agent.iteration_count}")

        print(f"\n🎯 Streaming loop fix test completed!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_streaming_loop_fix())