#!/usr/bin/env python3
"""
Test script to verify tool format parsing improvements.
This tests the format validation without requiring API calls.
"""
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.agent.react_agent import ReActAgent
from src.core.llm.llm_factory import llm_factory
from src.core.agent.tools_registry import ToolsRegistry

def test_format_parsing():
    """Test the ReAct response parsing with different formats."""
    print("🧪 Testing DevMind ReAct Format Validation...")
    print("=" * 60)

    try:
        # Create agent components
        tools_registry = ToolsRegistry()

        # Create a mock agent (we'll just test the parsing method)
        agent = ReActAgent(
            llm=None,  # We won't call the LLM
            tools_registry=tools_registry,
            max_iterations=1
        )

        print(f"✅ Created agent with {len(tools_registry.list_tools())} tools")

        # Test cases for different response formats
        test_cases = [
            {
                "name": "✅ CORRECT FORMAT - Standard ReAct",
                "response": """Thought: I need to create an HTML file as requested.
Action: file_write
Action Input: {"file_path": "test.html", "content": "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello World!</h1></body></html>"}""",
                "should_succeed": True
            },
            {
                "name": "❌ WRONG FORMAT - Function call syntax",
                "response": """Thought: I need to create an HTML file.
file_write(input={"file_path": "test.html", "content": "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello World!</h1></body></html>"})""",
                "should_succeed": False
            },
            {
                "name": "❌ WRONG FORMAT - Description as action",
                "response": """Thought: I need to create an HTML file.
Action: I will write the HTML content to a file
Action Input: {"file_path": "test.html", "content": "<!DOCTYPE html>"}""",
                "should_succeed": False
            },
            {
                "name": "❌ WRONG FORMAT - Missing Action Input label",
                "response": """Thought: I need to create an HTML file.
Action: file_write
{"file_path": "test.html", "content": "<!DOCTYPE html>"}""",
                "should_succeed": False
            },
            {
                "name": "✅ CORRECT FORMAT - Final Answer",
                "response": """Thought: This is a general question that doesn't require file operations.
Final Answer: I can help you with HTML! Here's a basic structure you can use...""",
                "should_succeed": True
            },
            {
                "name": "❌ WRONG FORMAT - Unknown tool",
                "response": """Thought: I need to write a file.
Action: write_file
Action Input: {"file_path": "test.html", "content": "test"}""",
                "should_succeed": False
            }
        ]

        print("\n🔍 Testing format validation:")
        print("-" * 50)

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. {test_case['name']}")
            print("   Response snippet:", test_case['response'][:80] + "..." if len(test_case['response']) > 80 else test_case['response'])

            try:
                # Test the parsing
                parsed_action = agent._parse_response(test_case['response'])

                if test_case['should_succeed']:
                    if parsed_action is not None:
                        print(f"   ✅ SUCCESS: Parsed correctly as {parsed_action.action_type}")
                        if hasattr(parsed_action, 'tool_name'):
                            print(f"      Tool: {parsed_action.tool_name}")
                    else:
                        print(f"   ❌ FAILED: Expected success but got None")
                else:
                    if parsed_action is None:
                        print(f"   ✅ SUCCESS: Correctly rejected invalid format")
                    else:
                        print(f"   ❌ FAILED: Should have rejected but parsed as {parsed_action.action_type}")

            except Exception as e:
                print(f"   ❌ EXCEPTION: {e}")

        print("\n" + "=" * 60)

        # Show the enhanced error messages that would be provided
        print("\n📝 Error messages that guide Deepseek to correct format:")
        print("-" * 50)

        # Test function call syntax detection
        print("\n🚨 Function call syntax detected:")
        print("   Input: file_write(input={...})")
        print("   Error message generated:")
        agent._parse_response('file_write(input={"file_path": "test.js"})')

        # Check conversation memory for the error message
        if hasattr(agent, 'conversation_memory') and len(agent.conversation_memory.get_messages()) > 0:
            last_msg = agent.conversation_memory.get_messages()[-1]
            if hasattr(last_msg, 'content'):
                print(f"   → {last_msg.content[:200]}...")

        print("\n✅ Format validation test completed!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_format_parsing()