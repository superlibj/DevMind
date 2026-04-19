"""
Agent Manager for spawning and managing specialized sub-agents.

Handles different agent types, execution contexts, and agent lifecycle management.
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Supported agent types and their capabilities."""
    GENERAL_PURPOSE = "general-purpose"
    EXPLORE = "Explore"
    PLAN = "Plan"
    STATUSLINE_SETUP = "statusline-setup"
    CLAUDE_CODE_GUIDE = "claude-code-guide"


class AgentCapability(Enum):
    """Agent capabilities and tool access."""
    ALL_TOOLS = "all_tools"
    READ_ONLY = "read_only"
    NO_DESTRUCTIVE = "no_destructive"
    FILE_OPERATIONS = "file_operations"
    SEARCH_OPERATIONS = "search_operations"


@dataclass
class AgentContext:
    """Context for agent execution."""
    agent_id: str
    agent_type: AgentType
    description: str
    prompt: str
    capabilities: Set[AgentCapability] = field(default_factory=set)
    model: Optional[str] = None
    max_turns: Optional[int] = None
    timeout_seconds: int = 300
    run_in_background: bool = False
    isolation: Optional[str] = None
    resume_from: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentManager:
    """Manager for spawning and coordinating specialized agents."""

    def __init__(self, agents_dir: Optional[Path] = None):
        """Initialize agent manager.

        Args:
            agents_dir: Directory for agent data and sessions
        """
        self.agents_dir = agents_dir or Path("sessions/agents")
        self.agents_dir.mkdir(parents=True, exist_ok=True)

        # Active agents
        self.active_agents: Dict[str, AgentContext] = {}
        self.completed_agents: Dict[str, AgentContext] = {}

        # Agent capabilities mapping
        self.agent_capabilities = {
            AgentType.GENERAL_PURPOSE: {
                AgentCapability.ALL_TOOLS
            },
            AgentType.EXPLORE: {
                AgentCapability.READ_ONLY,
                AgentCapability.SEARCH_OPERATIONS
            },
            AgentType.PLAN: {
                AgentCapability.READ_ONLY,
                AgentCapability.SEARCH_OPERATIONS,
                AgentCapability.NO_DESTRUCTIVE  # Allow AutoMemory but not destructive operations
            },
            AgentType.STATUSLINE_SETUP: {
                AgentCapability.READ_ONLY,
                AgentCapability.FILE_OPERATIONS
            },
            AgentType.CLAUDE_CODE_GUIDE: {
                AgentCapability.READ_ONLY,
                AgentCapability.SEARCH_OPERATIONS
            }
        }

        # Background task support
        self.background_agents: Dict[str, asyncio.Task] = {}

    async def spawn_agent(
        self,
        agent_type: AgentType,
        description: str,
        prompt: str,
        model: Optional[str] = None,
        max_turns: Optional[int] = None,
        run_in_background: bool = False,
        isolation: Optional[str] = None,
        resume_from: Optional[str] = None,
        **kwargs
    ) -> AgentContext:
        """Spawn a new specialized agent.

        Args:
            agent_type: Type of agent to spawn
            description: Short description of the task
            prompt: Detailed task prompt for the agent
            model: Optional model preference (haiku, sonnet, opus)
            max_turns: Maximum number of turns before stopping
            run_in_background: Whether to run in background
            isolation: Isolation mode (e.g., "worktree")
            resume_from: Agent ID to resume from
            **kwargs: Additional metadata

        Returns:
            Agent context for the spawned agent
        """
        agent_id = resume_from or f"agent_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        # Create agent context
        context = AgentContext(
            agent_id=agent_id,
            agent_type=agent_type,
            description=description,
            prompt=prompt,
            capabilities=self.agent_capabilities.get(agent_type, set()),
            model=model,
            max_turns=max_turns,
            run_in_background=run_in_background,
            isolation=isolation,
            resume_from=resume_from,
            metadata=kwargs
        )

        # Validate agent type
        if agent_type not in AgentType:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Register agent
        self.active_agents[agent_id] = context

        # Save agent context
        await self._save_agent_context(context)

        if run_in_background:
            # Start background execution
            task = asyncio.create_task(self._execute_agent_background(context))
            self.background_agents[agent_id] = task
            context.status = "running_background"
        else:
            # Execute synchronously
            context.status = "running"
            await self._execute_agent(context)

        logger.info(f"Spawned {agent_type.value} agent: {agent_id}")
        return context

    async def get_agent_status(self, agent_id: str) -> Optional[AgentContext]:
        """Get status of an agent.

        Args:
            agent_id: Agent ID to check

        Returns:
            Agent context if found
        """
        # Check active agents
        if agent_id in self.active_agents:
            return self.active_agents[agent_id]

        # Check completed agents
        if agent_id in self.completed_agents:
            return self.completed_agents[agent_id]

        # Try to load from disk
        return await self._load_agent_context(agent_id)

    async def get_agent_result(self, agent_id: str, wait: bool = True) -> Optional[Dict[str, Any]]:
        """Get result from an agent.

        Args:
            agent_id: Agent ID
            wait: Whether to wait for completion if running

        Returns:
            Agent result if available
        """
        context = await self.get_agent_status(agent_id)
        if not context:
            return None

        if context.status == "running_background" and wait:
            # Wait for background agent to complete
            if agent_id in self.background_agents:
                try:
                    await self.background_agents[agent_id]
                except Exception as e:
                    logger.error(f"Background agent {agent_id} failed: {e}")
                    context.error = str(e)
                    context.status = "failed"

        return context.result

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a running agent.

        Args:
            agent_id: Agent ID to stop

        Returns:
            True if agent was stopped
        """
        # Stop background task
        if agent_id in self.background_agents:
            task = self.background_agents[agent_id]
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            del self.background_agents[agent_id]

        # Update context
        if agent_id in self.active_agents:
            context = self.active_agents[agent_id]
            context.status = "cancelled"

            # Move to completed
            self.completed_agents[agent_id] = context
            del self.active_agents[agent_id]

            await self._save_agent_context(context)
            logger.info(f"Stopped agent: {agent_id}")
            return True

        return False

    async def list_agents(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        """List all agents with summary information.

        Args:
            include_completed: Whether to include completed agents

        Returns:
            List of agent summaries
        """
        summaries = []

        # Active agents
        for agent_id, context in self.active_agents.items():
            summary = {
                "agent_id": agent_id,
                "type": context.agent_type.value,
                "description": context.description,
                "status": context.status,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(context.created_at)),
                "background": context.run_in_background,
                "model": context.model
            }
            summaries.append(summary)

        # Completed agents
        if include_completed:
            for agent_id, context in self.completed_agents.items():
                summary = {
                    "agent_id": agent_id,
                    "type": context.agent_type.value,
                    "description": context.description,
                    "status": context.status,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(context.created_at)),
                    "background": context.run_in_background,
                    "model": context.model,
                    "has_result": context.result is not None
                }
                summaries.append(summary)

        # Sort by creation time (most recent first)
        summaries.sort(key=lambda x: x["created_at"], reverse=True)
        return summaries

    async def cleanup_completed_agents(self, max_age_hours: int = 24):
        """Clean up old completed agents.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        agents_to_remove = []

        for agent_id, context in self.completed_agents.items():
            if context.created_at < cutoff_time:
                agents_to_remove.append(agent_id)

        for agent_id in agents_to_remove:
            del self.completed_agents[agent_id]

            # Remove context file
            context_file = self.agents_dir / f"{agent_id}.json"
            if context_file.exists():
                try:
                    context_file.unlink()
                except Exception as e:
                    logger.warning(f"Error removing agent context file {context_file}: {e}")

        if agents_to_remove:
            logger.info(f"Cleaned up {len(agents_to_remove)} old agent contexts")

    async def _execute_agent(self, context: AgentContext):
        """Execute an agent synchronously."""
        try:
            # Import agent class
            from .agent_registry import get_agent_class
            agent_class = get_agent_class(context.agent_type)

            if not agent_class:
                raise ValueError(f"No agent class found for type: {context.agent_type}")

            # Create and run agent
            agent = agent_class(context)
            result = await agent.execute()

            context.result = result
            context.status = "completed"

        except Exception as e:
            logger.exception(f"Agent {context.agent_id} execution failed")
            context.error = str(e)
            context.status = "failed"

        finally:
            # Move to completed
            if context.agent_id in self.active_agents:
                self.completed_agents[context.agent_id] = context
                del self.active_agents[context.agent_id]

            await self._save_agent_context(context)

    async def _execute_agent_background(self, context: AgentContext):
        """Execute an agent in background."""
        try:
            await self._execute_agent(context)
        finally:
            # Clean up background task reference
            if context.agent_id in self.background_agents:
                del self.background_agents[context.agent_id]

    async def _save_agent_context(self, context: AgentContext):
        """Save agent context to disk."""
        try:
            context_file = self.agents_dir / f"{context.agent_id}.json"
            data = {
                "agent_id": context.agent_id,
                "agent_type": context.agent_type.value,
                "description": context.description,
                "prompt": context.prompt,
                "capabilities": [cap.value for cap in context.capabilities],
                "model": context.model,
                "max_turns": context.max_turns,
                "timeout_seconds": context.timeout_seconds,
                "run_in_background": context.run_in_background,
                "isolation": context.isolation,
                "resume_from": context.resume_from,
                "metadata": context.metadata,
                "created_at": context.created_at,
                "status": context.status,
                "result": context.result,
                "error": context.error
            }

            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving agent context {context.agent_id}: {e}")

    async def _load_agent_context(self, agent_id: str) -> Optional[AgentContext]:
        """Load agent context from disk."""
        try:
            context_file = self.agents_dir / f"{agent_id}.json"
            if not context_file.exists():
                return None

            with open(context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Reconstruct context
            context = AgentContext(
                agent_id=data["agent_id"],
                agent_type=AgentType(data["agent_type"]),
                description=data["description"],
                prompt=data["prompt"],
                capabilities={AgentCapability(cap) for cap in data.get("capabilities", [])},
                model=data.get("model"),
                max_turns=data.get("max_turns"),
                timeout_seconds=data.get("timeout_seconds", 300),
                run_in_background=data.get("run_in_background", False),
                isolation=data.get("isolation"),
                resume_from=data.get("resume_from"),
                metadata=data.get("metadata", {}),
                created_at=data.get("created_at", time.time()),
                status=data.get("status", "unknown"),
                result=data.get("result"),
                error=data.get("error")
            )

            return context

        except Exception as e:
            logger.error(f"Error loading agent context {agent_id}: {e}")
            return None


# Global agent manager instance
_agent_manager = None


def get_agent_manager() -> AgentManager:
    """Get the global agent manager instance."""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager


# Export singleton
agent_manager = get_agent_manager()