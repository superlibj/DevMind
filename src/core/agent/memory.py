"""
Memory management for the ReAct agent system.
"""
import json
import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in agent memory."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


@dataclass
class MemoryMessage:
    """Represents a message in agent memory."""
    type: MessageType
    content: str
    timestamp: float = None
    metadata: Optional[Dict[str, Any]] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryMessage':
        """Create from dictionary."""
        return cls(**data)

    def to_llm_message(self) -> Dict[str, Any]:
        """Convert to LLM message format."""
        role_map = {
            MessageType.USER: "user",
            MessageType.ASSISTANT: "assistant",
            MessageType.SYSTEM: "system",
            MessageType.THOUGHT: "assistant",
            MessageType.ACTION: "assistant",
            MessageType.OBSERVATION: "user",
            MessageType.TOOL_CALL: "assistant",
            MessageType.TOOL_RESULT: "user",
        }

        return {
            "role": role_map.get(self.type, "user"),
            "content": self.content
        }


class ConversationMemory:
    """Manages conversation history and context."""

    def __init__(self, max_messages: int = None):
        """Initialize conversation memory.

        Args:
            max_messages: Maximum number of messages to keep
        """
        self.max_messages = max_messages or settings.agent.conversation_history_limit
        self._messages: List[MemoryMessage] = []
        self._context: Dict[str, Any] = {}
        self._summary: Optional[str] = None

    def add_message(
        self,
        message_type: MessageType,
        content: str,
        **kwargs
    ) -> None:
        """Add a message to memory.

        Args:
            message_type: Type of message
            content: Message content
            **kwargs: Additional message fields
        """
        message = MemoryMessage(
            type=message_type,
            content=content,
            **kwargs
        )
        self._messages.append(message)

        # Trim messages if exceeding limit
        if len(self._messages) > self.max_messages:
            self._trim_messages()

        logger.debug(f"Added {message_type.value} message to memory")

    def add_user_message(self, content: str, **kwargs) -> None:
        """Add a user message."""
        self.add_message(MessageType.USER, content, **kwargs)

    def add_assistant_message(self, content: str, **kwargs) -> None:
        """Add an assistant message."""
        self.add_message(MessageType.ASSISTANT, content, **kwargs)

    def add_thought(self, content: str, **kwargs) -> None:
        """Add a thought message."""
        self.add_message(MessageType.THOUGHT, content, **kwargs)

    def add_action(
        self,
        content: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        **kwargs
    ) -> None:
        """Add an action message."""
        self.add_message(
            MessageType.ACTION,
            content,
            tool_name=tool_name,
            tool_args=tool_args,
            **kwargs
        )

    def add_observation(self, content: str, **kwargs) -> None:
        """Add an observation message."""
        self.add_message(MessageType.OBSERVATION, content, **kwargs)

    def add_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        content: str = None,
        **kwargs
    ) -> None:
        """Add a tool call message."""
        if content is None:
            content = f"Calling {tool_name} with args: {tool_args}"

        self.add_message(
            MessageType.TOOL_CALL,
            content,
            tool_name=tool_name,
            tool_args=tool_args,
            **kwargs
        )

    def add_tool_result(
        self,
        tool_name: str,
        result: Any,
        error: Optional[str] = None,
        **kwargs
    ) -> None:
        """Add a tool result message."""
        content = str(result) if result is not None else str(error)
        self.add_message(
            MessageType.TOOL_RESULT,
            content,
            tool_name=tool_name,
            tool_result=result,
            error=error,
            **kwargs
        )

    def get_messages(
        self,
        message_types: Optional[List[MessageType]] = None,
        limit: Optional[int] = None
    ) -> List[MemoryMessage]:
        """Get messages from memory.

        Args:
            message_types: Filter by message types
            limit: Limit number of messages returned

        Returns:
            List of memory messages
        """
        messages = self._messages

        if message_types:
            messages = [m for m in messages if m.type in message_types]

        if limit:
            messages = messages[-limit:]

        return messages

    def get_llm_messages(
        self,
        include_thoughts: bool = True,
        include_tools: bool = True,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get messages in LLM format.

        Args:
            include_thoughts: Whether to include thought messages
            include_tools: Whether to include tool messages
            limit: Limit number of messages

        Returns:
            List of LLM-formatted messages
        """
        message_types = [MessageType.USER, MessageType.ASSISTANT, MessageType.SYSTEM]

        if include_thoughts:
            message_types.extend([MessageType.THOUGHT])

        if include_tools:
            message_types.extend([
                MessageType.ACTION,
                MessageType.OBSERVATION,
                MessageType.TOOL_CALL,
                MessageType.TOOL_RESULT
            ])

        messages = self.get_messages(message_types, limit)
        return [msg.to_llm_message() for msg in messages]

    def get_recent_context(
        self,
        window_size: int = 10
    ) -> Dict[str, Any]:
        """Get recent conversation context.

        Args:
            window_size: Number of recent messages to include

        Returns:
            Context dictionary
        """
        recent_messages = self.get_messages(limit=window_size)

        # Count message types
        type_counts = {}
        for msg in recent_messages:
            type_counts[msg.type.value] = type_counts.get(msg.type.value, 0) + 1

        # Extract recent tool usage
        tool_usage = {}
        for msg in recent_messages:
            if msg.tool_name:
                tool_usage[msg.tool_name] = tool_usage.get(msg.tool_name, 0) + 1

        return {
            "recent_messages": len(recent_messages),
            "message_types": type_counts,
            "tool_usage": tool_usage,
            "last_message_type": recent_messages[-1].type.value if recent_messages else None,
            "context_data": self._context.copy()
        }

    def set_context(self, key: str, value: Any) -> None:
        """Set context data.

        Args:
            key: Context key
            value: Context value
        """
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context data.

        Args:
            key: Context key
            default: Default value if key not found

        Returns:
            Context value
        """
        return self._context.get(key, default)

    def update_context(self, updates: Dict[str, Any]) -> None:
        """Update multiple context values.

        Args:
            updates: Dictionary of updates
        """
        self._context.update(updates)

    def clear_context(self) -> None:
        """Clear all context data."""
        self._context.clear()

    def _trim_messages(self) -> None:
        """Trim messages to stay within limits."""
        if len(self._messages) <= self.max_messages:
            return

        # Always keep system messages
        system_messages = [m for m in self._messages if m.type == MessageType.SYSTEM]
        other_messages = [m for m in self._messages if m.type != MessageType.SYSTEM]

        # Keep the most recent messages
        messages_to_keep = self.max_messages - len(system_messages)
        if messages_to_keep > 0:
            other_messages = other_messages[-messages_to_keep:]

        self._messages = system_messages + other_messages

        logger.info(f"Trimmed conversation memory to {len(self._messages)} messages")

    def summarize_old_messages(self) -> Optional[str]:
        """Create a summary of old messages (placeholder for future implementation).

        Returns:
            Summary string or None
        """
        # TODO: Implement LLM-based summarization of old messages
        if len(self._messages) > self.max_messages * 0.8:
            self._summary = f"[Previous conversation with {len(self._messages)} messages]"
        return self._summary

    def export_conversation(self) -> Dict[str, Any]:
        """Export conversation to dictionary.

        Returns:
            Conversation data
        """
        return {
            "messages": [msg.to_dict() for msg in self._messages],
            "context": self._context.copy(),
            "summary": self._summary,
            "max_messages": self.max_messages,
            "export_timestamp": time.time()
        }

    def import_conversation(self, data: Dict[str, Any]) -> None:
        """Import conversation from dictionary.

        Args:
            data: Conversation data
        """
        self._messages = [
            MemoryMessage.from_dict(msg_data)
            for msg_data in data.get("messages", [])
        ]
        self._context = data.get("context", {})
        self._summary = data.get("summary")
        self.max_messages = data.get("max_messages", self.max_messages)

        logger.info(f"Imported conversation with {len(self._messages)} messages")

    def clear(self) -> None:
        """Clear all memory."""
        self._messages.clear()
        self._context.clear()
        self._summary = None
        logger.info("Cleared conversation memory")

    def __len__(self) -> int:
        """Return number of messages."""
        return len(self._messages)


class WorkingMemory:
    """Manages working memory for current task execution."""

    def __init__(self):
        """Initialize working memory."""
        self._current_task: Optional[str] = None
        self._task_context: Dict[str, Any] = {}
        self._step_history: List[Dict[str, Any]] = []
        self._variables: Dict[str, Any] = {}

    def set_current_task(self, task: str, context: Dict[str, Any] = None) -> None:
        """Set the current task.

        Args:
            task: Task description
            context: Task context
        """
        self._current_task = task
        self._task_context = context or {}
        self._step_history.clear()

        logger.info(f"Set current task: {task}")

    def get_current_task(self) -> Optional[str]:
        """Get the current task."""
        return self._current_task

    def add_step(
        self,
        step_type: str,
        description: str,
        result: Any = None,
        error: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Add a step to the history.

        Args:
            step_type: Type of step (thought, action, observation)
            description: Step description
            result: Step result
            error: Error if step failed
            metadata: Additional metadata
        """
        step = {
            "step_type": step_type,
            "description": description,
            "result": result,
            "error": error,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        self._step_history.append(step)

    def get_step_history(self) -> List[Dict[str, Any]]:
        """Get the step history."""
        return self._step_history.copy()

    def set_variable(self, name: str, value: Any) -> None:
        """Set a working memory variable.

        Args:
            name: Variable name
            value: Variable value
        """
        self._variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a working memory variable.

        Args:
            name: Variable name
            default: Default value

        Returns:
            Variable value
        """
        return self._variables.get(name, default)

    def clear_task(self) -> None:
        """Clear the current task and working memory."""
        self._current_task = None
        self._task_context.clear()
        self._step_history.clear()
        self._variables.clear()

        logger.info("Cleared working memory")

    def get_task_summary(self) -> Dict[str, Any]:
        """Get a summary of the current task state.

        Returns:
            Task summary
        """
        return {
            "current_task": self._current_task,
            "task_context": self._task_context.copy(),
            "total_steps": len(self._step_history),
            "step_types": {
                step["step_type"]: len([
                    s for s in self._step_history
                    if s["step_type"] == step["step_type"]
                ])
                for step in self._step_history
            },
            "variables": list(self._variables.keys()),
            "last_step": self._step_history[-1] if self._step_history else None
        }