"""
ReAct (Reasoning + Acting) Agent implementation.

This module implements the ReAct pattern for agent behavior:
1. Thought: The agent thinks about what to do
2. Action: The agent performs an action using available tools
3. Observation: The agent observes the result of the action
4. Repeat until the task is complete
"""
import json
import logging
import re
import time
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from ..llm import BaseLLM, LLMMessage, create_llm, ModelCapability
from .memory import ConversationMemory, WorkingMemory, MessageType
from .tools_registry import ToolsRegistry, ToolResult, tools_registry
from config.settings import settings

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """States of the ReAct agent."""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    COMPLETED = "completed"
    ERROR = "error"


class AgentAction:
    """Represents an agent action."""

    def __init__(
        self,
        action_type: str,
        tool_name: str = None,
        arguments: Dict[str, Any] = None,
        reasoning: str = None
    ):
        self.action_type = action_type
        self.tool_name = tool_name
        self.arguments = arguments or {}
        self.reasoning = reasoning


class ReActAgent:
    """ReAct pattern agent for code development tasks."""

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        tools_registry: Optional[ToolsRegistry] = None,
        max_iterations: int = None,
        memory_limit: int = None
    ):
        """Initialize the ReAct agent.

        Args:
            llm: LLM instance to use
            tools_registry: Tools registry instance
            max_iterations: Maximum number of reasoning iterations
            memory_limit: Memory limit for conversation history
        """
        from .tools_registry import tools_registry as default_tools_registry
        from ..llm.llm_factory import llm_factory

        self.llm = llm or create_llm(model=llm_factory.get_recommended_model("code"))
        self.tools = tools_registry or default_tools_registry

        # Ensure tools are registered
        self._register_default_tools()

        self.max_iterations = max_iterations or settings.agent.react_max_steps

        # Initialize memory systems
        self.conversation_memory = ConversationMemory(
            max_messages=memory_limit or settings.agent.conversation_history_limit
        )
        self.working_memory = WorkingMemory()

        # Agent state
        self.state = AgentState.IDLE
        self.current_task = None
        self.iteration_count = 0

        # System prompt for ReAct behavior
        self.system_prompt = self._build_system_prompt()

    def _register_default_tools(self):
        """Register default tools if none are registered."""
        if len(self.tools.list_tools()) == 0:
            logger.info("No tools registered, registering default tools...")

            # Register basic tools
            self._register_basic_tools()

    def _register_basic_tools(self):
        """Register basic development tools."""
        from .tools_registry import ToolParameter, ToolType

        # Register file read tool
        self.tools.register_tool(
            name="file_read",
            function=self._file_read_impl,
            description="Read the contents of a file",
            tool_type=ToolType.FILE_OPERATION,
            parameters=[
                ToolParameter("file_path", str, "Path to the file to read", required=True)
            ]
        )

        # Register file write tool
        self.tools.register_tool(
            name="file_write",
            function=self._file_write_impl,
            description="Write content to a file",
            tool_type=ToolType.FILE_OPERATION,
            parameters=[
                ToolParameter("file_path", str, "Path to the file to write", required=True),
                ToolParameter("content", str, "Content to write to the file", required=True)
            ]
        )

        # Register git status tool
        self.tools.register_tool(
            name="git_status",
            function=self._git_status_impl,
            description="Check git repository status",
            tool_type=ToolType.GIT_OPERATION,
            parameters=[]
        )

        logger.info("Registered basic development tools")

    async def _file_read_impl(self, file_path: str = None, filename: str = None, **kwargs) -> str:
        """Implementation of file read tool."""
        # Handle case where file_path/filename comes in different parameter formats
        # Support both file_path (new standard) and filename (backward compatibility)
        if file_path is None and filename is None and 'input' in kwargs:
            file_path = kwargs['input']

        # Use file_path if available, fallback to filename for backward compatibility
        target_file = file_path or filename

        if target_file is None:
            return "Error: file_path parameter is required"
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"Successfully read file: {target_file}\n\nContent:\n{content}"
        except Exception as e:
            return f"Error reading file {target_file}: {str(e)}"

    async def _file_write_impl(self, file_path: str = None, filename: str = None, content: str = None, **kwargs) -> str:
        """Implementation of file write tool."""
        # Handle case where parameters come in different formats
        # Support both file_path (new standard) and filename (backward compatibility)
        if file_path is None and filename is None and 'input' in kwargs:
            # Try to parse input as JSON or extract file_path/filename/content
            input_data = kwargs['input']
            if isinstance(input_data, dict):
                file_path = input_data.get('file_path') or input_data.get('filename')
                content = input_data.get('content')
            elif isinstance(input_data, str):
                # Try to parse as JSON
                try:
                    parsed = json.loads(input_data)
                    file_path = parsed.get('file_path') or parsed.get('filename')
                    content = parsed.get('content')
                except json.JSONDecodeError:
                    return "Error: Unable to parse input. Expected JSON with file_path and content fields."

        # Use file_path if available, fallback to filename for backward compatibility
        target_file = file_path or filename

        if target_file is None or content is None:
            return "Error: Both file_path and content parameters are required"
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote content to file: {target_file}"
        except Exception as e:
            return f"Error writing to file {target_file}: {str(e)}"

    async def _git_status_impl(self, **kwargs) -> str:
        """Implementation of git status tool."""
        try:
            import subprocess
            result = subprocess.run(['git', 'status'], capture_output=True, text=True)
            if result.returncode == 0:
                return f"Git status:\n{result.stdout}"
            else:
                return f"Git error: {result.stderr}"
        except Exception as e:
            return f"Error running git status: {str(e)}"

    def _build_system_prompt(self) -> str:
        """Build the system prompt for ReAct behavior."""
        return """You are DevMind, an AI code development assistant that helps with programming tasks.

Your primary goal is to be helpful and respond appropriately to user queries.

FOR SIMPLE CONVERSATIONAL QUESTIONS (greetings, questions about yourself, general chat):
- Respond directly without using tools
- Be friendly and conversational
- Use this format:
  Thought: [Brief reasoning]
  Final Answer: [Your direct response]

FOR CODING/DEVELOPMENT TASKS that require analysis or file operations:
- Use the ReAct pattern with available tools
- Follow this format:
  Thought: [Your reasoning about what to do next]
  Action: [EXACT tool name from the available tools list]
  Action Input: [Input for the tool in JSON format]

When you have completed any task or want to provide a final response:
Thought: [Your final reasoning]
Final Answer: [Your complete response to the user]

Available tools:
{tools}

Guidelines:
1. FIRST determine if the query needs tools or if it's a simple conversation
2. For greetings, name questions, or casual chat - respond directly without tools
3. For code tasks - use tools when you need file operations, git commands, or analysis
4. CRITICAL: Action must be an EXACT tool name from the list above, not a description
5. If a tool fails or doesn't exist, provide a helpful response without retrying
6. Never use non-existent tools or hallucinate tool names
6. Break complex tasks into smaller steps
7. Ask for clarification if the task is unclear
8. Always consider security implications of code changes
9. Focus on best practices and clean, maintainable code

Examples:
- User: "What's your name?" → Direct answer, no tools needed
- User: "Fix this bug in my code" → Use tools to read/analyze files
- User: "Hello" → Friendly greeting, no tools needed
"""

    async def process_user_message(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Process a user message and return the agent's response.

        Args:
            message: User message
            context: Additional context

        Returns:
            Agent's response
        """
        logger.info(f"Processing user message: {message[:100]}...")

        # Reset agent state
        self.state = AgentState.IDLE
        self.iteration_count = 0

        # Add user message to memory
        self.conversation_memory.add_user_message(message)

        # Set current task in working memory
        self.working_memory.set_current_task(message, context or {})

        # Handle simple conversational queries directly
        if self._is_simple_conversational_query(message):
            response = self._handle_conversational_query(message)
            self.conversation_memory.add_assistant_message(response)
            return response

        try:
            # Execute ReAct loop for complex tasks
            response = await self._react_loop()

            # Add final response to memory
            self.conversation_memory.add_assistant_message(response)

            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")

            # If LLM fails but it's a conversational query, try built-in responses
            if self._is_simple_conversational_query(message):
                logger.info("LLM failed, falling back to built-in conversational responses")
                response = self._handle_conversational_query(message)
                self.conversation_memory.add_assistant_message(response)
                return response

            error_response = f"I encountered an error while processing your request: {str(e)}"
            self.conversation_memory.add_assistant_message(error_response)
            return error_response

    async def _react_loop(self) -> str:
        """Execute the main ReAct reasoning loop.

        Returns:
            Final response to the user
        """
        consecutive_failures = 0
        max_failures = 3

        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            logger.debug(f"ReAct iteration {self.iteration_count}")

            # Get current conversation context
            messages = self._build_messages_for_llm()

            # Generate response from LLM
            response = await self.llm.generate(messages)
            response_text = response.content.strip()

            logger.debug(f"LLM response: {response_text[:200]}...")

            # Parse the response
            parsed_action = self._parse_response(response_text)

            if parsed_action is None:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    # Too many consecutive failures, provide fallback response
                    logger.warning("Too many parsing failures, providing fallback response")
                    return "I'm having trouble understanding the request format. Let me provide a direct response instead."

                # Invalid format, ask LLM to correct
                self.conversation_memory.add_observation(
                    "Invalid response format. Please use either a direct Final Answer or the Thought/Action/Action Input format."
                )
                continue

            # Reset failure counter on successful parse
            consecutive_failures = 0

            # Handle different action types
            if parsed_action.action_type == "final_answer":
                # Task completed
                self.state = AgentState.COMPLETED
                return parsed_action.arguments.get("answer", response_text)

            elif parsed_action.action_type == "tool_use":
                # Check if tool exists before executing
                tool = self.tools.get_tool(parsed_action.tool_name)
                if tool is None:
                    # Tool doesn't exist, provide helpful response
                    available_tools = [t.name for t in self.tools.list_tools()]
                    error_msg = f"Tool '{parsed_action.tool_name}' is not available. Available tools are: {', '.join(available_tools)}"
                    self.conversation_memory.add_observation(error_msg)

                    # If it's a simple query that doesn't need tools, suggest direct response
                    user_message = self.working_memory.get_current_task().get("task", "")
                    if self._is_simple_conversational_query(user_message):
                        return "I'm DevMind, an AI assistant designed to help with software development tasks. How can I help you with your coding needs today?"
                    continue

                # Execute tool
                await self._execute_tool_action(parsed_action)

            else:
                # Unknown action type
                self.conversation_memory.add_observation(
                    f"Unknown action type: {parsed_action.action_type}. Please use 'Final Answer' to complete the response."
                )

        # Max iterations reached
        logger.warning("Maximum iterations reached in ReAct loop")
        return "I've reached the maximum number of reasoning steps. Let me provide what I've found so far."

    def _build_messages_for_llm(self) -> List[LLMMessage]:
        """Build messages for LLM request.

        Returns:
            List of LLM messages
        """
        messages = []

        # System message with tools
        tools_description = self._get_tools_description()
        system_prompt = self.system_prompt.format(tools=tools_description)

        messages.append(LLMMessage(
            role="system",
            content=system_prompt
        ))

        # Add conversation history
        conversation_messages = self.conversation_memory.get_llm_messages(
            include_thoughts=True,
            include_tools=True,
            limit=20  # Limit to recent context
        )

        for msg_dict in conversation_messages:
            messages.append(LLMMessage(
                role=msg_dict["role"],
                content=msg_dict["content"]
            ))

        return messages

    def _get_tools_description(self) -> str:
        """Get a description of available tools.

        Returns:
            Formatted tools description
        """
        tools = self.tools.list_tools(enabled_only=True)

        if not tools:
            return "No tools are currently available."

        tool_descriptions = []
        for tool in tools:
            if tool.parameters:
                params_desc = []
                json_example = {}
                for p in tool.parameters:
                    type_name = p.type.__name__ if hasattr(p.type, "__name__") else str(p.type)
                    params_desc.append(f"{p.name} ({type_name}): {p.description}")
                    json_example[p.name] = f"<{p.name}_value>"

                json_format = json.dumps(json_example)
                tool_descriptions.append(
                    f"- {tool.name}: {tool.description}\n"
                    f"  Parameters: {', '.join(params_desc)}\n"
                    f"  Usage: Action Input: {json_format}"
                )
            else:
                tool_descriptions.append(
                    f"- {tool.name}: {tool.description}\n"
                    f"  Parameters: None\n"
                    f"  Usage: Action Input: {{}}"
                )

        return "\n".join(tool_descriptions)

    def _parse_response(self, response: str) -> Optional[AgentAction]:
        """Parse LLM response into an AgentAction.

        Args:
            response: LLM response text

        Returns:
            Parsed action or None if invalid format
        """
        # Add the response as a thought
        thought_match = re.search(r"Thought:\s*(.*?)(?=\n(?:Action|Final Answer):|$)", response, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()
            self.conversation_memory.add_thought(thought)
            self.working_memory.add_step("thought", thought)

        # Check for Final Answer
        final_answer_match = re.search(r"Final Answer:\s*(.*)", response, re.DOTALL)
        if final_answer_match:
            answer = final_answer_match.group(1).strip()
            return AgentAction(
                action_type="final_answer",
                arguments={"answer": answer}
            )

        # Check for Action
        action_match = re.search(r"Action:\s*(.*?)(?=\nAction Input:|$)", response, re.DOTALL)
        if not action_match:
            return None

        action_name = action_match.group(1).strip()

        # Validate that action_name is a valid tool name (not a description)
        # Tool names should be short identifiers, not long sentences
        if len(action_name.split()) > 3 or len(action_name) > 50:
            logger.warning(f"Invalid tool name detected: '{action_name}' - treating as invalid format")
            return None

        # Check if the action name contains typical description words
        description_indicators = ['will', 'ensure', 'review', 'the', 'to', 'and', 'that', 'is', 'are', 'for', 'meets', 'requirements']
        action_words = action_name.lower().split()
        if any(word in description_indicators for word in action_words):
            logger.warning(f"Action appears to be a description rather than tool name: '{action_name}'")
            return None

        # Check for Action Input
        action_input_match = re.search(r"Action Input:\s*(.*)", response, re.DOTALL)
        action_input = {}

        if action_input_match:
            input_text = action_input_match.group(1).strip()
            try:
                # Try to parse as JSON
                action_input = json.loads(input_text)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                action_input = {"input": input_text}

        return AgentAction(
            action_type="tool_use",
            tool_name=action_name,
            arguments=action_input,
            reasoning=thought_match.group(1).strip() if thought_match else ""
        )

    async def _execute_tool_action(self, action: AgentAction) -> None:
        """Execute a tool action.

        Args:
            action: Action to execute
        """
        self.state = AgentState.ACTING

        # Record the action
        self.conversation_memory.add_action(
            f"Using tool: {action.tool_name}",
            tool_name=action.tool_name,
            tool_args=action.arguments
        )

        # Execute the tool
        result = await self.tools.execute_tool(
            action.tool_name,
            action.arguments
        )

        # Record the result
        self.state = AgentState.OBSERVING

        if result.success:
            observation = f"Tool execution successful. Result: {result.result}"
            if result.stdout:
                observation += f"\nOutput: {result.stdout}"
        else:
            observation = f"Tool execution failed. Error: {result.error}"
            if result.stderr:
                observation += f"\nError output: {result.stderr}"

        self.conversation_memory.add_observation(observation)
        self.working_memory.add_step(
            "action",
            f"Executed {action.tool_name}",
            result=result.result if result.success else None,
            error=result.error if not result.success else None
        )

        logger.info(f"Tool {action.tool_name} executed: success={result.success}")

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history.

        Returns:
            List of conversation messages
        """
        return [msg.to_dict() for msg in self.conversation_memory.get_messages()]

    def get_task_summary(self) -> Dict[str, Any]:
        """Get a summary of the current task.

        Returns:
            Task summary
        """
        return {
            "state": self.state.value,
            "iteration_count": self.iteration_count,
            "max_iterations": self.max_iterations,
            "current_task": self.working_memory.get_current_task(),
            "working_memory": self.working_memory.get_task_summary(),
            "conversation_length": len(self.conversation_memory),
            "available_tools": len(self.tools.list_tools(enabled_only=True))
        }

    def clear_memory(self) -> None:
        """Clear all memory."""
        self.conversation_memory.clear()
        self.working_memory.clear_task()
        self.state = AgentState.IDLE
        self.current_task = None
        self.iteration_count = 0

        logger.info("Agent memory cleared")

    def _is_simple_conversational_query(self, message: str) -> bool:
        """Check if a message is a simple conversational query that doesn't need tools.

        Args:
            message: The user message

        Returns:
            True if it's a simple conversational query
        """
        message_lower = message.lower().strip()

        # Common conversational patterns (English and Chinese)
        conversational_patterns = [
            # English patterns
            "what is your name", "what's your name", "who are you", "tell me your name",
            "who you are", "hello", "hi", "hey", "greetings", "how are you", "how do you do",
            "what can you do", "what are your capabilities", "help", "assist", "thanks", "thank you",
            "goodbye", "bye", "farewell", "what are you", "introduce yourself",
            # Chinese patterns
            "你叫什么名字", "你叫什么", "你是谁", "你的名字", "名字是什么",
            "你好", "您好", "hi", "hello", "你能做什么", "你可以做什么",
            "帮助", "帮我", "谢谢", "再见", "介绍一下自己", "你是什么"
        ]

        # Check for exact matches or partial matches
        for pattern in conversational_patterns:
            if pattern in message_lower:
                return True

        # Check if message is very short and likely conversational
        if len(message.split()) <= 3 and not any(word in message_lower for word in
            ["code", "bug", "error", "file", "debug", "fix", "write", "read", "analyze"]):
            return True

        return False

    def _handle_conversational_query(self, message: str) -> str:
        """Handle simple conversational queries directly.

        Args:
            message: The user message

        Returns:
            Direct response to the conversational query
        """
        message_lower = message.lower().strip()

        # Detect if message is in Chinese
        is_chinese = any(ord(char) > 127 for char in message)

        # Handle name queries
        name_patterns_en = ["what's your name", "what is your name", "who are you", "tell me your name", "who you are"]
        name_patterns_zh = ["你叫什么名字", "你叫什么", "你是谁", "你的名字", "名字是什么"]

        if any(pattern in message_lower for pattern in name_patterns_en + name_patterns_zh):
            if is_chinese:
                return "我是DevMind，专门为软件开发设计的AI助手。我可以帮助您进行代码生成、审查、重构、调试等各种开发任务。有什么我可以帮助您的吗？"
            else:
                return "I'm DevMind, an AI assistant specifically designed for software development. I can help you with code generation, review, refactoring, debugging, and various development tasks. What can I help you with?"

        # Handle greetings
        greeting_patterns_en = ["hello", "hi", "hey", "greetings"]
        greeting_patterns_zh = ["你好", "您好"]

        if any(pattern in message_lower for pattern in greeting_patterns_en + greeting_patterns_zh):
            if is_chinese:
                return "你好！我是DevMind，您的AI开发助手。我可以帮您处理各种编程任务，包括代码编写、调试、重构和代码审查。请告诉我您需要什么帮助。"
            else:
                return "Hello! I'm DevMind, your AI development assistant. I can help you with various programming tasks including code writing, debugging, refactoring, and code review. Please tell me what you need help with."

        # Handle capability queries
        if any(pattern in message_lower for pattern in ["what can you do", "what are your capabilities", "help", "assist"]):
            return """I'm DevMind, and I can provide the following development services:

🔧 **Code Development**
- Code generation and writing
- Code refactoring and optimization
- Code review and quality checking

🐛 **Debugging Support**
- Error analysis and fixing
- Performance optimization suggestions
- Code logic analysis

📁 **File Operations**
- Reading and editing files
- Project structure analysis
- Git operation support

Please tell me your specific needs, and I'll be happy to help!"""

        # Handle thanks
        if any(pattern in message_lower for pattern in ["thanks", "thank you"]):
            return "You're welcome! I'm glad I could help. If you have any other development questions, feel free to ask me anytime."

        # Handle goodbye
        if any(pattern in message_lower for pattern in ["goodbye", "bye", "farewell"]):
            return "Goodbye! Happy coding, and feel free to reach out if you have any questions."

        # Default conversational response
        return "I'm DevMind, an AI assistant specifically designed for software development. I can help you with various programming tasks. What specific help do you need?"

    def export_session(self) -> Dict[str, Any]:
        """Export the current session.

        Returns:
            Session data
        """
        return {
            "conversation": self.conversation_memory.export_conversation(),
            "working_memory": self.working_memory.get_task_summary(),
            "agent_state": {
                "state": self.state.value,
                "iteration_count": self.iteration_count,
                "current_task": self.current_task
            },
            "export_timestamp": time.time()
        }

    def import_session(self, session_data: Dict[str, Any]) -> None:
        """Import a session.

        Args:
            session_data: Session data to import
        """
        # Import conversation
        if "conversation" in session_data:
            self.conversation_memory.import_conversation(session_data["conversation"])

        # Import agent state
        if "agent_state" in session_data:
            state_data = session_data["agent_state"]
            self.state = AgentState(state_data.get("state", "idle"))
            self.iteration_count = state_data.get("iteration_count", 0)
            self.current_task = state_data.get("current_task")

        logger.info("Session imported successfully")