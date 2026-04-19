"""
Memory Manager for DevMind persistent memory system.

Provides topic-based memory organization, auto-memory functionality,
and cross-session persistence with intelligent content management.
"""
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import json

logger = logging.getLogger(__name__)


class MemoryTopic(Enum):
    """Memory topic categories for organization."""
    GENERAL = "general"
    PATTERNS = "patterns"
    DEBUGGING = "debugging"
    USER_PREFERENCES = "user_preferences"
    PROJECT_STRUCTURE = "project_structure"
    ARCHITECTURE = "architecture"
    TOOLS = "tools"
    WORKFLOWS = "workflows"
    SOLUTIONS = "solutions"
    CONFIGURATIONS = "configurations"


@dataclass
class MemoryEntry:
    """Individual memory entry."""
    content: str
    topic: MemoryTopic
    timestamp: float = field(default_factory=time.time)
    priority: int = 1  # 1=low, 2=medium, 3=high
    tags: Set[str] = field(default_factory=set)
    verified: bool = False
    source: str = ""  # Where this memory came from

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "topic": self.topic.value,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "tags": list(self.tags),
            "verified": self.verified,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create from dictionary."""
        return cls(
            content=data["content"],
            topic=MemoryTopic(data["topic"]),
            timestamp=data.get("timestamp", time.time()),
            priority=data.get("priority", 1),
            tags=set(data.get("tags", [])),
            verified=data.get("verified", False),
            source=data.get("source", "")
        )


class MemoryManager:
    """Manager for persistent memory and auto-memory functionality."""

    def __init__(self, memory_dir: Optional[Path] = None):
        """Initialize memory manager.

        Args:
            memory_dir: Directory for memory storage
        """
        self.memory_dir = memory_dir or Path("sessions/memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Main memory file (loaded into context)
        self.main_memory_file = self.memory_dir / "MEMORY.md"

        # Topic files
        self.topic_files = {
            topic: self.memory_dir / f"{topic.value}.md"
            for topic in MemoryTopic
        }

        # In-memory storage
        self.memories: Dict[MemoryTopic, List[MemoryEntry]] = {
            topic: [] for topic in MemoryTopic
        }

        # Load existing memories
        self._load_memories()

        # Memory management settings
        self.max_main_memory_lines = 200
        self.auto_cleanup_enabled = True

    def add_memory(
        self,
        content: str,
        topic: MemoryTopic = MemoryTopic.GENERAL,
        priority: int = 1,
        tags: Optional[Set[str]] = None,
        source: str = "",
        verified: bool = False
    ) -> MemoryEntry:
        """Add a new memory entry.

        Args:
            content: Memory content
            topic: Topic category
            priority: Priority level (1-3)
            tags: Optional tags
            source: Source of the memory
            verified: Whether this is verified information

        Returns:
            Created memory entry
        """
        entry = MemoryEntry(
            content=content,
            topic=topic,
            priority=priority,
            tags=tags or set(),
            source=source,
            verified=verified
        )

        # Add to in-memory storage
        self.memories[topic].append(entry)

        # Sort by priority and timestamp
        self.memories[topic].sort(key=lambda x: (-x.priority, -x.timestamp))

        # Update memory files
        self._update_topic_file(topic)
        self._update_main_memory_file()

        logger.info(f"Added {topic.value} memory: {content[:50]}...")
        return entry

    def search_memories(
        self,
        query: str,
        topic: Optional[MemoryTopic] = None,
        tags: Optional[Set[str]] = None
    ) -> List[MemoryEntry]:
        """Search for memories matching criteria.

        Args:
            query: Search query
            topic: Optional topic filter
            tags: Optional tag filter

        Returns:
            List of matching memory entries
        """
        query_lower = query.lower()
        results = []

        topics_to_search = [topic] if topic else list(MemoryTopic)

        for topic in topics_to_search:
            for entry in self.memories[topic]:
                # Check content match
                if query_lower in entry.content.lower():
                    # Check tag filter
                    if tags and not tags.intersection(entry.tags):
                        continue
                    results.append(entry)

        # Sort by priority and relevance
        results.sort(key=lambda x: (-x.priority, -x.timestamp))
        return results

    def get_topic_memories(self, topic: MemoryTopic) -> List[MemoryEntry]:
        """Get all memories for a specific topic."""
        return self.memories[topic].copy()

    def update_memory(
        self,
        content: str,
        new_content: str,
        topic: Optional[MemoryTopic] = None
    ) -> bool:
        """Update an existing memory entry.

        Args:
            content: Original content to find
            new_content: New content
            topic: Optional topic to limit search

        Returns:
            True if memory was updated
        """
        topics_to_search = [topic] if topic else list(MemoryTopic)

        for topic in topics_to_search:
            for entry in self.memories[topic]:
                if content.lower() in entry.content.lower():
                    entry.content = new_content
                    entry.timestamp = time.time()

                    # Update files
                    self._update_topic_file(topic)
                    self._update_main_memory_file()

                    logger.info(f"Updated {topic.value} memory")
                    return True

        return False

    def remove_memory(
        self,
        content: str,
        topic: Optional[MemoryTopic] = None
    ) -> bool:
        """Remove a memory entry.

        Args:
            content: Content to find and remove
            topic: Optional topic to limit search

        Returns:
            True if memory was removed
        """
        topics_to_search = [topic] if topic else list(MemoryTopic)

        for topic in topics_to_search:
            for i, entry in enumerate(self.memories[topic]):
                if content.lower() in entry.content.lower():
                    del self.memories[topic][i]

                    # Update files
                    self._update_topic_file(topic)
                    self._update_main_memory_file()

                    logger.info(f"Removed {topic.value} memory")
                    return True

        return False

    def get_main_memory_content(self) -> str:
        """Get the main memory file content for context loading."""
        if not self.main_memory_file.exists():
            return ""

        try:
            with open(self.main_memory_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Truncate if too long
            lines = content.split('\n')
            if len(lines) > self.max_main_memory_lines:
                truncated_lines = lines[:self.max_main_memory_lines]
                truncated_lines.append("... (additional memories in topic files)")
                content = '\n'.join(truncated_lines)

            return content

        except Exception as e:
            logger.error(f"Error reading main memory file: {e}")
            return ""

    def remember_user_preference(self, preference: str, value: str):
        """Remember a user preference."""
        content = f"User prefers: {preference} = {value}"
        self.add_memory(
            content=content,
            topic=MemoryTopic.USER_PREFERENCES,
            priority=2,
            verified=True,
            source="user_request"
        )

    def remember_pattern(self, pattern: str, context: str = ""):
        """Remember a stable pattern or convention."""
        content = f"Pattern: {pattern}"
        if context:
            content += f" (Context: {context})"

        self.add_memory(
            content=content,
            topic=MemoryTopic.PATTERNS,
            priority=2,
            verified=True,
            source="pattern_recognition"
        )

    def remember_solution(self, problem: str, solution: str):
        """Remember a solution to a recurring problem."""
        content = f"Problem: {problem}\nSolution: {solution}"
        self.add_memory(
            content=content,
            topic=MemoryTopic.SOLUTIONS,
            priority=3,
            verified=True,
            source="problem_solving"
        )

    def forget_outdated_memories(self, max_age_days: int = 30):
        """Remove memories older than specified days."""
        if not self.auto_cleanup_enabled:
            return

        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        removed_count = 0

        for topic in MemoryTopic:
            initial_count = len(self.memories[topic])
            self.memories[topic] = [
                entry for entry in self.memories[topic]
                if entry.timestamp > cutoff_time or entry.priority >= 3 or entry.verified
            ]
            removed = initial_count - len(self.memories[topic])
            removed_count += removed

            if removed > 0:
                self._update_topic_file(topic)

        if removed_count > 0:
            self._update_main_memory_file()
            logger.info(f"Cleaned up {removed_count} outdated memories")

    def _load_memories(self):
        """Load memories from files."""
        # Load from topic files
        for topic, file_path in self.topic_files.items():
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Parse markdown content into memories
                    entries = self._parse_topic_file(content, topic)
                    self.memories[topic] = entries

                except Exception as e:
                    logger.warning(f"Error loading {topic.value} memories: {e}")

    def _parse_topic_file(self, content: str, topic: MemoryTopic) -> List[MemoryEntry]:
        """Parse topic file content into memory entries."""
        entries = []
        current_entry = []

        for line in content.split('\n'):
            if line.startswith('## ') or line.startswith('### '):
                # Start of new entry
                if current_entry:
                    entry_content = '\n'.join(current_entry).strip()
                    if entry_content:
                        entries.append(MemoryEntry(
                            content=entry_content,
                            topic=topic,
                            priority=1,
                            verified=True,
                            source="file_load"
                        ))
                current_entry = [line]
            elif line.strip():
                current_entry.append(line)

        # Handle last entry
        if current_entry:
            entry_content = '\n'.join(current_entry).strip()
            if entry_content:
                entries.append(MemoryEntry(
                    content=entry_content,
                    topic=topic,
                    priority=1,
                    verified=True,
                    source="file_load"
                ))

        return entries

    def _update_topic_file(self, topic: MemoryTopic):
        """Update the topic-specific memory file."""
        file_path = self.topic_files[topic]
        memories = self.memories[topic]

        if not memories:
            # Remove empty file
            if file_path.exists():
                file_path.unlink()
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {topic.value.replace('_', ' ').title()} Memories\n\n")

                for entry in memories:
                    timestamp_str = time.strftime("%Y-%m-%d", time.localtime(entry.timestamp))

                    f.write(f"## {entry.content.split('.')[0] if '.' in entry.content else entry.content[:50]}\n\n")
                    f.write(f"{entry.content}\n\n")
                    f.write(f"*Added: {timestamp_str}*")
                    if entry.tags:
                        f.write(f" *Tags: {', '.join(entry.tags)}*")
                    f.write("\n\n")

        except Exception as e:
            logger.error(f"Error updating {topic.value} file: {e}")

    def _update_main_memory_file(self):
        """Update the main memory file with key information."""
        try:
            with open(self.main_memory_file, 'w', encoding='utf-8') as f:
                f.write("# DevMind Auto Memory\n\n")
                f.write("This file contains key memories and insights from previous conversations.\n\n")

                # Add high-priority memories from all topics
                line_count = 5  # Start with header lines

                for topic in MemoryTopic:
                    if topic == MemoryTopic.GENERAL:
                        continue  # Skip general, handle separately

                    high_priority_memories = [
                        entry for entry in self.memories[topic]
                        if entry.priority >= 2 or entry.verified
                    ]

                    if high_priority_memories and line_count < self.max_main_memory_lines - 10:
                        f.write(f"## {topic.value.replace('_', ' ').title()}\n\n")
                        line_count += 2

                        for entry in high_priority_memories[:3]:  # Max 3 per topic
                            if line_count >= self.max_main_memory_lines - 5:
                                break

                            f.write(f"- {entry.content}\n")
                            line_count += 1

                        f.write(f"\n*See {topic.value}.md for more details*\n\n")
                        line_count += 2

                # Add general memories last
                general_memories = [
                    entry for entry in self.memories[MemoryTopic.GENERAL]
                    if entry.priority >= 2
                ]

                if general_memories and line_count < self.max_main_memory_lines - 5:
                    f.write("## General Notes\n\n")
                    for entry in general_memories:
                        if line_count >= self.max_main_memory_lines - 2:
                            break
                        f.write(f"- {entry.content}\n")
                        line_count += 1

                f.write(f"\n---\n*Auto-updated: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n")

        except Exception as e:
            logger.error(f"Error updating main memory file: {e}")


# Global memory manager instance
_memory_manager = None


def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager