"""
Auto Memory tool for managing persistent memory during execution.

Provides tools for saving, retrieving, and managing memories during
task execution with topic organization and intelligent storage.
"""
import logging
from typing import Dict, Any, Optional, List

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .memory_manager import get_memory_manager, MemoryTopic

logger = logging.getLogger(__name__)


class AutoMemoryTool(ACPTool):
    """Tool for managing auto memory during execution."""

    def __init__(self):
        """Initialize AutoMemory tool."""
        spec = ACPToolSpec(
            name="AutoMemory",
            description="Save and retrieve persistent memories across conversations",
            version="1.0.0",
            parameters={
                "required": ["action"],
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["save", "search", "update", "remove", "list_topics"],
                        "description": "Memory action to perform"
                    },
                    "content": {
                        "type": "string",
                        "description": "Memory content (for save/update actions)"
                    },
                    "topic": {
                        "type": "string",
                        "enum": [
                            "general", "patterns", "debugging", "user_preferences",
                            "project_structure", "architecture", "tools", "workflows",
                            "solutions", "configurations"
                        ],
                        "description": "Memory topic category"
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3,
                        "description": "Priority level (1=low, 2=medium, 3=high)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for the memory"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (for search action)"
                    },
                    "verified": {
                        "type": "boolean",
                        "description": "Whether this is verified information",
                        "default": False
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the memory operation request."""
        payload = message.payload

        action = payload.get("action")
        if not action:
            return "action is required"

        # Validate action-specific requirements
        if action == "save":
            if not payload.get("content"):
                return "content is required for save action"

        elif action == "search":
            if not payload.get("query"):
                return "query is required for search action"

        elif action in ["update", "remove"]:
            if not payload.get("content") and not payload.get("query"):
                return "content or query is required for update/remove actions"

        # Validate priority
        priority = payload.get("priority")
        if priority is not None and (priority < 1 or priority > 3):
            return "priority must be between 1 and 3"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the memory operation."""
        payload = message.payload
        action = payload["action"]

        try:
            memory_manager = get_memory_manager()

            if action == "save":
                return await self._handle_save(memory_manager, payload)

            elif action == "search":
                return await self._handle_search(memory_manager, payload)

            elif action == "update":
                return await self._handle_update(memory_manager, payload)

            elif action == "remove":
                return await self._handle_remove(memory_manager, payload)

            elif action == "list_topics":
                return await self._handle_list_topics(memory_manager, payload)

            else:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Unknown action: {action}"
                )

        except Exception as e:
            logger.exception(f"Error in memory operation {action}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Memory operation error: {str(e)}"
            )

    async def _handle_save(self, memory_manager, payload: Dict[str, Any]) -> ACPToolResult:
        """Handle save memory action."""
        content = payload["content"]
        topic_str = payload.get("topic", "general")
        priority = payload.get("priority", 1)
        tags = set(payload.get("tags", []))
        verified = payload.get("verified", False)

        # Convert topic string to enum
        try:
            topic = MemoryTopic(topic_str)
        except ValueError:
            topic = MemoryTopic.GENERAL

        # Save memory
        entry = memory_manager.add_memory(
            content=content,
            topic=topic,
            priority=priority,
            tags=tags,
            verified=verified,
            source="auto_memory_tool"
        )

        return ACPToolResult(
            status=ACPStatus.COMPLETED,
            result=f"✅ Memory saved to {topic.value}\n\n**Content:** {content}\n**Priority:** {priority}",
            metadata={
                "action": "saved",
                "topic": topic.value,
                "priority": priority,
                "verified": verified,
                "timestamp": entry.timestamp
            }
        )

    async def _handle_search(self, memory_manager, payload: Dict[str, Any]) -> ACPToolResult:
        """Handle search memory action."""
        query = payload["query"]
        topic_str = payload.get("topic")
        tags = set(payload.get("tags", []))

        # Convert topic string to enum if provided
        topic = None
        if topic_str:
            try:
                topic = MemoryTopic(topic_str)
            except ValueError:
                pass

        # Search memories
        results = memory_manager.search_memories(
            query=query,
            topic=topic,
            tags=tags if tags else None
        )

        if not results:
            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=f"No memories found for query: '{query}'",
                metadata={
                    "action": "search",
                    "query": query,
                    "results_count": 0
                }
            )

        # Format results
        result_lines = [
            f"**Found {len(results)} memories for '{query}':**",
            ""
        ]

        for i, entry in enumerate(results[:10], 1):  # Limit to top 10
            priority_str = "●" * entry.priority
            topic_str = entry.topic.value.replace('_', ' ').title()

            result_lines.extend([
                f"{i}. **{topic_str}** {priority_str}",
                f"   {entry.content}",
                ""
            ])

            if entry.tags:
                result_lines.extend([
                    f"   *Tags: {', '.join(entry.tags)}*",
                    ""
                ])

        if len(results) > 10:
            result_lines.append(f"... and {len(results) - 10} more results")

        return ACPToolResult(
            status=ACPStatus.COMPLETED,
            result="\n".join(result_lines),
            metadata={
                "action": "search",
                "query": query,
                "results_count": len(results),
                "topic_filter": topic.value if topic else None
            }
        )

    async def _handle_update(self, memory_manager, payload: Dict[str, Any]) -> ACPToolResult:
        """Handle update memory action."""
        content = payload.get("content")
        query = payload.get("query")
        new_content = payload.get("new_content", content)
        topic_str = payload.get("topic")

        # Convert topic string to enum if provided
        topic = None
        if topic_str:
            try:
                topic = MemoryTopic(topic_str)
            except ValueError:
                pass

        search_text = content or query
        if not search_text:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Either content or query must be provided for update"
            )

        # Update memory
        success = memory_manager.update_memory(
            content=search_text,
            new_content=new_content,
            topic=topic
        )

        if success:
            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=f"✅ Memory updated\n\n**Updated content:** {new_content}",
                metadata={
                    "action": "updated",
                    "search_text": search_text,
                    "new_content": new_content
                }
            )
        else:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Memory not found for: {search_text}"
            )

    async def _handle_remove(self, memory_manager, payload: Dict[str, Any]) -> ACPToolResult:
        """Handle remove memory action."""
        content = payload.get("content")
        query = payload.get("query")
        topic_str = payload.get("topic")

        # Convert topic string to enum if provided
        topic = None
        if topic_str:
            try:
                topic = MemoryTopic(topic_str)
            except ValueError:
                pass

        search_text = content or query
        if not search_text:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Either content or query must be provided for remove"
            )

        # Remove memory
        success = memory_manager.remove_memory(
            content=search_text,
            topic=topic
        )

        if success:
            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=f"✅ Memory removed: {search_text}",
                metadata={
                    "action": "removed",
                    "search_text": search_text
                }
            )
        else:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Memory not found for: {search_text}"
            )

    async def _handle_list_topics(self, memory_manager, payload: Dict[str, Any]) -> ACPToolResult:
        """Handle list topics action."""
        result_lines = [
            "**Available Memory Topics:**",
            ""
        ]

        for topic in MemoryTopic:
            memories = memory_manager.get_topic_memories(topic)
            count = len(memories)
            high_priority_count = len([m for m in memories if m.priority >= 2])

            topic_name = topic.value.replace('_', ' ').title()
            result_lines.append(f"• **{topic_name}** ({count} memories, {high_priority_count} high priority)")

        result_lines.extend([
            "",
            "*Use the topic names in lowercase with underscores for save/search operations*",
            "*(e.g., 'user_preferences', 'project_structure')*"
        ])

        return ACPToolResult(
            status=ACPStatus.COMPLETED,
            result="\n".join(result_lines),
            metadata={
                "action": "list_topics",
                "topics": [topic.value for topic in MemoryTopic]
            }
        )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        action = message.payload.get("action", "")
        self.logger.debug(f"Executing memory action: {action}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            action = result.metadata.get("action", "unknown")
            self.logger.info(f"Memory action completed: {action}")


# Create singleton instance
auto_memory_tool = AutoMemoryTool()