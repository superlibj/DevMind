"""
Agent Registry for managing specialized agent types.

Provides registration and lookup functionality for different agent implementations.
"""
import logging
from typing import Dict, Type, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_agent import BaseAgent
    from .agent_manager import AgentType

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing agent type implementations."""

    def __init__(self):
        """Initialize agent registry."""
        self.agent_classes: Dict['AgentType', Type['BaseAgent']] = {}

    def register_agent_type(self, agent_type: 'AgentType', agent_class: Type['BaseAgent']):
        """Register an agent implementation for a specific type.

        Args:
            agent_type: Agent type to register
            agent_class: Agent class implementation
        """
        self.agent_classes[agent_type] = agent_class
        logger.info(f"Registered agent type: {agent_type.value} -> {agent_class.__name__}")

    def get_agent_class(self, agent_type: 'AgentType') -> Optional[Type['BaseAgent']]:
        """Get agent class for a specific type.

        Args:
            agent_type: Agent type to lookup

        Returns:
            Agent class if found
        """
        return self.agent_classes.get(agent_type)

    def list_registered_types(self) -> Dict[str, str]:
        """List all registered agent types.

        Returns:
            Dict mapping agent type names to class names
        """
        return {
            agent_type.value: agent_class.__name__
            for agent_type, agent_class in self.agent_classes.items()
        }

    def is_registered(self, agent_type: 'AgentType') -> bool:
        """Check if an agent type is registered.

        Args:
            agent_type: Agent type to check

        Returns:
            True if registered
        """
        return agent_type in self.agent_classes


# Global registry instance
_agent_registry = None


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry


# Export singleton
agent_registry = get_agent_registry()


def register_agent_type(agent_type: 'AgentType', agent_class: Type['BaseAgent']):
    """Register an agent type implementation."""
    agent_registry.register_agent_type(agent_type, agent_class)


def get_agent_class(agent_type: 'AgentType') -> Optional[Type['BaseAgent']]:
    """Get agent class for a specific type."""
    return agent_registry.get_agent_class(agent_type)