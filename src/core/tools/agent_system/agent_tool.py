"""
Agent Tool for spawning and managing specialized sub-agents.

Provides ACP interface for launching different agent types with various capabilities.
"""
import logging
from typing import Dict, Any, Optional

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .agent_manager import get_agent_manager, AgentType

logger = logging.getLogger(__name__)


class AgentTool(ACPTool):
    """Tool for launching specialized agents to handle complex tasks autonomously."""

    def __init__(self):
        """Initialize Agent tool."""
        spec = ACPToolSpec(
            name="Agent",
            description="Launch specialized agents to handle complex, multi-step tasks autonomously",
            version="1.0.0",
            parameters={
                "required": ["subagent_type", "description", "prompt"],
                "properties": {
                    "subagent_type": {
                        "type": "string",
                        "enum": ["general-purpose", "Explore", "Plan", "statusline-setup", "claude-code-guide"],
                        "description": "The type of specialized agent to use for this task"
                    },
                    "description": {
                        "type": "string",
                        "description": "A short (3-5 word) description of the task"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The task for the agent to perform"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["sonnet", "opus", "haiku"],
                        "description": "Optional model to use for this agent (defaults to inherit)"
                    },
                    "max_turns": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Maximum number of agentic turns before stopping"
                    },
                    "run_in_background": {
                        "type": "boolean",
                        "description": "Set to true to run this agent in the background",
                        "default": False
                    },
                    "isolation": {
                        "type": "string",
                        "enum": ["worktree"],
                        "description": "Isolation mode for agent execution"
                    },
                    "resume": {
                        "type": "string",
                        "description": "Optional agent ID to resume from previous execution"
                    }
                }
            },
            security_level="standard",
            timeout_seconds=600  # 10 minutes for agent execution
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the agent launch request."""
        payload = message.payload

        # Check required fields
        required_fields = ["subagent_type", "description", "prompt"]
        for field in required_fields:
            if not payload.get(field):
                return f"{field} is required"

        # Validate agent type
        subagent_type = payload.get("subagent_type")
        valid_types = ["general-purpose", "Explore", "Plan", "statusline-setup", "claude-code-guide"]
        if subagent_type not in valid_types:
            return f"Invalid subagent_type. Must be one of: {valid_types}"

        # Validate max_turns if provided
        max_turns = payload.get("max_turns")
        if max_turns is not None and (max_turns < 1 or max_turns > 100):
            return "max_turns must be between 1 and 100"

        # Validate description length
        description = payload.get("description", "")
        if len(description) > 100:
            return "description should be short (3-5 words, max 100 characters)"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute agent spawning."""
        payload = message.payload

        try:
            agent_manager = get_agent_manager()

            # Extract parameters
            subagent_type_str = payload["subagent_type"]
            description = payload["description"]
            prompt = payload["prompt"]
            model = payload.get("model")
            max_turns = payload.get("max_turns")
            run_in_background = payload.get("run_in_background", False)
            isolation = payload.get("isolation")
            resume_from = payload.get("resume")

            # Map string to enum
            try:
                agent_type = AgentType(subagent_type_str)
            except ValueError:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Unknown agent type: {subagent_type_str}"
                )

            # Spawn agent
            self.logger.info(f"Spawning {agent_type.value} agent: {description}")

            agent_context = await agent_manager.spawn_agent(
                agent_type=agent_type,
                description=description,
                prompt=prompt,
                model=model,
                max_turns=max_turns,
                run_in_background=run_in_background,
                isolation=isolation,
                resume_from=resume_from
            )

            # Prepare result
            if run_in_background:
                result_message = f"""🤖 **{agent_type.value.title()} Agent Launched in Background**

**Agent ID:** {agent_context.agent_id}
**Task:** {description}
**Status:** Running in background

The agent will work autonomously and you'll be notified when it completes.
Use TaskOutput with agent ID to check progress or results."""

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result=result_message,
                    metadata={
                        "agent_id": agent_context.agent_id,
                        "agent_type": agent_type.value,
                        "background": True,
                        "status": agent_context.status
                    }
                )
            else:
                # Wait for completion and return result
                final_result = agent_context.result

                if final_result and final_result.get("success", False):
                    agent_output = final_result.get("result", "Agent completed successfully")
                    execution_summary = final_result.get("execution_summary", {})

                    result_message = f"""🤖 **{agent_type.value.title()} Agent Results**

{agent_output}

---
**Execution Summary:**
- Agent ID: {agent_context.agent_id}
- Tools Used: {execution_summary.get('turns_used', 0)} turns
- Execution Time: {execution_summary.get('execution_time_seconds', 0)}s"""

                    return ACPToolResult(
                        status=ACPStatus.COMPLETED,
                        result=result_message,
                        metadata={
                            "agent_id": agent_context.agent_id,
                            "agent_type": agent_type.value,
                            "background": False,
                            "execution_summary": execution_summary,
                            "agent_result": final_result
                        }
                    )
                else:
                    error_msg = final_result.get("error", "Agent execution failed") if final_result else "No result returned"
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"{agent_type.value.title()} agent failed: {error_msg}",
                        metadata={
                            "agent_id": agent_context.agent_id,
                            "agent_type": agent_type.value,
                            "agent_result": final_result
                        }
                    )

        except Exception as e:
            logger.exception(f"Error spawning agent {subagent_type_str}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to spawn agent: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        payload = message.payload
        agent_type = payload.get("subagent_type", "unknown")
        description = payload.get("description", "")
        self.logger.debug(f"Preparing to spawn {agent_type} agent: {description}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            agent_id = result.metadata.get("agent_id", "unknown")
            agent_type = result.metadata.get("agent_type", "unknown")
            background = result.metadata.get("background", False)

            status = "background execution started" if background else "completed"
            self.logger.info(f"Agent {agent_type} ({agent_id}) {status}")

    def get_agent_type_descriptions(self) -> Dict[str, str]:
        """Get descriptions of available agent types."""
        return {
            "general-purpose": "General-purpose agent for researching complex questions, searching for code, and executing multi-step tasks. Has access to all tools.",
            "Explore": "Fast agent specialized for exploring codebases. Can quickly find files by patterns, search code for keywords, or answer questions about codebase structure. Specify thoroughness level: 'quick', 'medium', or 'very thorough'.",
            "Plan": "Software architect agent for designing implementation plans. Returns step-by-step plans, identifies critical files, and considers architectural trade-offs.",
            "statusline-setup": "Specialized agent for configuring status line settings. Has access to Read and Edit tools for configuration management.",
            "claude-code-guide": "Agent for answering questions about Claude Code features, hooks, slash commands, MCP servers, settings, IDE integrations, and the Claude API. Uses web search and documentation access."
        }


# Create singleton instance
agent_tool = AgentTool()