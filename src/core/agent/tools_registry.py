"""
Tool registration and execution management for the ReAct agent.
"""
import asyncio
import inspect
import logging
import traceback
from typing import Dict, Any, Callable, List, Optional, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import time

from config.settings import settings

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Types of tools available to the agent."""
    FILE_OPERATION = "file_operation"
    GIT_OPERATION = "git_operation"
    CODE_EXECUTION = "code_execution"
    TEXT_PROCESSING = "text_processing"
    WEB_ACCESS = "web_access"
    SYSTEM_COMMAND = "system_command"
    AI_OPERATION = "ai_operation"


@dataclass
class ToolParameter:
    """Represents a tool parameter."""
    name: str
    type: Type
    description: str
    required: bool = True
    default: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "type": self.type.__name__ if hasattr(self.type, "__name__") else str(self.type),
            "description": self.description,
            "required": self.required,
            "default": self.default
        }


@dataclass
class ToolDefinition:
    """Defines a tool available to the agent."""
    name: str
    description: str
    tool_type: ToolType
    function: Callable
    parameters: List[ToolParameter] = field(default_factory=list)
    requires_confirmation: bool = False
    security_risk: bool = False
    timeout: int = 30
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for LLM consumption."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        param.name: {
                            "type": self._get_json_type(param.type),
                            "description": param.description
                        }
                        for param in self.parameters
                    },
                    "required": [p.name for p in self.parameters if p.required]
                }
            }
        }

    def _get_json_type(self, python_type: Type) -> str:
        """Convert Python type to JSON schema type."""
        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object"
        }
        return type_mapping.get(python_type, "string")


@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    stdout: Optional[str] = None
    stderr: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
            "stdout": self.stdout,
            "stderr": self.stderr
        }


class ToolsRegistry:
    """Registry for managing agent tools."""

    def __init__(self):
        """Initialize the tools registry."""
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_usage_stats: Dict[str, Dict[str, Any]] = {}
        self._security_confirmations: Dict[str, bool] = {}

    def register_tool(
        self,
        name: str,
        function: Callable,
        description: str,
        tool_type: ToolType,
        parameters: List[ToolParameter] = None,
        requires_confirmation: bool = False,
        security_risk: bool = False,
        timeout: int = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Register a tool with the agent.

        Args:
            name: Tool name
            function: Function to execute
            description: Tool description
            tool_type: Type of tool
            parameters: Tool parameters
            requires_confirmation: Whether tool requires user confirmation
            security_risk: Whether tool poses security risks
            timeout: Execution timeout in seconds
            metadata: Additional metadata
        """
        if parameters is None:
            parameters = self._extract_parameters(function)

        tool_def = ToolDefinition(
            name=name,
            description=description,
            tool_type=tool_type,
            function=function,
            parameters=parameters,
            requires_confirmation=requires_confirmation,
            security_risk=security_risk,
            timeout=timeout or settings.tools.tool_timeout_seconds,
            metadata=metadata or {}
        )

        self._tools[name] = tool_def
        self._tool_usage_stats[name] = {
            "calls": 0,
            "successes": 0,
            "errors": 0,
            "total_execution_time": 0,
            "last_used": None
        }

        logger.info(f"Registered tool: {name} ({tool_type.value})")

    def _extract_parameters(self, function: Callable) -> List[ToolParameter]:
        """Extract parameters from function signature.

        Args:
            function: Function to analyze

        Returns:
            List of tool parameters
        """
        parameters = []
        sig = inspect.signature(function)

        for param_name, param in sig.parameters.items():
            # Skip self parameter
            if param_name == "self":
                continue

            # Determine type
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str

            # Determine if required
            required = param.default == inspect.Parameter.empty

            # Extract description from docstring (simplified)
            description = f"Parameter {param_name}"

            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=description,
                required=required,
                default=param.default if not required else None
            ))

        return parameters

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name.

        Args:
            name: Tool name

        Returns:
            Tool definition or None if not found
        """
        return self._tools.get(name)

    def list_tools(
        self,
        tool_type: Optional[ToolType] = None,
        enabled_only: bool = True
    ) -> List[ToolDefinition]:
        """List available tools.

        Args:
            tool_type: Filter by tool type
            enabled_only: Only return enabled tools

        Returns:
            List of tool definitions
        """
        tools = list(self._tools.values())

        if enabled_only:
            tools = [t for t in tools if t.enabled]

        if tool_type:
            tools = [t for t in tools if t.tool_type == tool_type]

        return tools

    def get_tools_for_llm(self, tool_type: Optional[ToolType] = None) -> List[Dict[str, Any]]:
        """Get tools formatted for LLM consumption.

        Args:
            tool_type: Filter by tool type

        Returns:
            List of tool definitions for LLM
        """
        tools = self.list_tools(tool_type=tool_type)
        return [tool.to_dict() for tool in tools]

    async def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        user_confirmation: bool = False
    ) -> ToolResult:
        """Execute a tool with given arguments.

        Args:
            name: Tool name
            arguments: Tool arguments
            user_confirmation: Whether user has confirmed execution

        Returns:
            Tool execution result
        """
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found"
            )

        if not tool.enabled:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' is disabled"
            )

        # Check for required confirmation
        if tool.requires_confirmation and not user_confirmation:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' requires user confirmation",
                metadata={"requires_confirmation": True}
            )

        # Security risk warning
        if tool.security_risk and not user_confirmation:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' poses security risks and requires confirmation",
                metadata={"requires_confirmation": True, "security_risk": True}
            )

        start_time = time.time()

        try:
            # Validate arguments
            validation_error = self._validate_arguments(tool, arguments)
            if validation_error:
                return ToolResult(
                    success=False,
                    error=f"Argument validation failed: {validation_error}"
                )

            # Execute the tool
            logger.info(f"Executing tool: {name} with args: {arguments}")

            if asyncio.iscoroutinefunction(tool.function):
                # Async function
                result = await asyncio.wait_for(
                    tool.function(**arguments),
                    timeout=tool.timeout
                )
            else:
                # Sync function - run in thread pool
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: tool.function(**arguments)),
                    timeout=tool.timeout
                )

            execution_time = time.time() - start_time

            # Update statistics
            self._update_tool_stats(name, True, execution_time)

            logger.info(f"Tool {name} executed successfully in {execution_time:.2f}s")

            return ToolResult(
                success=True,
                result=result,
                execution_time=execution_time
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            self._update_tool_stats(name, False, execution_time)

            error_msg = f"Tool '{name}' execution timed out after {tool.timeout}s"
            logger.error(error_msg)

            return ToolResult(
                success=False,
                error=error_msg,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self._update_tool_stats(name, False, execution_time)

            error_msg = f"Tool '{name}' execution failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")

            return ToolResult(
                success=False,
                error=error_msg,
                execution_time=execution_time,
                metadata={"exception": str(e), "traceback": traceback.format_exc()}
            )

    def _validate_arguments(
        self,
        tool: ToolDefinition,
        arguments: Dict[str, Any]
    ) -> Optional[str]:
        """Validate tool arguments.

        Args:
            tool: Tool definition
            arguments: Arguments to validate

        Returns:
            Error message if validation fails, None otherwise
        """
        # Handle 'input' parameter format - extract nested parameters
        actual_arguments = arguments.copy()
        if 'input' in arguments and isinstance(arguments['input'], dict):
            # Merge input parameters with top-level parameters
            input_params = arguments['input']
            actual_arguments.update(input_params)

        # Check required parameters
        for param in tool.parameters:
            if param.required and param.name not in actual_arguments:
                return f"Required parameter '{param.name}' missing"

        # Check parameter types (basic validation)
        for param_name, value in actual_arguments.items():
            if param_name == 'input':
                continue  # Skip the input wrapper parameter
            param = next((p for p in tool.parameters if p.name == param_name), None)
            if param and not self._check_type(value, param.type):
                return f"Parameter '{param_name}' has invalid type"

        return None

    def _check_type(self, value: Any, expected_type: Type) -> bool:
        """Check if value matches expected type.

        Args:
            value: Value to check
            expected_type: Expected type

        Returns:
            True if type matches
        """
        try:
            if expected_type == Any:
                return True
            if expected_type == str:
                return isinstance(value, str)
            elif expected_type == int:
                return isinstance(value, int)
            elif expected_type == float:
                return isinstance(value, (int, float))
            elif expected_type == bool:
                return isinstance(value, bool)
            elif expected_type == list:
                return isinstance(value, list)
            elif expected_type == dict:
                return isinstance(value, dict)
            else:
                return True  # Skip complex type checking for now
        except:
            return True  # Be permissive for now

    def _update_tool_stats(
        self,
        tool_name: str,
        success: bool,
        execution_time: float
    ) -> None:
        """Update tool usage statistics.

        Args:
            tool_name: Name of the tool
            success: Whether execution was successful
            execution_time: Time taken to execute
        """
        stats = self._tool_usage_stats[tool_name]
        stats["calls"] += 1
        stats["total_execution_time"] += execution_time
        stats["last_used"] = time.time()

        if success:
            stats["successes"] += 1
        else:
            stats["errors"] += 1

    def get_tool_stats(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get usage statistics for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Usage statistics or None if tool not found
        """
        return self._tool_usage_stats.get(tool_name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get all tool usage statistics.

        Returns:
            Dictionary of all tool statistics
        """
        return self._tool_usage_stats.copy()

    def enable_tool(self, tool_name: str) -> bool:
        """Enable a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            True if successful
        """
        tool = self.get_tool(tool_name)
        if tool:
            tool.enabled = True
            logger.info(f"Enabled tool: {tool_name}")
            return True
        return False

    def disable_tool(self, tool_name: str) -> bool:
        """Disable a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            True if successful
        """
        tool = self.get_tool(tool_name)
        if tool:
            tool.enabled = False
            logger.info(f"Disabled tool: {tool_name}")
            return True
        return False

    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            True if successful
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            if tool_name in self._tool_usage_stats:
                del self._tool_usage_stats[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False

    def clear_tools(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._tool_usage_stats.clear()
        self._security_confirmations.clear()
        logger.info("Cleared all tools from registry")


# Global tools registry instance
tools_registry = ToolsRegistry()