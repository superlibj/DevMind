"""
Session management for DevMind CLI.

Handles persistent conversation history, session save/load,
and cross-session context restoration.
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from rich.console import Console
from rich.table import Table

console = Console()

@dataclass
class SessionMetadata:
    """Metadata for a conversation session."""
    name: str
    created_at: float
    last_accessed: float
    message_count: int
    model_used: Optional[str] = None
    description: Optional[str] = None


class SessionManager:
    """Manages persistent conversation sessions."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        """Initialize session manager.

        Args:
            sessions_dir: Directory to store session files
        """
        if sessions_dir is None:
            # Default to sessions directory in project root
            project_root = Path(__file__).parent.parent.parent
            sessions_dir = project_root / "sessions"

        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)

    def _get_session_file(self, session_name: str) -> Path:
        """Get the file path for a session.

        Args:
            session_name: Name of the session

        Returns:
            Path to session file
        """
        # Sanitize session name for filename
        safe_name = "".join(c for c in session_name if c.isalnum() or c in "._-")
        return self.sessions_dir / f"{safe_name}.json"

    def save_session(
        self,
        session_name: str,
        conversation_data: Dict[str, Any],
        model: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """Save a session to disk.

        Args:
            session_name: Name for the session
            conversation_data: Conversation history and state
            model: Model used in the session
            description: Optional description

        Returns:
            True if saved successfully
        """
        try:
            session_file = self._get_session_file(session_name)

            # Get message count
            message_count = 0
            if "conversation" in conversation_data:
                message_count = len(conversation_data["conversation"])

            # Create session metadata
            now = time.time()
            metadata = SessionMetadata(
                name=session_name,
                created_at=conversation_data.get("created_at", now),
                last_accessed=now,
                message_count=message_count,
                model_used=model,
                description=description
            )

            # Prepare session data
            session_data = {
                "metadata": asdict(metadata),
                "conversation": conversation_data,
                "format_version": "1.0"
            }

            # Save to file
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            console.print(f"[green]Session saved: {session_name}[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Failed to save session: {e}[/red]")
            return False

    def load_session(self, session_name: str) -> Optional[Dict[str, Any]]:
        """Load a session from disk.

        Args:
            session_name: Name of the session to load

        Returns:
            Session data if found, None otherwise
        """
        try:
            session_file = self._get_session_file(session_name)

            if not session_file.exists():
                console.print(f"[yellow]Session not found: {session_name}[/yellow]")
                return None

            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Update last accessed time
            if "metadata" in session_data:
                session_data["metadata"]["last_accessed"] = time.time()

                # Save updated metadata
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)

            return session_data.get("conversation", {})

        except Exception as e:
            console.print(f"[red]Failed to load session: {e}[/red]")
            return None

    def list_sessions(self) -> List[SessionMetadata]:
        """List all available sessions.

        Returns:
            List of session metadata
        """
        sessions = []

        try:
            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)

                    if "metadata" in session_data:
                        metadata = SessionMetadata(**session_data["metadata"])
                        sessions.append(metadata)

                except Exception as e:
                    console.print(f"[yellow]Warning: Could not read session {session_file.name}: {e}[/yellow]")

            # Sort by last accessed time (most recent first)
            sessions.sort(key=lambda s: s.last_accessed, reverse=True)

        except Exception as e:
            console.print(f"[red]Failed to list sessions: {e}[/red]")

        return sessions

    def delete_session(self, session_name: str) -> bool:
        """Delete a session.

        Args:
            session_name: Name of the session to delete

        Returns:
            True if deleted successfully
        """
        try:
            session_file = self._get_session_file(session_name)

            if not session_file.exists():
                console.print(f"[yellow]Session not found: {session_name}[/yellow]")
                return False

            session_file.unlink()
            console.print(f"[green]Session deleted: {session_name}[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Failed to delete session: {e}[/red]")
            return False

    def export_session(
        self,
        session_name: str,
        output_file: Path,
        format: str = "markdown"
    ) -> bool:
        """Export a session to a file.

        Args:
            session_name: Name of the session to export
            output_file: Path to output file
            format: Export format ("markdown" or "json")

        Returns:
            True if exported successfully
        """
        try:
            session_data = self.load_session(session_name)
            if not session_data:
                return False

            if format.lower() == "markdown":
                return self._export_as_markdown(session_data, output_file)
            elif format.lower() == "json":
                return self._export_as_json(session_data, output_file)
            else:
                console.print(f"[red]Unknown export format: {format}[/red]")
                return False

        except Exception as e:
            console.print(f"[red]Failed to export session: {e}[/red]")
            return False

    def _export_as_markdown(self, session_data: Dict[str, Any], output_file: Path) -> bool:
        """Export session as Markdown."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# DevMind Session Export\n\n")
                f.write(f"**Exported at:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                conversation = session_data.get("conversation", [])
                for msg in conversation:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")

                    if role == "user":
                        f.write(f"## User\n\n{content}\n\n")
                    elif role == "assistant":
                        f.write(f"## Assistant\n\n{content}\n\n")

            console.print(f"[green]Session exported to: {output_file}[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Failed to export as Markdown: {e}[/red]")
            return False

    def _export_as_json(self, session_data: Dict[str, Any], output_file: Path) -> bool:
        """Export session as JSON."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            console.print(f"[green]Session exported to: {output_file}[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Failed to export as JSON: {e}[/red]")
            return False

    def show_sessions_table(self) -> None:
        """Display a table of all sessions."""
        sessions = self.list_sessions()

        if not sessions:
            console.print("[yellow]No saved sessions found.[/yellow]")
            return

        table = Table(title="Saved Sessions")
        table.add_column("Name", style="cyan")
        table.add_column("Messages", justify="right", style="magenta")
        table.add_column("Model", style="green")
        table.add_column("Last Accessed", style="blue")
        table.add_column("Description", style="white")

        for session in sessions:
            last_accessed = time.strftime(
                "%Y-%m-%d %H:%M",
                time.localtime(session.last_accessed)
            )

            table.add_row(
                session.name,
                str(session.message_count),
                session.model_used or "Unknown",
                last_accessed,
                session.description or ""
            )

        console.print(table)

    def get_session_metadata(self, session_name: str) -> Optional[SessionMetadata]:
        """Get metadata for a specific session.

        Args:
            session_name: Name of the session

        Returns:
            SessionMetadata if found, None otherwise
        """
        try:
            session_file = self._get_session_file(session_name)

            if not session_file.exists():
                return None

            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            if "metadata" in session_data:
                return SessionMetadata(**session_data["metadata"])

        except Exception as e:
            console.print(f"[red]Failed to get session metadata: {e}[/red]")

        return None