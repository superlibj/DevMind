#!/usr/bin/env python3
"""
Test the Deepseek-specific format fix to see if it provides better guidance.
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

async def test_deepseek_format_fix():
    """Test that Deepseek gets better error messages."""
    print("🧪 Testing Deepseek-Specific Format Fix...")
    print("=" * 60)

    try:
        # Create mock LLMs for both Deepseek and regular models
        test_cases = [
            {
                "model_name": "deepseek-chat",
                "is_deepseek": True,
                "expected_text": "DEEPSEEK FORMAT ERROR"
            },
            {
                "model_name": "gpt-3.5-turbo",
                "is_deepseek": False,
                "expected_text": "WRONG FORMAT DETECTED"
            }
        ]

        for test_case in test_cases:
            print(f"\n🔍 Testing {test_case['model_name']}:")
            print("-" * 40)

            # Create mock LLM
            mock_llm = MagicMock()
            mock_response = MagicMock()

            # Problematic Deepseek-style response
            mock_response.content = """Thought: I need to create a file.
file_write(input={"file_path": "test.html", "content": "<!DOCTYPE html><html><body>Hello</body></html>"})"""

            mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            mock_llm.generate = AsyncMock(return_value=mock_response)
            mock_llm.config = MagicMock()
            mock_llm.config.model = test_case["model_name"]

            # Create agent
            tools_registry = ToolsRegistry()
            agent = ReActAgent(
                llm=mock_llm,
                tools_registry=tools_registry,
                max_iterations=2
            )

            print(f"✅ Created agent with model: {test_case['model_name']}")

            # Test the system prompt generation
            system_prompt = agent._build_system_prompt()
            if test_case['is_deepseek'] and "DEEPSEEK SPECIFIC WARNING" in system_prompt:
                print("✅ System prompt contains Deepseek-specific warnings")
            elif not test_case['is_deepseek'] and "DEEPSEEK SPECIFIC WARNING" not in system_prompt:
                print("✅ System prompt uses standard format for non-Deepseek models")
            else:
                print("❌ System prompt issue")

            # Test error message generation
            parsed_action = agent._parse_response(mock_response.content)

            # Should be None due to format error
            if parsed_action is None:
                print("✅ Correctly rejected invalid format")

                # Check the error message that was added to conversation memory
                messages = agent.conversation_memory.get_messages()
                if messages:
                    last_message = messages[-1]
                    error_content = last_message.content if hasattr(last_message, 'content') else str(last_message)

                    if test_case['expected_text'] in error_content:
                        print(f"✅ Generated {test_case['model_name']}-appropriate error message")

                        if test_case['is_deepseek']:
                            if "DEEPSEEK" in error_content and "FORBIDDEN" in error_content:
                                print("✅ Deepseek error contains strong warnings")
                            else:
                                print("❌ Deepseek error missing strong language")

                        # Show a snippet of the error message
                        print(f"   Message preview: {error_content[:100]}...")
                    else:
                        print(f"❌ Error message doesn't contain expected text: {test_case['expected_text']}")
                        print(f"   Actual: {error_content[:100]}...")
                else:
                    print("❌ No error message generated")
            else:
                print("❌ Should have rejected invalid format")

        print("\n" + "=" * 60)
        print("🎯 Deepseek format fix test completed!")
        print("\nThe enhanced error messages should help Deepseek understand")
        print("the correct format better and reduce infinite loops.")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_deepseek_format_fix())