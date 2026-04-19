"""
Basic tests for ReAct agent framework.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.core.agent import (
    MessageType, MemoryMessage, ConversationMemory, WorkingMemory,
    ToolType, ToolParameter, ToolDefinition, ToolResult, ToolsRegistry,
    AgentState, AgentAction, ReActAgent
)


def test_memory_message_creation():
    """Test MemoryMessage creation and conversion."""
    msg = MemoryMessage(
        type=MessageType.USER,
        content="Hello, assistant!"
    )

    assert msg.type == MessageType.USER
    assert msg.content == "Hello, assistant!"
    assert msg.timestamp is not None

    # Test conversion to LLM format
    llm_msg = msg.to_llm_message()
    assert llm_msg["role"] == "user"
    assert llm_msg["content"] == "Hello, assistant!"


def test_conversation_memory():
    """Test conversation memory functionality."""
    memory = ConversationMemory(max_messages=5)

    # Add messages
    memory.add_user_message("What's 2+2?")
    memory.add_assistant_message("2+2 equals 4.")
    memory.add_thought("I need to think about this...")

    # Check message count
    assert len(memory) == 3

    # Test message filtering
    user_messages = memory.get_messages([MessageType.USER])
    assert len(user_messages) == 1
    assert user_messages[0].content == "What's 2+2?"

    # Test LLM message format
    llm_messages = memory.get_llm_messages()
    assert len(llm_messages) == 3


def test_working_memory():
    """Test working memory functionality."""
    memory = WorkingMemory()

    # Set task
    memory.set_current_task("Calculate 2+2", {"type": "math"})
    assert memory.get_current_task() == "Calculate 2+2"

    # Add steps
    memory.add_step("thought", "I need to add 2 and 2")
    memory.add_step("action", "Performed calculation", result=4)

    # Check history
    history = memory.get_step_history()
    assert len(history) == 2
    assert history[0]["step_type"] == "thought"
    assert history[1]["result"] == 4


def test_tool_parameter():
    """Test tool parameter definition."""
    param = ToolParameter(
        name="filename",
        type=str,
        description="Name of the file to read",
        required=True
    )

    assert param.name == "filename"
    assert param.type == str
    assert param.required is True

    # Test dictionary conversion
    param_dict = param.to_dict()
    assert param_dict["name"] == "filename"
    assert param_dict["type"] == "str"


def test_tool_definition():
    """Test tool definition."""
    def dummy_tool(text: str) -> str:
        return f"Processed: {text}"

    tool_def = ToolDefinition(
        name="process_text",
        description="Process text input",
        tool_type=ToolType.TEXT_PROCESSING,
        function=dummy_tool,
        parameters=[
            ToolParameter("text", str, "Text to process", required=True)
        ]
    )

    assert tool_def.name == "process_text"
    assert tool_def.tool_type == ToolType.TEXT_PROCESSING

    # Test LLM format conversion
    llm_format = tool_def.to_dict()
    assert llm_format["type"] == "function"
    assert llm_format["function"]["name"] == "process_text"


def test_tools_registry():
    """Test tools registry functionality."""
    registry = ToolsRegistry()

    # Register a tool
    def echo_tool(message: str) -> str:
        return f"Echo: {message}"

    registry.register_tool(
        name="echo",
        function=echo_tool,
        description="Echo a message",
        tool_type=ToolType.TEXT_PROCESSING
    )

    # Check tool is registered
    tool = registry.get_tool("echo")
    assert tool is not None
    assert tool.name == "echo"

    # List tools
    tools = registry.list_tools()
    assert len(tools) == 1

    # Get tools for LLM
    llm_tools = registry.get_tools_for_llm()
    assert len(llm_tools) == 1
    assert llm_tools[0]["function"]["name"] == "echo"


@pytest.mark.asyncio
async def test_tool_execution():
    """Test tool execution."""
    registry = ToolsRegistry()

    # Register an async tool
    async def async_tool(value: int) -> int:
        await asyncio.sleep(0.01)  # Simulate async work
        return value * 2

    registry.register_tool(
        name="double",
        function=async_tool,
        description="Double a number",
        tool_type=ToolType.TEXT_PROCESSING
    )

    # Execute the tool
    result = await registry.execute_tool("double", {"value": 5})

    assert result.success is True
    assert result.result == 10
    assert result.execution_time > 0


@pytest.mark.asyncio
async def test_tool_execution_failure():
    """Test tool execution failure handling."""
    registry = ToolsRegistry()

    def failing_tool():
        raise ValueError("This tool always fails")

    registry.register_tool(
        name="fail",
        function=failing_tool,
        description="A tool that fails",
        tool_type=ToolType.TEXT_PROCESSING
    )

    # Execute the failing tool
    result = await registry.execute_tool("fail", {})

    assert result.success is False
    assert "This tool always fails" in result.error


def test_agent_action():
    """Test agent action creation."""
    action = AgentAction(
        action_type="tool_use",
        tool_name="echo",
        arguments={"message": "Hello"},
        reasoning="I need to echo a message"
    )

    assert action.action_type == "tool_use"
    assert action.tool_name == "echo"
    assert action.arguments["message"] == "Hello"


@pytest.mark.asyncio
async def test_react_agent_initialization():
    """Test ReAct agent initialization."""
    # Mock LLM
    mock_llm = Mock()
    mock_llm.generate = AsyncMock()

    # Create agent
    agent = ReActAgent(llm=mock_llm, max_iterations=3)

    assert agent.state == AgentState.IDLE
    assert agent.max_iterations == 3
    assert agent.conversation_memory is not None
    assert agent.working_memory is not None


@pytest.mark.asyncio
@patch('src.core.llm.create_llm')
async def test_react_agent_response_parsing(mock_create_llm):
    """Test ReAct agent response parsing."""
    # Mock LLM
    mock_llm = Mock()
    mock_create_llm.return_value = mock_llm

    agent = ReActAgent()

    # Test final answer parsing
    response = """Thought: The user asked for help with math.
Final Answer: 2 + 2 equals 4."""

    action = agent._parse_response(response)
    assert action.action_type == "final_answer"
    assert "4" in action.arguments["answer"]

    # Test tool action parsing
    response = """Thought: I need to use a calculator.
Action: calculate
Action Input: {"expression": "2+2"}"""

    action = agent._parse_response(response)
    assert action.action_type == "tool_use"
    assert action.tool_name == "calculate"
    assert action.arguments["expression"] == "2+2"


def test_agent_memory_integration():
    """Test integration between agent and memory systems."""
    memory = ConversationMemory()

    # Add various message types
    memory.add_user_message("Hello")
    memory.add_thought("I should respond")
    memory.add_action("Responding to user", "respond", {"message": "Hi"})
    memory.add_observation("User seems friendly")

    # Test that all messages are stored
    assert len(memory) == 4

    # Test LLM message conversion
    llm_messages = memory.get_llm_messages()
    assert len(llm_messages) == 4

    # Test context extraction
    context = memory.get_recent_context()
    assert context["recent_messages"] == 4
    assert "user" in context["message_types"]