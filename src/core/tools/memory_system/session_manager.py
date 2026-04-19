"""
Enhanced Session Manager for DevMind with memory integration.

Provides comprehensive session management with memory integration,
context persistence, and conversation state tracking.
"""
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

from .memory_manager import get_memory_manager, MemoryTopic

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Session data model with memory integration."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    memory_snapshots: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create from dictionary."""
        return cls(**data)

    @property
    def age_hours(self) -> float:
        """Get session age in hours."""
        return (time.time() - self.created_at) / 3600

    @property
    def idle_hours(self) -> float:
        """Get idle time in hours."""
        return (time.time() - self.last_accessed) / 3600


class EnhancedSessionManager:
    """Enhanced session manager with memory integration."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        """Initialize enhanced session manager.

        Args:
            sessions_dir: Directory for session storage
        """
        self.sessions_dir = sessions_dir or Path("sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Session storage
        self.sessions: Dict[str, SessionData] = {}
        self.current_session: Optional[SessionData] = None

        # Memory integration
        self.memory_manager = get_memory_manager()

        # Session management settings
        self.max_sessions = 50
        self.session_cleanup_hours = 24 * 7  # 7 days
        self.auto_save_interval = 300  # 5 minutes

        # Load existing sessions
        self._load_sessions()

    def create_session(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionData:
        """Create a new session.

        Args:
            session_id: Optional session ID
            metadata: Optional metadata

        Returns:
            Created session data
        """
        if not session_id:
            session_id = f"session_{int(time.time())}"

        session = SessionData(
            session_id=session_id,
            metadata=metadata or {}
        )

        self.sessions[session_id] = session
        self.current_session = session

        # Persist session
        self._save_session(session)

        logger.info(f"Created session: {session_id}")
        return session

    def load_session(self, session_id: str) -> Optional[SessionData]:
        """Load an existing session.

        Args:
            session_id: Session ID to load

        Returns:
            Session data if found, None otherwise
        """
        session = self.sessions.get(session_id)
        if session:
            session.last_accessed = time.time()
            self.current_session = session
            self._save_session(session)
            logger.info(f"Loaded session: {session_id}")
            return session

        # Try to load from file
        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                session = SessionData.from_dict(data)
                session.last_accessed = time.time()
                self.sessions[session_id] = session
                self.current_session = session

                logger.info(f"Loaded session from file: {session_id}")
                return session

            except Exception as e:
                logger.error(f"Error loading session {session_id}: {e}")

        return None

    def save_current_session(self):
        """Save the current session."""
        if self.current_session:
            self._save_session(self.current_session)

    def add_conversation_entry(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add an entry to the conversation history.

        Args:
            role: Role (user, assistant, system)
            content: Message content
            metadata: Optional metadata
        """
        if not self.current_session:
            self.create_session()

        entry = {
            "timestamp": time.time(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }

        self.current_session.conversation_history.append(entry)
        self.current_session.last_accessed = time.time()

        # Auto-save periodically
        if len(self.current_session.conversation_history) % 10 == 0:
            self.save_current_session()

    def update_context_data(self, key: str, value: Any):
        """Update context data for the current session.

        Args:
            key: Context key
            value: Context value
        """
        if not self.current_session:
            self.create_session()

        self.current_session.context_data[key] = value
        self.current_session.last_accessed = time.time()

    def set_user_preference(self, key: str, value: Any):
        """Set a user preference for the current session.

        Args:
            key: Preference key
            value: Preference value
        """
        if not self.current_session:
            self.create_session()

        self.current_session.user_preferences[key] = value
        self.current_session.last_accessed = time.time()

        # Also remember in persistent memory
        self.memory_manager.remember_user_preference(key, str(value))

    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference.

        Args:
            key: Preference key
            default: Default value

        Returns:
            Preference value or default
        """
        if self.current_session:
            return self.current_session.user_preferences.get(key, default)
        return default

    def capture_memory_snapshot(self):
        """Capture current memory state for session."""
        if not self.current_session:
            return

        # Capture key memories from each topic
        snapshots = {}
        for topic in MemoryTopic:
            memories = self.memory_manager.get_topic_memories(topic)
            # Store top 3 memories per topic
            top_memories = sorted(memories, key=lambda x: (-x.priority, -x.timestamp))[:3]
            snapshots[topic.value] = [mem.content for mem in top_memories]

        self.current_session.memory_snapshots = snapshots
        self.current_session.last_accessed = time.time()

    def get_session_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of session information.

        Args:
            session_id: Optional session ID (uses current if not provided)

        Returns:
            Session summary
        """
        session = self.current_session
        if session_id:
            session = self.sessions.get(session_id)

        if not session:
            return {}

        return {
            "session_id": session.session_id,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session.created_at)),
            "last_accessed": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session.last_accessed)),
            "age_hours": round(session.age_hours, 2),
            "idle_hours": round(session.idle_hours, 2),
            "conversation_entries": len(session.conversation_history),
            "context_keys": list(session.context_data.keys()),
            "user_preferences": len(session.user_preferences),
            "memory_topics": list(session.memory_snapshots.keys()) if session.memory_snapshots else []
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions with summary information.

        Returns:
            List of session summaries
        """
        summaries = []
        for session in self.sessions.values():
            summary = {
                "session_id": session.session_id,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session.created_at)),
                "last_accessed": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session.last_accessed)),
                "age_hours": round(session.age_hours, 2),
                "conversation_entries": len(session.conversation_history),
                "is_current": session == self.current_session
            }
            summaries.append(summary)

        # Sort by last accessed (most recent first)
        summaries.sort(key=lambda x: x["last_accessed"], reverse=True)
        return summaries

    def cleanup_old_sessions(self):
        """Clean up old sessions."""
        cutoff_time = time.time() - (self.session_cleanup_hours * 3600)
        sessions_to_remove = []

        for session_id, session in self.sessions.items():
            if session.last_accessed < cutoff_time and session != self.current_session:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            self._delete_session(session_id)

        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")

    def _save_session(self, session: SessionData):
        """Save session to file."""
        try:
            session_file = self.sessions_dir / f"{session.session_id}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2)

        except Exception as e:
            logger.error(f"Error saving session {session.session_id}: {e}")

    def _load_sessions(self):
        """Load sessions from files."""
        try:
            for session_file in self.sessions_dir.glob("session_*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    session = SessionData.from_dict(data)
                    self.sessions[session.session_id] = session

                except Exception as e:
                    logger.warning(f"Error loading session file {session_file}: {e}")

            logger.info(f"Loaded {len(self.sessions)} existing sessions")

        except Exception as e:
            logger.error(f"Error loading sessions: {e}")

    def _delete_session(self, session_id: str):
        """Delete a session."""
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]

        # Remove file
        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            try:
                session_file.unlink()
            except Exception as e:
                logger.warning(f"Error deleting session file {session_file}: {e}")


# Global session manager instance
_session_manager = None


def get_session_manager() -> EnhancedSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = EnhancedSessionManager()
    return _session_manager