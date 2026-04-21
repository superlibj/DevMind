"""
Agent Client Protocol (ACP) integration for standardized tool access.

This module implements the Agent Client Protocol for consistent and secure
tool communication between the AI agent and development tools.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Callable
import uuid

logger = logging.getLogger(__name__)


class ACPMessageType(Enum):
    """ACP message types."""
    TOOL_REQUEST = "tool_request"
    TOOL_RESPONSE = "tool_response"
    TOOL_ERROR = "tool_error"
    TOOL_PROGRESS = "tool_progress"
    TOOL_CANCEL = "tool_cancel"


class ACPStatus(Enum):
    """ACP execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ACPMessage:
    """ACP protocol message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: ACPMessageType = ACPMessageType.TOOL_REQUEST
    tool_name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "tool_name": self.tool_name,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ACPMessage':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=ACPMessageType(data.get("type", "tool_request")),
            tool_name=data.get("tool_name", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time()),
            correlation_id=data.get("correlation_id"),
            metadata=data.get("metadata", {})
        )


@dataclass
class ACPToolResult:
    """Result of ACP tool execution."""
    status: ACPStatus
    result: Any = None
    error: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    execution_time: float = 0
    exit_code: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "execution_time": self.execution_time,
            "exit_code": self.exit_code,
            "metadata": self.metadata
        }

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ACPStatus.COMPLETED and self.error is None


@dataclass
class ACPToolSpec:
    """Specification for an ACP-compliant tool."""
    name: str
    description: str
    version: str = "1.0.0"
    parameters: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    security_level: str = "standard"  # "low", "standard", "high", "critical"
    timeout_seconds: int = 30
    requires_confirmation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": self.parameters,
            "capabilities": self.capabilities,
            "security_level": self.security_level,
            "timeout_seconds": self.timeout_seconds,
            "requires_confirmation": self.requires_confirmation,
            "metadata": self.metadata
        }


class ACPTool:
    """Base class for ACP-compliant tools."""

    def __init__(self, spec: ACPToolSpec):
        """Initialize ACP tool.

        Args:
            spec: Tool specification
        """
        self.spec = spec
        self.logger = logging.getLogger(f"acp.{spec.name}")

    async def execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute tool with ACP message.

        Args:
            message: ACP request message
            context: Additional execution context

        Returns:
            Tool execution result
        """
        start_time = time.time()

        try:
            self.logger.info(f"Executing {self.spec.name} with message {message.id}")

            # Validate message
            validation_error = await self._validate_message(message)
            if validation_error:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Message validation failed: {validation_error}",
                    execution_time=time.time() - start_time
                )

            # Pre-execution hook
            await self._pre_execute(message, context)

            # Execute tool-specific logic
            result = await self._execute_impl(message, context)

            # Post-execution hook
            await self._post_execute(message, result, context)

            execution_time = time.time() - start_time
            result.execution_time = execution_time

            self.logger.info(
                f"Tool {self.spec.name} completed in {execution_time:.2f}s"
            )

            return result

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            self.logger.error(f"Tool {self.spec.name} timed out after {execution_time:.2f}s")

            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Tool execution timed out after {self.spec.timeout_seconds}s",
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            import traceback
            tb_str = traceback.format_exc()
            self.logger.error(f"Tool {self.spec.name} failed: {e}")
            self.logger.error(f"Full traceback: {tb_str}")

            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"{str(e)} | Exception: {type(e).__name__} | Traceback: {tb_str[:200]}",
                execution_time=execution_time,
                metadata={"exception_type": type(e).__name__, "full_traceback": tb_str}
            )

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate incoming ACP message.

        Args:
            message: ACP message to validate

        Returns:
            Error message if validation fails, None if valid
        """
        if not message.tool_name:
            return "Tool name is required"

        if message.tool_name != self.spec.name:
            return f"Tool name mismatch: expected {self.spec.name}, got {message.tool_name}"

        # Validate required parameters
        required_params = self.spec.parameters.get("required", [])
        for param in required_params:
            if param not in message.payload:
                return f"Required parameter '{param}' missing"

        return None

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]]
    ):
        """Pre-execution hook for setup."""
        pass

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]]
    ) -> ACPToolResult:
        """Tool-specific execution logic (to be implemented by subclasses).

        Args:
            message: ACP message
            context: Execution context

        Returns:
            Execution result
        """
        raise NotImplementedError("Subclasses must implement _execute_impl")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]]
    ):
        """Post-execution hook for cleanup."""
        pass

    def get_spec(self) -> ACPToolSpec:
        """Get tool specification."""
        return self.spec


class ACPRegistry:
    """Registry for ACP-compliant tools."""

    def __init__(self):
        """Initialize ACP registry."""
        self.tools: Dict[str, ACPTool] = {}
        self.tool_specs: Dict[str, ACPToolSpec] = {}
        self.logger = logging.getLogger("acp.registry")

    def register_tool(self, tool: ACPTool):
        """Register an ACP tool.

        Args:
            tool: ACP tool to register
        """
        spec = tool.get_spec()

        if spec.name in self.tools:
            self.logger.warning(f"Overriding existing tool: {spec.name}")

        self.tools[spec.name] = tool
        self.tool_specs[spec.name] = spec

        self.logger.info(f"Registered ACP tool: {spec.name} v{spec.version}")

    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister an ACP tool.

        Args:
            tool_name: Name of tool to unregister

        Returns:
            True if tool was unregistered
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            del self.tool_specs[tool_name]
            self.logger.info(f"Unregistered ACP tool: {tool_name}")
            return True

        return False

    def get_tool(self, tool_name: str) -> Optional[ACPTool]:
        """Get registered tool by name.

        Args:
            tool_name: Name of tool

        Returns:
            ACP tool or None if not found
        """
        return self.tools.get(tool_name)

    def list_tools(self) -> List[ACPToolSpec]:
        """List all registered tool specifications.

        Returns:
            List of tool specifications
        """
        return list(self.tool_specs.values())

    def get_tools_by_capability(self, capability: str) -> List[ACPTool]:
        """Get tools that have a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of tools with the capability
        """
        matching_tools = []

        for tool_name, spec in self.tool_specs.items():
            if capability in spec.capabilities:
                tool = self.tools.get(tool_name)
                if tool:
                    matching_tools.append(tool)

        return matching_tools

    async def execute_tool(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            payload: Tool payload
            context: Execution context

        Returns:
            Tool execution result
        """
        tool = self.get_tool(tool_name)

        if not tool:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Tool '{tool_name}' not found"
            )

        # Create ACP message
        message = ACPMessage(
            type=ACPMessageType.TOOL_REQUEST,
            tool_name=tool_name,
            payload=payload
        )

        # Execute with timeout
        spec = tool.get_spec()
        try:
            result = await asyncio.wait_for(
                tool.execute(message, context),
                timeout=spec.timeout_seconds
            )
            return result

        except asyncio.TimeoutError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Tool execution timed out after {spec.timeout_seconds}s"
            )

    def get_tool_manifest(self) -> Dict[str, Any]:
        """Get manifest of all registered tools.

        Returns:
            Tool manifest
        """
        return {
            "version": "1.0.0",
            "protocol": "ACP",
            "tools": {
                name: spec.to_dict()
                for name, spec in self.tool_specs.items()
            },
            "capabilities": list(set(
                cap for spec in self.tool_specs.values()
                for cap in spec.capabilities
            )),
            "count": len(self.tools)
        }


class ACPClient:
    """Client for communicating with ACP tools."""

    def __init__(self, registry: ACPRegistry):
        """Initialize ACP client.

        Args:
            registry: ACP tool registry
        """
        self.registry = registry
        self.logger = logging.getLogger("acp.client")
        self._active_requests: Dict[str, asyncio.Task] = {}

    async def call_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> ACPToolResult:
        """Call a tool with keyword arguments.

        Args:
            tool_name: Name of tool to call
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        return await self.registry.execute_tool(tool_name, kwargs)

    async def call_tool_async(
        self,
        tool_name: str,
        **kwargs
    ) -> str:
        """Call a tool asynchronously and return request ID.

        Args:
            tool_name: Name of tool to call
            **kwargs: Tool parameters

        Returns:
            Request ID for tracking
        """
        request_id = str(uuid.uuid4())

        # Start async execution
        task = asyncio.create_task(
            self.registry.execute_tool(tool_name, kwargs)
        )

        self._active_requests[request_id] = task

        # Clean up completed tasks
        def cleanup_task(task):
            if request_id in self._active_requests:
                del self._active_requests[request_id]

        task.add_done_callback(cleanup_task)

        return request_id

    async def get_result(self, request_id: str) -> Optional[ACPToolResult]:
        """Get result of async tool call.

        Args:
            request_id: Request ID from call_tool_async

        Returns:
            Tool result if available, None if still running
        """
        task = self._active_requests.get(request_id)

        if not task:
            return None

        if task.done():
            try:
                return task.result()
            except Exception as e:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=str(e)
                )

        return None

    async def cancel_request(self, request_id: str) -> bool:
        """Cancel an async tool request.

        Args:
            request_id: Request ID to cancel

        Returns:
            True if request was cancelled
        """
        task = self._active_requests.get(request_id)

        if task and not task.done():
            task.cancel()
            return True

        return False

    def list_active_requests(self) -> List[str]:
        """List active request IDs.

        Returns:
            List of active request IDs
        """
        return [
            req_id for req_id, task in self._active_requests.items()
            if not task.done()
        ]

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names.

        Returns:
            List of tool names
        """
        return list(self.registry.tools.keys())

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool.

        Args:
            tool_name: Name of tool

        Returns:
            Tool information or None if not found
        """
        spec = self.registry.tool_specs.get(tool_name)
        return spec.to_dict() if spec else None


# Global ACP registry and client instances
acp_registry = ACPRegistry()
acp_client = ACPClient(acp_registry)


def register_acp_tool(tool: ACPTool):
    """Convenience function to register an ACP tool.

    Args:
        tool: ACP tool to register
    """
    acp_registry.register_tool(tool)


def create_acp_message(
    tool_name: str,
    payload: Dict[str, Any],
    message_type: ACPMessageType = ACPMessageType.TOOL_REQUEST
) -> ACPMessage:
    """Convenience function to create ACP message.

    Args:
        tool_name: Name of target tool
        payload: Message payload
        message_type: Type of message

    Returns:
        ACP message
    """
    return ACPMessage(
        type=message_type,
        tool_name=tool_name,
        payload=payload
    )