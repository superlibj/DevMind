"""
Integration between ACP tools and ReAct agent tools registry.

This module bridges the ACP tool system with the ReAct agent's tools registry
to provide seamless tool access for the AI agent.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional

from ..agent import tools_registry, ToolType, ToolParameter, ToolDefinition, ToolResult
from .acp_integration import acp_client, acp_registry, ACPStatus
from config.settings import settings

logger = logging.getLogger(__name__)


def register_acp_tools_with_agent():
    """Register all ACP tools with the ReAct agent tools registry."""

    # Get all available ACP tools
    acp_tools = acp_registry.list_tools()

    for acp_spec in acp_tools:
        # Convert ACP tool spec to agent tool definition
        agent_tool_def = _convert_acp_to_agent_tool(acp_spec)

        # Create wrapper function for the ACP tool
        tool_function = _create_tool_wrapper(acp_spec.name)

        # Register with agent tools registry
        tools_registry.register_tool(
            name=acp_spec.name,
            function=tool_function,
            description=acp_spec.description,
            tool_type=_map_capabilities_to_tool_type(acp_spec.capabilities),
            parameters=agent_tool_def.parameters,
            requires_confirmation=acp_spec.requires_confirmation,
            security_risk=acp_spec.security_level in ["high", "critical"],
            timeout=acp_spec.timeout_seconds,
            metadata={
                "acp_tool": True,
                "acp_version": acp_spec.version,
                "security_level": acp_spec.security_level,
                "capabilities": acp_spec.capabilities
            }
        )

        logger.info(f"Registered ACP tool '{acp_spec.name}' with agent")


def _convert_acp_to_agent_tool(acp_spec) -> ToolDefinition:
    """Convert ACP tool spec to agent tool definition.

    Args:
        acp_spec: ACP tool specification

    Returns:
        Agent tool definition
    """
    # Extract parameters from ACP spec
    parameters = []

    # Get required and all properties
    required_params = acp_spec.parameters.get("required", [])
    all_properties = acp_spec.parameters.get("properties", {})

    # Also check "optional" for backward compatibility
    if not all_properties and "optional" in acp_spec.parameters:
        all_properties = acp_spec.parameters.get("optional", {})

    # Process all parameters
    for param_name, param_info in all_properties.items():
        is_required = param_name in required_params

        parameters.append(ToolParameter(
            name=param_name,
            type=_map_json_type_to_python(param_info.get("type", "string")),
            description=param_info.get("description", f"{'Required' if is_required else 'Optional'} parameter {param_name}"),
            required=is_required,
            default=param_info.get("default")
        ))

    # Create tool definition (we don't need the actual function here)
    return ToolDefinition(
        name=acp_spec.name,
        description=acp_spec.description,
        tool_type=_map_capabilities_to_tool_type(acp_spec.capabilities),
        function=lambda: None,  # Placeholder, real function is wrapped
        parameters=parameters,
        requires_confirmation=acp_spec.requires_confirmation,
        security_risk=acp_spec.security_level in ["high", "critical"],
        timeout=acp_spec.timeout_seconds,
        metadata=acp_spec.metadata
    )


def _map_json_type_to_python(json_type: str) -> type:
    """Map JSON schema type to Python type.

    Args:
        json_type: JSON schema type string

    Returns:
        Python type
    """
    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict
    }
    return type_mapping.get(json_type, str)


def _map_capabilities_to_tool_type(capabilities: List[str]) -> ToolType:
    """Map ACP capabilities to agent tool type.

    Args:
        capabilities: List of ACP capabilities

    Returns:
        Agent tool type
    """
    capability_mapping = {
        "version_control": ToolType.GIT_OPERATION,
        "file_tracking": ToolType.GIT_OPERATION,
        "history_management": ToolType.GIT_OPERATION,
        "branch_management": ToolType.GIT_OPERATION,
        "file_management": ToolType.FILE_OPERATION,
        "directory_operations": ToolType.FILE_OPERATION,
        "content_manipulation": ToolType.FILE_OPERATION,
        "file_search": ToolType.FILE_OPERATION,
        "text_editing": ToolType.FILE_OPERATION,
        "pattern_matching": ToolType.TEXT_PROCESSING,
        "text_navigation": ToolType.TEXT_PROCESSING,
        "location_services": ToolType.WEB_ACCESS,
        "weather_services": ToolType.WEB_ACCESS,
        "geolocation": ToolType.WEB_ACCESS,
        "data_retrieval": ToolType.WEB_ACCESS,
        "web_access": ToolType.WEB_ACCESS
    }

    # Find the most relevant tool type
    for capability in capabilities:
        if capability in capability_mapping:
            return capability_mapping[capability]

    # Default to file operation if no specific mapping found
    return ToolType.FILE_OPERATION


def _create_tool_wrapper(tool_name: str):
    """Create a wrapper function for an ACP tool.

    Args:
        tool_name: Name of the ACP tool

    Returns:
        Async wrapper function
    """
    async def tool_wrapper(**kwargs) -> Any:
        """Wrapper function that calls the ACP tool.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            Exception: If tool execution fails
        """
        try:
            logger.debug(f"Executing ACP tool '{tool_name}' with args: {kwargs}")

            # Call ACP tool
            result = await acp_client.call_tool(tool_name, **kwargs)

            if result.status == ACPStatus.COMPLETED:
                logger.debug(f"ACP tool '{tool_name}' completed successfully")
                return result.result
            else:
                error_msg = result.error or f"Tool '{tool_name}' failed"
                logger.error(f"ACP tool '{tool_name}' failed: {error_msg}")
                raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error executing ACP tool '{tool_name}': {e}")
            raise

    # Set function name for debugging
    tool_wrapper.__name__ = f"acp_{tool_name}_wrapper"
    tool_wrapper.__doc__ = f"ACP tool wrapper for {tool_name}"

    return tool_wrapper


class ACPToolManager:
    """Manager for ACP tool integration with the agent."""

    def __init__(self):
        """Initialize ACP tool manager."""
        self.registered_tools = set()

    def register_all_tools(self):
        """Register all ACP tools with the agent."""
        if not self.registered_tools:
            register_acp_tools_with_agent()
            self.registered_tools = set(spec.name for spec in acp_registry.list_tools())
            logger.info(f"Registered {len(self.registered_tools)} ACP tools with agent")

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about an ACP tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool information or None if not found
        """
        spec = acp_registry.tool_specs.get(tool_name)
        if spec:
            return {
                "name": spec.name,
                "description": spec.description,
                "version": spec.version,
                "capabilities": spec.capabilities,
                "security_level": spec.security_level,
                "timeout": spec.timeout_seconds,
                "requires_confirmation": spec.requires_confirmation,
                "parameters": spec.parameters
            }
        return None

    def list_available_tools(self) -> List[Dict[str, Any]]:
        """List all available ACP tools.

        Returns:
            List of tool information
        """
        return [
            self.get_tool_info(tool_name)
            for tool_name in self.registered_tools
        ]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Execute an ACP tool and return agent-compatible result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            context: Execution context

        Returns:
            Agent tool result
        """
        try:
            # Execute ACP tool
            acp_result = await acp_client.call_tool(tool_name, **arguments)

            # Convert to agent tool result
            return ToolResult(
                success=(acp_result.status == ACPStatus.COMPLETED),
                result=acp_result.result,
                error=acp_result.error,
                execution_time=acp_result.execution_time,
                stdout=acp_result.stdout,
                stderr=acp_result.stderr,
                metadata={
                    "acp_status": acp_result.status.value,
                    "exit_code": acp_result.exit_code,
                    **acp_result.metadata
                }
            )

        except Exception as e:
            logger.error(f"Failed to execute ACP tool '{tool_name}': {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"exception": type(e).__name__}
            )


# Global ACP tool manager instance
acp_tool_manager = ACPToolManager()


def initialize_acp_integration():
    """Initialize ACP integration with the agent.

    This should be called during application startup to register all tools.
    """
    try:
        # Register all ACP tools with the agent
        acp_tool_manager.register_all_tools()

        logger.info("ACP integration initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize ACP integration: {e}")
        raise


# Convenience functions for external use
def get_acp_tool_info(tool_name: str) -> Optional[Dict[str, Any]]:
    """Get information about an ACP tool."""
    return acp_tool_manager.get_tool_info(tool_name)


def list_acp_tools() -> List[Dict[str, Any]]:
    """List all available ACP tools."""
    return acp_tool_manager.list_available_tools()


async def execute_acp_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> ToolResult:
    """Execute an ACP tool."""
    return await acp_tool_manager.execute_tool(tool_name, arguments, context)