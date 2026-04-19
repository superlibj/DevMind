"""
Agent System for DevMind - Sub-agent spawning and management.

Provides specialized agents that can autonomously handle complex tasks,
with support for different agent types, resume capabilities, and background execution.
"""

from .agent_manager import (
    AgentManager, AgentType, AgentCapability,
    agent_manager
)
from .agent_tool import agent_tool, AgentTool
from .specialized_agents import (
    GeneralPurposeAgent,
    ExploreAgent,
    PlanAgent,
    StatuslineSetupAgent
)
from .agent_registry import (
    agent_registry,
    register_agent_type,
    get_agent_class
)

__all__ = [
    # Agent Management
    "AgentManager",
    "AgentType",
    "AgentCapability",
    "agent_manager",

    # Agent Tool
    "agent_tool",
    "AgentTool",

    # Specialized Agents
    "GeneralPurposeAgent",
    "ExploreAgent",
    "PlanAgent",
    "StatuslineSetupAgent",

    # Registry
    "agent_registry",
    "register_agent_type",
    "get_agent_class",

    # Registration function
    "register_agent_system_tools"
]


def register_agent_system_tools():
    """Register agent system tools with the ACP registry."""
    from ..acp_integration import register_acp_tool

    register_acp_tool(agent_tool)