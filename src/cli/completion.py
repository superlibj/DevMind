"""
Auto-completion and command suggestions for DevMind CLI.

Provides intelligent tab completion for commands, filenames, and session names,
along with interactive command selection when typing '/'.
"""
import os
from typing import List, Optional, Dict, Any, Iterable
from pathlib import Path

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.formatted_text import FormattedText


class DevMindCompleter(Completer):
    """Smart completer for DevMind CLI commands and arguments."""

    def __init__(self, repl_instance):
        """Initialize completer with reference to REPL instance.

        Args:
            repl_instance: Reference to DevMindREPL instance for accessing commands and sessions
        """
        self.repl = repl_instance

        # Available commands (without the '/' prefix for internal use)
        self.commands = {
            "help": "Show detailed help information",
            "model": "Switch to a different LLM model",
            "models": "List all available models",
            "save": "Save current conversation session",
            "load": "Load a saved conversation session",
            "sessions": "List all saved sessions",
            "delete": "Delete a saved session",
            "export": "Export session to file (markdown/json)",
            "clear": "Clear current conversation",
            "status": "Show conversation and agent status",
            "tokens": "Show current token usage statistics",
            "usage": "Show detailed usage report",
            "cost": "Show cost breakdown by model",
            "iterations": "Toggle thinking process display",
            "exit": "Exit DevMind",
            "quit": "Exit DevMind"
        }

        # Command argument patterns
        self.command_args = {
            "model": self._get_model_completions,
            "save": self._get_session_name_completions,
            "load": self._get_existing_session_completions,
            "delete": self._get_existing_session_completions,
            "export": self._get_export_completions,
            "models": lambda: ["openai", "anthropic", "deepseek"],
            "iterations": lambda: ["on", "off", "show", "hide"],
            "usage": lambda: ["--export"]
        }

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Generate completions based on current input."""
        text = document.text

        # Handle command completion (starts with '/')
        if text.startswith('/'):
            yield from self._complete_commands(document)
        else:
            # For non-command text, provide basic filename completion
            yield from self._complete_files(document)

    def _complete_commands(self, document: Document) -> Iterable[Completion]:
        """Complete DevMind commands starting with '/'."""
        text = document.text[1:]  # Remove leading '/'
        words = text.split()

        if not words or (len(words) == 1 and not text.endswith(' ')):
            # Complete command name
            prefix = words[0] if words else ""
            for cmd_name, description in self.commands.items():
                if cmd_name.startswith(prefix):
                    yield Completion(
                        text=cmd_name,
                        start_position=-len(prefix),
                        display=f"{cmd_name}",
                        display_meta=description
                    )
        else:
            # Complete command arguments
            cmd_name = words[0]
            if cmd_name in self.command_args:
                current_arg = words[-1] if not text.endswith(' ') else ""

                arg_completions = self.command_args[cmd_name]()
                if isinstance(arg_completions, list):
                    for arg in arg_completions:
                        if arg.startswith(current_arg):
                            yield Completion(
                                text=arg,
                                start_position=-len(current_arg),
                                display=arg
                            )

    def _complete_files(self, document: Document) -> Iterable[Completion]:
        """Complete file and directory paths."""
        text = document.text

        # Find the last word that might be a path
        words = text.split()
        if not words:
            return

        current_path = words[-1]

        try:
            if '/' in current_path:
                # Path contains directory separator
                dir_path = Path(current_path).parent
                prefix = Path(current_path).name
            else:
                # No path separator, complete in current directory
                dir_path = Path('.')
                prefix = current_path

            if dir_path.exists():
                for item in dir_path.iterdir():
                    item_name = item.name
                    if item_name.startswith(prefix):
                        display_name = item_name + ('/' if item.is_dir() else '')
                        yield Completion(
                            text=item_name,
                            start_position=-len(prefix),
                            display=display_name,
                            display_meta="directory" if item.is_dir() else "file"
                        )

        except (OSError, PermissionError):
            # Ignore errors in file completion
            pass

    def _get_model_completions(self) -> List[str]:
        """Get available model names for completion."""
        try:
            from ..core.llm.model_config import model_config_manager
            models = model_config_manager.list_models()
            return [model.name for model in models]
        except Exception:
            # Fallback to common models
            return [
                "gpt-4", "gpt-3.5-turbo", "gpt-4-turbo-preview",
                "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
                "deepseek-chat", "deepseek-coder-v2"
            ]

    def _get_session_name_completions(self) -> List[str]:
        """Get session name suggestions (common patterns)."""
        return [
            "web-project", "api-development", "debugging-session",
            "code-review", "refactoring", "feature-development"
        ]

    def _get_existing_session_completions(self) -> List[str]:
        """Get existing session names for completion."""
        try:
            sessions = self.repl.session_manager.list_sessions()
            return [session['name'] for session in sessions]
        except Exception:
            return []

    def _get_export_completions(self) -> List[str]:
        """Get export format completions."""
        return ["markdown", "json"]


class DevMindCommandSelector:
    """Interactive command selector for when user types '/'."""

    def __init__(self, completer: DevMindCompleter):
        """Initialize command selector.

        Args:
            completer: DevMindCompleter instance to get command list
        """
        self.completer = completer

    def format_commands_for_display(self) -> List[tuple]:
        """Format commands for interactive selection.

        Returns:
            List of (command, description) tuples
        """
        commands = []
        for cmd_name, description in self.completer.commands.items():
            commands.append((f"/{cmd_name}", description))
        return sorted(commands)

    def get_formatted_text_commands(self) -> FormattedText:
        """Get formatted text for command display."""
        formatted = FormattedText([])
        for cmd, desc in self.format_commands_for_display():
            formatted.append(('class:command', f"{cmd:<15}"))
            formatted.append(('class:description', f"  {desc}"))
            formatted.append(('', '\n'))
        return formatted


def create_completer(repl_instance) -> DevMindCompleter:
    """Create and configure the DevMind completer.

    Args:
        repl_instance: DevMindREPL instance

    Returns:
        Configured DevMindCompleter instance
    """
    return DevMindCompleter(repl_instance)