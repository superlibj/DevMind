"""
Base Agent class for all specialized agents in DevMind.

Provides common functionality for agent execution, tool access, and context management.
"""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .agent_manager import AgentContext, AgentCapability

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all specialized agents."""

    def __init__(self, context: 'AgentContext'):
        """Initialize base agent.

        Args:
            context: Agent execution context
        """
        self.context = context
        self.logger = logging.getLogger(f"{self.__class__.__name__}({context.agent_id})")
        self.start_time = time.time()
        self.turn_count = 0
        self.execution_log: List[Dict[str, Any]] = []

        # Tool access based on capabilities
        self.available_tools = self._determine_available_tools()

    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """Execute the agent's main task.

        Returns:
            Execution result with agent output and metadata
        """
        pass

    def _determine_available_tools(self) -> Set[str]:
        """Determine which tools this agent can use based on capabilities."""
        from .agent_manager import AgentCapability

        available_tools = set()

        for capability in self.context.capabilities:
            if capability == AgentCapability.ALL_TOOLS:
                available_tools.update([
                    "Read", "Write", "Edit", "Bash", "Glob", "Grep",
                    "WebSearch", "WebFetch", "TaskCreate", "TaskUpdate",
                    "TaskGet", "TaskList", "AskUserQuestion", "SmartCommit",
                    "PRCreate", "TaskOutput", "TaskStop", "AutoMemory"
                ])
            elif capability == AgentCapability.READ_ONLY:
                available_tools.update([
                    "Read", "Glob", "Grep", "TaskGet", "TaskList"
                ])
            elif capability == AgentCapability.SEARCH_OPERATIONS:
                available_tools.update([
                    "Glob", "Grep", "WebSearch", "WebFetch"
                ])
            elif capability == AgentCapability.FILE_OPERATIONS:
                available_tools.update([
                    "Read", "Write", "Edit"
                ])
            elif capability == AgentCapability.NO_DESTRUCTIVE:
                available_tools.update([
                    "Read", "Glob", "Grep", "WebSearch", "WebFetch",
                    "TaskCreate", "TaskUpdate", "TaskGet", "TaskList",
                    "AskUserQuestion", "AutoMemory"
                ])

        return available_tools

    async def use_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Use a tool if allowed by agent capabilities.

        Args:
            tool_name: Name of the tool to use
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        if tool_name not in self.available_tools:
            raise PermissionError(f"Agent {self.context.agent_type.value} cannot use tool: {tool_name}")

        self.turn_count += 1

        # Check turn limit
        if self.context.max_turns and self.turn_count > self.context.max_turns:
            raise RuntimeError(f"Agent exceeded maximum turns: {self.context.max_turns}")

        try:
            # Get tool from registry and execute
            from ..acp_integration import acp_registry, create_acp_message

            tool = acp_registry.get_tool(tool_name)
            if not tool:
                raise ValueError(f"Tool not found: {tool_name}")

            # Create ACP message
            message = create_acp_message(tool_name, kwargs)

            # Execute tool
            result = await tool.execute(message)

            # Log execution
            log_entry = {
                "turn": self.turn_count,
                "tool": tool_name,
                "parameters": kwargs,
                "success": result.is_success(),
                "timestamp": time.time()
            }

            if result.is_success():
                log_entry["result"] = result.result
            else:
                log_entry["error"] = result.error

            self.execution_log.append(log_entry)

            self.logger.debug(f"Used tool {tool_name}: {'success' if result.is_success() else 'failed'}")

            return {
                "success": result.is_success(),
                "result": result.result if result.is_success() else None,
                "error": result.error if not result.is_success() else None,
                "metadata": result.metadata
            }

        except Exception as e:
            self.logger.error(f"Error using tool {tool_name}: {e}")
            return {
                "success": False,
                "result": None,
                "error": str(e),
                "metadata": {}
            }

    async def read_file(self, file_path: str, **kwargs) -> str:
        """Convenience method for reading files."""
        result = await self.use_tool("Read", file_path=file_path, **kwargs)
        if result["success"]:
            return result["result"]
        else:
            raise RuntimeError(f"Failed to read file {file_path}: {result['error']}")

    async def search_files(self, pattern: str, path: Optional[str] = None) -> List[str]:
        """Convenience method for searching files."""
        params = {"pattern": pattern}
        if path:
            params["path"] = path
        result = await self.use_tool("Glob", **params)
        if result["success"]:
            # Handle both string and dict results
            if isinstance(result["result"], dict):
                return result["result"].get("files", [])
            elif isinstance(result["result"], str):
                # Parse file list from string result
                files = []
                for line in result["result"].split('\n'):
                    line = line.strip()
                    if line and not line.startswith('Found') and not line.startswith('Total'):
                        files.append(line)
                return files
            else:
                return []
        else:
            raise RuntimeError(f"Failed to search files: {result['error']}")

    async def search_content(self, pattern: str, **kwargs) -> List[str]:
        """Convenience method for searching content."""
        result = await self.use_tool("Grep", pattern=pattern, output_mode="files_with_matches", **kwargs)
        if result["success"]:
            # Handle both string and dict results
            if isinstance(result["result"], dict):
                return result["result"].get("files", [])
            elif isinstance(result["result"], str):
                # Parse file list from string result
                files = []
                for line in result["result"].split('\n'):
                    line = line.strip()
                    if line and not line.startswith('Found') and not line.startswith('Total') and line.endswith(('.py', '.js', '.ts', '.go', '.rs', '.java', '.cpp', '.c', '.h')):
                        files.append(line)
                return files
            else:
                return []
        else:
            raise RuntimeError(f"Failed to search content: {result['error']}")

    async def get_content_matches(self, pattern: str, **kwargs) -> str:
        """Convenience method for getting content matches."""
        result = await self.use_tool("Grep", pattern=pattern, output_mode="content", **kwargs)
        if result["success"]:
            if isinstance(result["result"], str):
                return result["result"]
            else:
                return str(result["result"])
        else:
            raise RuntimeError(f"Failed to get content matches: {result['error']}")

    async def write_file(self, file_path: str, content: str) -> bool:
        """Convenience method for writing files."""
        result = await self.use_tool("Write", file_path=file_path, content=content)
        return result["success"]

    async def edit_file(self, file_path: str, old_string: str, new_string: str, **kwargs) -> bool:
        """Convenience method for editing files."""
        result = await self.use_tool("Edit", file_path=file_path, old_string=old_string, new_string=new_string, **kwargs)
        return result["success"]

    async def run_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """Convenience method for running bash commands."""
        return await self.use_tool("Bash", command=command, **kwargs)

    async def web_search(self, query: str, **kwargs) -> str:
        """Convenience method for web search."""
        result = await self.use_tool("WebSearch", query=query, **kwargs)
        if result["success"]:
            return result["result"]
        else:
            raise RuntimeError(f"Failed to web search: {result['error']}")

    async def save_memory(self, content: str, topic: str = "general", **kwargs) -> bool:
        """Convenience method for saving memories."""
        result = await self.use_tool("AutoMemory", action="save", content=content, topic=topic, **kwargs)
        return result["success"]

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of agent execution."""
        execution_time = time.time() - self.start_time

        tool_usage = {}
        for log_entry in self.execution_log:
            tool = log_entry.get("tool", "unknown")
            if tool not in tool_usage:
                tool_usage[tool] = {"count": 0, "successes": 0, "failures": 0}

            tool_usage[tool]["count"] += 1
            if log_entry.get("success", True):  # Progress entries default to success
                tool_usage[tool]["successes"] += 1
            else:
                tool_usage[tool]["failures"] += 1

        return {
            "agent_id": self.context.agent_id,
            "agent_type": self.context.agent_type.value,
            "execution_time_seconds": round(execution_time, 2),
            "turns_used": self.turn_count,
            "max_turns": self.context.max_turns,
            "tool_usage": tool_usage,
            "available_tools": list(self.available_tools),
            "capabilities": [cap.value for cap in self.context.capabilities]
        }

    async def check_timeout(self):
        """Check if agent has exceeded timeout."""
        if time.time() - self.start_time > self.context.timeout_seconds:
            raise asyncio.TimeoutError(f"Agent exceeded timeout: {self.context.timeout_seconds}s")

    def log_progress(self, message: str, level: str = "info"):
        """Log progress message."""
        log_method = getattr(self.logger, level, self.logger.info)
        log_method(message)

        # Add to execution log
        self.execution_log.append({
            "turn": self.turn_count,
            "type": "progress",
            "tool": "progress",  # Add tool field for consistency
            "message": message,
            "level": level,
            "timestamp": time.time()
        })