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
            input_data = kwargs['input']
            if isinstance(input_data, dict):
                file_path = input_data.get('file_path') or input_data.get('filename')
            elif isinstance(input_data, str):
                file_path = input_data

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
        # Check if we're using Deepseek and need extra guidance
        is_deepseek = hasattr(self.llm, 'config') and 'deepseek' in self.llm.config.model.lower()

        base_prompt = """You are DevMind, an AI code development assistant that helps with programming tasks.

IMPORTANT: Most questions can be answered directly without tools! Only use tools when you absolutely need to read/write files or execute commands.

FOR MOST QUERIES - Give direct answers using this format:
Thought: [Brief reasoning about why no tools are needed]
Final Answer: [Your complete helpful response]

ONLY use tools for these specific cases:
- Reading actual files from the filesystem
- Writing/editing files
- Git operations
- Running system commands

🌍 MANDATORY TOOL USAGE - NO EXCEPTIONS:
- ANY weather question (current, today, tomorrow, forecasts) → MUST use Weather tool
- ANY location question (where am I, current location) → MUST use Location tool
- NEVER try to answer weather/location from memory or reasoning - ALWAYS use the appropriate tool

Available tools:
{tools}

🚨 MANDATORY FORMAT REQUIREMENTS 🚨

When using tools, you MUST use this EXACT format:

Action: [exact_tool_name]
Action Input: [valid_json_object]

❌ NEVER EVER use these WRONG formats:
- file_write(input={{"file_path": "test.js"}})  ← FUNCTION CALL SYNTAX - FORBIDDEN
- tool_name(args)  ← ANY FUNCTION CALL SYNTAX - FORBIDDEN
- file_write({{"file_path": "test.js"}})  ← MISSING "Action Input:" - FORBIDDEN
- Action: I will write a file  ← DESCRIPTION AS ACTION - FORBIDDEN
- Action: write the code to file  ← SENTENCE AS ACTION - FORBIDDEN

✅ ONLY use this CORRECT format:
Action: file_write
Action Input: {{"file_path": "test.js", "content": "console.log('hello')"}}

🔥 CRITICAL RULES:
1. Action MUST be EXACTLY one word from the available tool names (see tools list above)
2. Action Input MUST be valid JSON with double quotes
3. NEVER use function call syntax like tool_name(args)
4. NEVER use descriptions or sentences as Action names
5. If you're unsure about format, use Final Answer instead
6. AFTER A SUCCESSFUL TOOL EXECUTION: Immediately provide Final Answer with the result
7. NEVER continue thinking after a tool gives you the information you need

Examples:

USER: "Review my HTML file for errors"
Thought: I can provide general HTML review guidance without reading the actual file
Final Answer: I can help you review HTML for common issues...

USER: "Read the contents of index.html"
Thought: The user wants me to read a specific file
Action: file_read
Action Input: {{"file_path": "index.html"}}

USER: "Create a simple JavaScript file"
Thought: The user wants me to create a file with JavaScript code
Action: file_write
Action Input: {{"file_path": "script.js", "content": "console.log('Hello, World!');"}}

USER: "How do I fix JavaScript errors?"
Thought: This is asking for general advice, no file access needed
Final Answer: Here are common ways to debug JavaScript errors...

USER: "What's the weather today?"
Thought: User wants current weather information, I need to use the Weather tool
Action: Weather
Action Input: {{"location": "current", "forecast_days": 1}}
Observation: Weather for Current Location: Current conditions: Temperature: 15.7 C...
Thought: Perfect! I have the weather information the user requested
Final Answer: Based on the current weather data, today's weather is 15.7°C with overcast conditions...

USER: "What's the weather the day after tomorrow?"
Thought: User wants weather forecast for day after tomorrow, I need to get a 3-day forecast
Action: Weather
Action Input: {{"location": "current", "forecast_days": 3}}
Observation: Weather for Current Location: Forecast: Today: 14 to 16 C... Tomorrow: 12 to 15 C... Day after tomorrow: 11 to 21 C, Mainly clear
Thought: Perfect! The forecast shows day after tomorrow will be 11-21°C and mainly clear
Final Answer: The day after tomorrow's weather will be mainly clear with temperatures ranging from 11 to 21°C.

⚠️ FORMAT VIOLATIONS WILL CAUSE ERRORS:
❌ Action: file_write(input={{"file_path": "test.js", "content": "code"}})
❌ Action: Read the file and analyze it
❌ Action: write_file
❌ file_read({{"file_path": "test.js"}})

✅ ONLY CORRECT FORMAT:
Action: file_read
Action Input: {{"file_path": "test.js"}}

🛑 CRITICAL TERMINATION RULE:
When a tool returns the information requested by the user, IMMEDIATELY provide Final Answer.
Do NOT continue thinking, planning, or executing more actions.

🌤️ WEATHER/LOCATION ENFORCEMENT:
❌ NEVER do this for weather questions:
Thought: The weather is usually nice this time of year
Final Answer: I don't have current weather data...

✅ ALWAYS do this for ANY weather question:
Thought: User is asking about weather, I MUST use the Weather tool
Action: Weather
Action Input: {"location": "current", "forecast_days": 3}

❌ NEVER try to answer weather questions without tools
❌ NEVER say "I don't have weather information"
✅ ALWAYS use Weather tool for ANY weather-related query
The user asked a question, you got the answer via tool, now give Final Answer.

Guidelines:
1. DEFAULT to direct answers - tools are the exception, not the rule
2. Only use tools when you absolutely must access files/commands
3. Use EXACT format: "Action: tool_name" then "Action Input: json_object"
4. When unsure about format, always choose Final Answer over tools
5. Be helpful and comprehensive in your direct answers
"""

        # Add extra Deepseek-specific guidance if needed
        if is_deepseek:
            deepseek_addendum = """

🚨🚨🚨 CRITICAL DEEPSEEK FORMAT RULES 🚨🚨🚨

DEEPSEEK: You are known to use WRONG function call syntax. This BREAKS the system.
Follow these rules EXACTLY or your response will be REJECTED:

❌ DEEPSEEK FORBIDDEN PATTERNS (NEVER USE):
❌ file_write(input={{"file_path": "test.js"}})    ← NEVER parentheses
❌ file_read(input={{"file_path": "test.js"}})     ← NEVER parentheses
❌ any_tool_name({{"arg": "value"}})                ← NEVER parentheses
❌ any_tool_name(arg=value)                        ← NEVER parentheses
❌ function_style_calls()                          ← NEVER parentheses

✅ DEEPSEEK REQUIRED FORMAT (ONLY USE THIS):
✅ Action: file_write
✅ Action Input: {{"file_path": "test.js", "content": "code"}}

✅ Action: file_read
✅ Action Input: {{"file_path": "test.js"}}

✅ DEEPSEEK STEP-BY-STEP:
1. Write "Thought: [your thinking]"
2. Write "Action: [tool_name]" (NO PARENTHESES!)
3. Write "Action Input: [json]" (NO PARENTHESES!)

✅ DEEPSEEK PREFERRED METHOD - USE FINAL ANSWER:
DeepSeek works BEST with Final Answer. Use this pattern:

Thought: Let me analyze the snake game issue...
Final Answer: I found the bug in the snake game...

This is EASIER than tools and gives complete answers!

✅ ONLY use tools if you ABSOLUTELY need to read/write files or get weather/location.
✅ For analysis, debugging, explanations: USE FINAL ANSWER!
✅ After ANY successful tool execution: IMMEDIATELY give Final Answer!
✅ Weather tool gives you weather → Final Answer with weather info
✅ Location tool gives you location → Final Answer with location info
✅ File tool gives you content → Final Answer with the content

DEEPSEEK RULES:
- NEVER write tool_name() with parentheses
- NEVER write tool_name(args)
- NEVER write input= syntax
- ALWAYS write "Action:" on separate line
- ALWAYS write "Action Input:" on separate line

🚨🚨🚨 DEEPSEEK: PARENTHESES = INSTANT FAILURE 🚨🚨🚨
"""
            return base_prompt + deepseek_addendum

        return base_prompt

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

            # Provide specific help for different types of API issues
            error_str = str(e).lower()
            if "504 gateway timeout" in error_str or "cloudfront" in error_str or "infrastructure" in error_str:
                error_response = """🚨 **API Infrastructure Issue Detected**

The API service is currently experiencing server problems (504 Gateway Timeout). This is **not a problem with your request or DevMind** - it's a temporary infrastructure issue on the provider's side.

🔄 **Immediate Solutions:**
1. **Switch models**: `/model gpt-3.5-turbo` or `/model claude-3-sonnet-20240229`
2. **Wait and retry**: Try again in 15-30 minutes when servers recover
3. **Check service status**: Visit the provider's status page

🚀 **Working Alternatives:**
- **OpenAI**: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo-preview`
- **Anthropic**: `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`
- **Local**: Use `/local` for Ollama or llama.cpp models

This type of error typically resolves automatically within 30 minutes."""

            elif "deepseek" in error_str and "json" in error_str:
                error_response = """I'm experiencing issues with the Deepseek API. Here are some solutions to try:

🔧 **Immediate Solutions:**
1. Switch to a working model: `/model gpt-3.5-turbo` or `/model claude-3-sonnet-20240229`
2. Check your API key: `export DEEPSEEK_API_KEY=your_key_here`
3. Verify you have API quota remaining at https://platform.deepseek.com

🔄 **Alternative Models:**
- OpenAI: `gpt-3.5-turbo`, `gpt-4`
- Anthropic: `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`
- Local: `/local` to see available local models (Ollama/llama.cpp)

The Deepseek API seems to be returning empty or malformed responses. This is often temporary and may resolve itself, or could indicate API quota/authentication issues."""

            elif "timeout" in error_str:
                error_response = f"""⏱️ **Request Timeout**

The API request timed out. This could be due to:
• High API server load
• Network connectivity issues
• Large request processing time

🔄 **Solutions:**
1. **Retry**: Often works on second attempt
2. **Switch models**: Try `/model gpt-3.5-turbo` for faster responses
3. **Simplify request**: Break complex tasks into smaller parts
4. **Check network**: Ensure stable internet connection"""

            else:
                error_response = f"I encountered an error while processing your request: {str(e)}"
            self.conversation_memory.add_assistant_message(error_response)
            return error_response

    async def _react_loop(self) -> str:
        """Execute the main ReAct reasoning loop.

        Returns:
            Final response to the user
        """
        consecutive_failures = 0
        max_failures = 2  # Maximum consecutive failures before fallback
        max_loop_iterations = self.max_iterations  # Use configured max_iterations
        format_error_history = []  # Track repeated format errors

        while True:  # Use infinite loop with explicit breaks
            self.iteration_count += 1
            logger.debug(f"ReAct iteration {self.iteration_count}/{max_loop_iterations}")

            # Check termination conditions FIRST
            if self.iteration_count >= max_loop_iterations:
                logger.warning(f"Reached maximum loop iterations ({max_loop_iterations}), terminating")
                current_task = self.working_memory.get_current_task()
                # Handle both string and dict return types
                if isinstance(current_task, dict):
                    user_message = current_task.get("task", "your request")
                else:
                    user_message = str(current_task) if current_task else "your request"
                return f"I've attempted to process your request but encountered persistent formatting issues. For the task '{user_message[:100]}...', I recommend trying with a different model or simplifying the request. You can use `/model gpt-3.5-turbo` or `/model claude-3-sonnet-20240229` for more reliable results."

            if self.iteration_count >= self.max_iterations:
                logger.warning(f"Reached maximum iterations ({self.max_iterations}), terminating")
                current_task = self.working_memory.get_current_task()
                # Handle both string and dict return types
                if isinstance(current_task, dict):
                    user_message = current_task.get("task", "your request")
                else:
                    user_message = str(current_task) if current_task else "your request"
                return f"I've reached the maximum number of reasoning steps while processing '{user_message[:100]}...'. Please try simplifying your request or using a different model."

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

                # Track what type of format error this is
                error_type = "unknown"
                if "function call pattern" in response_text.lower():
                    error_type = "function_call"
                elif "action:" not in response_text.lower():
                    error_type = "missing_action"
                elif "invalid tool name" in str(self.conversation_memory.get_messages()[-1:]):
                    error_type = "invalid_tool"

                format_error_history.append(error_type)

                # Check for repeated identical errors (indicates model is stuck)
                if len(format_error_history) >= 3:
                    recent_errors = format_error_history[-3:]
                    if len(set(recent_errors)) == 1:  # All same error type
                        logger.warning(f"Detected repeated format error pattern: {error_type}")
                        current_task = self.working_memory.get_current_task()
                        if isinstance(current_task, dict):
                            user_message = current_task.get("task", "your request")
                        else:
                            user_message = str(current_task) if current_task else "your request"

                        # Provide a helpful fallback response based on the original request
                        if "create" in user_message.lower() or "write" in user_message.lower():
                            return "I understand you want me to create or write something. Due to technical formatting issues, I can't execute file operations right now. Please try using a different model like `/model gpt-3.5-turbo` for file creation tasks, or provide your request in a different way."
                        else:
                            return f"I've encountered persistent formatting issues while processing your request about '{user_message[:100]}...'. Please try switching to a more compatible model using `/model claude-3-sonnet-20240229` or `/model gpt-3.5-turbo`."

                if consecutive_failures >= max_failures:
                    # Too many consecutive failures, provide helpful fallback response
                    logger.warning("Too many parsing failures, providing direct answer")
                    current_task = self.working_memory.get_current_task()
                    if isinstance(current_task, dict):
                        user_message = current_task.get("task", "your request")
                    else:
                        user_message = str(current_task) if current_task else "your request"

                    # Try to extract useful response from the raw LLM output
                    if "Final Answer:" in response_text:
                        final_answer_match = re.search(r"Final Answer:\s*(.*)", response_text, re.DOTALL)
                        if final_answer_match:
                            return final_answer_match.group(1).strip()

                    # Clear some conversation history to prevent context pollution
                    messages = self.conversation_memory.get_messages()
                    if len(messages) > 10:
                        # Keep first few messages (user request) and remove middle error messages
                        self.conversation_memory._messages = messages[:3] + messages[-2:]
                        logger.debug("Cleared conversation history to prevent context pollution")

                    # Generic helpful response
                    return f"I can help you with that request. Based on your question about '{user_message[:50]}...', I'd recommend checking the relevant documentation or providing more specific details about what you need assistance with."

                # Only add error message if we haven't seen this error type repeatedly
                if format_error_history.count(error_type) <= 2:
                    error_msg = f"""🚨 FORMAT ERROR #{consecutive_failures}/{max_failures} 🚨

CRITICAL: You MUST use this EXACT format:

Action: [exact_tool_name]
Action Input: [valid_json]

Available tools: {', '.join([tool.name for tool in self.tools.list_tools(enabled_only=True)])}

❌ FORBIDDEN: file_write(input={{...}}) ← NEVER use this syntax
❌ FORBIDDEN: Descriptions as actions

✅ REQUIRED:
Action: file_write
Action Input: {{"file_path": "test.js", "content": "code here"}}

OR use Final Answer if no tools needed."""

                    self.conversation_memory.add_observation(error_msg)
                else:
                    # Stop adding error messages for repeated errors
                    logger.warning(f"Suppressing repeated error message for {error_type}")

                continue

            # Reset failure counter on successful parse
            consecutive_failures = 0
            format_error_history.clear()  # Clear error history on success

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
                    current_task = self.working_memory.get_current_task()
                    if isinstance(current_task, dict):
                        user_message = current_task.get("task", "your request")
                    else:
                        user_message = str(current_task) if current_task else "your request"
                    if self._is_simple_conversational_query(user_message):
                        return "I'm DevMind, an AI assistant designed to help with software development tasks. How can I help you with your coding needs today?"
                    continue

                # Execute tool
                final_answer = await self._execute_tool_action(parsed_action)

                # If tool returns a final answer, terminate loop immediately
                if final_answer is not None:
                    logger.info(f"Tool {parsed_action.tool_name} returned final answer - terminating loop")
                    self.state = AgentState.COMPLETED
                    return final_answer

            else:
                # Unknown action type
                self.conversation_memory.add_observation(
                    f"Unknown action type: {parsed_action.action_type}. Please use 'Final Answer' to complete the response."
                )

        # This should never be reached due to explicit termination checks above
        logger.error("ReAct loop exited unexpectedly without explicit termination")
        return "An unexpected error occurred during processing. Please try again or use a different model."

    def _build_messages_for_llm(self) -> List[LLMMessage]:
        """Build messages for LLM request.

        Returns:
            List of LLM messages
        """
        messages = []

        # System message with tools
        tools_description = self._get_tools_description()
        # Use simple string replacement to avoid conflicts with JSON braces in the prompt
        system_prompt = self.system_prompt.replace('{tools}', tools_description)

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

        # Check for function call syntax (WRONG FORMAT) and provide helpful error
        function_call_match = re.search(r"(\w+)\s*\(\s*input\s*=\s*(\{.*?\})\s*\)", response, re.DOTALL)
        if function_call_match:
            tool_name = function_call_match.group(1)
            input_json = function_call_match.group(2)

            logger.warning(f"Detected function call syntax: {tool_name}(input={input_json})")

            # Check if this is a Deepseek model for specialized error message
            is_deepseek = hasattr(self.llm, 'config') and 'deepseek' in self.llm.config.model.lower()

            if is_deepseek:
                error_msg = f"""🚨 DEEPSEEK FORMAT ERROR 🚨

You used: {tool_name}(input={input_json})
This is WRONG! Deepseek models must NEVER use function call syntax.

DEEPSEEK CORRECT FORMAT:
Action: {tool_name}
Action Input: {input_json}

DEEPSEEK RULES:
- NEVER use parentheses: {tool_name}() ❌
- NEVER use input= syntax ❌
- ALWAYS use "Action:" label ✅
- ALWAYS use "Action Input:" label ✅

DEEPSEEK: You MUST follow this exact format or your response will be rejected."""
            else:
                error_msg = f"""WRONG FORMAT DETECTED: {tool_name}(input=...)

CORRECT FORMAT:
Action: {tool_name}
Action Input: {input_json}

Please use the exact format shown above. Do NOT use function call syntax like {tool_name}(input=...)."""

            self.conversation_memory.add_observation(error_msg)
            return None

        # Check for specific tool function call patterns (avoid false positives)
        # Only flag actual tool names followed by parentheses, not general text
        tool_names = ["file_read", "file_write", "git_status"]  # Known tools
        invalid_patterns = []

        for tool in tool_names:
            # Match specific tool names followed by parentheses
            invalid_patterns.append(rf"\b{tool}\s*\([^)]*\)")  # tool_name(args)
            invalid_patterns.append(rf"\b{tool}\s*\(\s*input\s*=")  # tool_name(input=

        # Also catch generic function call syntax that's clearly meant as tools
        invalid_patterns.extend([
            r"^\s*\w+\s*\(\s*input\s*=",  # line starts with tool_name(input=
            r"^\s*\w+\s*\(\s*\{",  # line starts with tool_name({
        ])

        for pattern in invalid_patterns:
            if re.search(pattern, response):
                logger.warning(f"Detected invalid function call pattern in: {response[:100]}...")

                # Check if this is a Deepseek model for specialized error message
                is_deepseek = hasattr(self.llm, 'config') and 'deepseek' in self.llm.config.model.lower()

                if is_deepseek:
                    error_msg = """🚨 DEEPSEEK CRITICAL ERROR 🚨

YOU USED PARENTHESES! This is completely forbidden for Deepseek.

YOUR MISTAKE: You wrote something like tool_name()
SYSTEM RULE: Deepseek CANNOT use function call syntax

✅ CORRECT FORMAT ONLY:
Action: file_read
Action Input: {{"file_path": "file.txt"}}

❌ WHAT YOU DID WRONG:
- Used parentheses () ← FORBIDDEN
- Used function call syntax ← FORBIDDEN

DEEPSEEK: Delete all parentheses! Use Action: format only!

DEEPSEEK: Use the Action/Action Input format ONLY."""
                else:
                    error_msg = """INVALID FORMAT: Function call syntax detected.

REQUIRED FORMAT:
Action: [tool_name]
Action Input: {json_object}

Do NOT use function call syntax like tool_name(args). Use the exact format above."""

                self.conversation_memory.add_observation(error_msg)
                return None

        # Check for proper Action format
        action_match = re.search(r"Action:\s*(.*?)(?=\nAction Input:|$)", response, re.DOTALL)
        if not action_match:
            # Check if there's any tool-like content that might indicate a format error
            tool_names = ['file_read', 'file_write', 'git_status']
            for tool in tool_names:
                if tool in response.lower() and 'action:' not in response.lower():
                    error_msg = f"""FORMAT ERROR: Tool name '{tool}' detected but not in proper format.

REQUIRED FORMAT:
Action: {tool}
Action Input: {{json_object}}

Make sure to use 'Action:' followed by the exact tool name."""
                    self.conversation_memory.add_observation(error_msg)
                    return None

            # No action found and no tool names detected - this might be meant as a final answer
            return None

        action_name = action_match.group(1).strip()

        # Validate that action_name is a valid tool name (not a description)
        # Tool names should be short identifiers, not long sentences
        if len(action_name.split()) > 2 or len(action_name) > 30:
            logger.warning(f"Invalid tool name detected: '{action_name}' - treating as invalid format")
            available_tools = [tool.name for tool in self.tools.list_tools(enabled_only=True)]
            error_msg = f"""INVALID ACTION NAME: '{action_name}'

Action must be EXACTLY one of these tool names: {', '.join(available_tools)}
Do NOT use descriptions or sentences as action names.

Example:
✅ Action: file_read
❌ Action: I will read the file to check for errors"""
            self.conversation_memory.add_observation(error_msg)
            return None

        # Check if the action name contains typical description words or phrases
        description_indicators = [
            'will', 'ensure', 'review', 'the', 'to', 'and', 'that', 'is', 'are',
            'for', 'meets', 'requirements', 'check', 'open', 'console', 'browser',
            'any', 'errors', 'in', 'your', 'web', 'javascript', 'html', 'css',
            'this', 'file', 'appears', 'contains', 'necessary', 'elements'
        ]
        action_words = action_name.lower().split()
        if len(action_words) > 2 or any(word in description_indicators for word in action_words):
            logger.warning(f"Action appears to be a description rather than tool name: '{action_name}'")
            available_tools = [tool.name for tool in self.tools.list_tools(enabled_only=True)]
            error_msg = f"""ACTION IS A DESCRIPTION: '{action_name}'

Action must be EXACTLY one of these tool names: {', '.join(available_tools)}
Do NOT use descriptions. Use the exact tool name only.

Example:
✅ Action: file_write
❌ Action: write the code to a file"""
            self.conversation_memory.add_observation(error_msg)
            return None

        # Additional check: if it contains punctuation typical of sentences
        if any(char in action_name for char in ['.', '!', '?', ',']):
            logger.warning(f"Action contains sentence punctuation: '{action_name}'")
            error_msg = f"""INVALID ACTION FORMAT: '{action_name}'

Action names cannot contain punctuation like . ! ? ,
Use only the exact tool name without punctuation.

Available tools: {', '.join([tool.name for tool in self.tools.list_tools(enabled_only=True)])}"""
            self.conversation_memory.add_observation(error_msg)
            return None

        # Verify the action name is a valid tool
        available_tools = [tool.name for tool in self.tools.list_tools(enabled_only=True)]
        if action_name not in available_tools:
            error_msg = f"""UNKNOWN TOOL: '{action_name}'

Available tools are: {', '.join(available_tools)}
Use EXACTLY one of these tool names (case-sensitive).

Example:
✅ Action: file_read
❌ Action: read_file"""
            self.conversation_memory.add_observation(error_msg)
            return None

        # Check for Action Input
        action_input_match = re.search(r"Action Input:\s*(.*)", response, re.DOTALL)
        action_input = {}

        if action_input_match:
            input_text = action_input_match.group(1).strip()
            try:
                # Try to parse as JSON
                action_input = json.loads(input_text)
            except json.JSONDecodeError as e:
                # If not JSON, provide helpful error with exact input for debugging
                error_msg = f"""INVALID JSON in Action Input: {input_text[:200]}
JSON Error: {str(e)}

Action Input must be valid JSON format:
✅ Action Input: {{"file_path": "example.js", "content": "code here"}}
❌ Action Input: file_path: example.js, content: code here

Check your JSON syntax - make sure to use double quotes and proper formatting.
Received input: '{input_text}'"""
                self.conversation_memory.add_observation(error_msg)
                logger.error(f"JSON parsing error for action input: '{input_text}' - Error: {e}")
                return None

        return AgentAction(
            action_type="tool_use",
            tool_name=action_name,
            arguments=action_input,
            reasoning=thought_match.group(1).strip() if thought_match else ""
        )

    async def _execute_tool_action(self, action: AgentAction) -> Optional[str]:
        """Execute a tool action.

        Args:
            action: Action to execute

        Returns:
            Optional final answer if tool execution should terminate the loop,
            None to continue normal ReAct flow
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
            # For weather and location tools, immediately return final answer to bypass loop
            if action.tool_name in ["Weather", "Location"]:
                logger.info(f"Weather/Location tool {action.tool_name} successful - returning final answer immediately")

                # Format the final answer based on the original user query
                current_task = self.working_memory.get_current_task()
                if isinstance(current_task, dict):
                    user_query = current_task.get("task", "").lower()
                else:
                    user_query = str(current_task).lower() if current_task else ""

                final_answer = self._format_weather_location_answer(action.tool_name, result.result, user_query)

                # Still record the action for completeness
                self.conversation_memory.add_observation(f"Tool execution successful. Result: {result.result}")
                self.working_memory.add_step(
                    "action",
                    f"Executed {action.tool_name}",
                    result=result.result,
                    error=None
                )

                # Return final answer to terminate loop
                return final_answer

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

        # Return None to continue normal ReAct flow
        return None

    def _format_weather_location_answer(self, tool_name: str, tool_result: str, user_query: str) -> str:
        """Format a natural final answer for weather/location queries.

        Args:
            tool_name: Name of the tool that was executed
            tool_result: Raw result from the tool
            user_query: Original user query (lowercase)

        Returns:
            Formatted final answer
        """
        if tool_name == "Weather":
            # Extract key information from weather result
            if "day after tomorrow" in user_query:
                # Look for day after tomorrow info in the result
                lines = tool_result.split('\n')
                for line in lines:
                    if "day after tomorrow" in line.lower():
                        # Extract the weather info for day after tomorrow
                        weather_info = line.replace("Day after tomorrow:", "").strip()
                        return f"The day after tomorrow's weather will be {weather_info}."

                # Fallback if specific line not found
                return f"Based on the forecast, here's the weather information:\n\n{tool_result}"

            elif "tomorrow" in user_query and "day after" not in user_query:
                # Look for tomorrow info
                lines = tool_result.split('\n')
                for line in lines:
                    if "tomorrow" in line.lower():
                        weather_info = line.replace("Tomorrow:", "").strip()
                        return f"Tomorrow's weather will be {weather_info}."

                return f"Here's tomorrow's weather information:\n\n{tool_result}"

            elif "today" in user_query:
                # Extract current conditions
                if "Current conditions:" in tool_result:
                    parts = tool_result.split("Current conditions:")
                    if len(parts) > 1:
                        current_info = parts[1].split("Forecast:")[0].strip()
                        return f"Today's weather: {current_info}"

                return f"Here's today's weather:\n\n{tool_result}"

            else:
                # General weather query
                return f"Here's the current weather information:\n\n{tool_result}"

        elif tool_name == "Location":
            # Format location response
            if "where am i" in user_query or "current location" in user_query:
                return f"You are currently located at:\n\n{tool_result}"
            else:
                return f"Here's the location information:\n\n{tool_result}"

        # Fallback
        return f"Here's the information you requested:\n\n{tool_result}"

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