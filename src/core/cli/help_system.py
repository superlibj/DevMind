"""
Enhanced Help System for DevMind CLI.

Provides comprehensive help documentation, command discovery, and interactive help.
"""
import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .output_formatter import get_output_formatter, OutputStyle


@dataclass
class HelpEntry:
    """Help entry for commands and topics."""
    name: str
    description: str
    usage: str = ""
    examples: List[str] = field(default_factory=list)
    arguments: List[str] = field(default_factory=list)
    options: List[str] = field(default_factory=list)
    see_also: List[str] = field(default_factory=list)
    details: str = ""
    category: str = "general"


class HelpSystem:
    """Enhanced help system with comprehensive documentation."""

    def __init__(self):
        """Initialize help system."""
        self.formatter = get_output_formatter()
        self.entries: Dict[str, HelpEntry] = {}
        self.topics: Dict[str, str] = {}

        # Initialize built-in help entries
        self._initialize_builtin_help()

    def register_help(self, entry: HelpEntry):
        """Register a help entry.

        Args:
            entry: Help entry to register
        """
        self.entries[entry.name] = entry

        # Register aliases or related commands
        if " " not in entry.name:  # Single command
            # Also register with common prefixes
            if entry.category != "general":
                self.entries[f"{entry.category}.{entry.name}"] = entry

    def register_topic(self, name: str, content: str):
        """Register a help topic.

        Args:
            name: Topic name
            content: Topic content
        """
        self.topics[name] = content

    def show_help(self, command: Optional[str] = None):
        """Show help information.

        Args:
            command: Specific command to show help for (shows general help if None)
        """
        if command:
            self._show_command_help(command)
        else:
            self._show_general_help()

    def search_help(self, query: str) -> List[HelpEntry]:
        """Search help entries.

        Args:
            query: Search query

        Returns:
            List of matching help entries
        """
        query_lower = query.lower()
        matches = []

        for entry in self.entries.values():
            # Check name match
            if query_lower in entry.name.lower():
                matches.append(entry)
                continue

            # Check description match
            if query_lower in entry.description.lower():
                matches.append(entry)
                continue

            # Check examples match
            for example in entry.examples:
                if query_lower in example.lower():
                    matches.append(entry)
                    break

        return matches

    def get_command_suggestions(self, partial: str) -> List[str]:
        """Get command suggestions for partial input.

        Args:
            partial: Partial command name

        Returns:
            List of suggested commands
        """
        suggestions = []
        partial_lower = partial.lower()

        for entry_name in self.entries.keys():
            if entry_name.lower().startswith(partial_lower):
                suggestions.append(entry_name)

        return sorted(suggestions)

    def _show_general_help(self):
        """Show general help overview."""
        self.formatter.print(
            self.formatter.header("DevMind - AI-Powered Development Assistant"),
            ""
        )

        self.formatter.print(
            "DevMind is an intelligent development assistant that helps you with",
            "coding tasks, git operations, project management, and more.",
            ""
        )

        # Show quick start
        self.formatter.print(self.formatter.header("Quick Start", level=2))
        self.formatter.print(self.formatter.list_items([
            "devmind help <command>     - Get help for a specific command",
            "devmind agent explore      - Explore your codebase",
            "devmind git commit         - Create smart commits",
            "devmind worktree create    - Create isolated workspace"
        ]))
        self.formatter.print("")

        # Show commands by category
        self._show_commands_by_category()

        # Show additional information
        self.formatter.print(self.formatter.header("Getting More Help", level=2))
        self.formatter.print(self.formatter.list_items([
            "Use 'devmind help <command>' for detailed command help",
            "Use 'devmind help topics' to see available help topics",
            "Use 'devmind config' to customize DevMind behavior"
        ]))
        self.formatter.print("")

        self.formatter.print(
            self.formatter.style("For more information, visit:", OutputStyle.MUTED),
            self.formatter.style("https://github.com/your-repo/devmind", OutputStyle.EMPHASIS)
        )

    def _show_command_help(self, command: str):
        """Show help for a specific command.

        Args:
            command: Command to show help for
        """
        # Try to find exact match first
        entry = self.entries.get(command)

        # Try partial matching if no exact match
        if not entry:
            matches = [e for name, e in self.entries.items() if command in name]
            if len(matches) == 1:
                entry = matches[0]
            elif len(matches) > 1:
                self._show_multiple_matches(command, matches)
                return

        # Check if it's a topic
        if not entry and command in self.topics:
            self._show_topic_help(command)
            return

        # Try searching
        if not entry:
            search_results = self.search_help(command)
            if search_results:
                self.formatter.print_warning(f"Command '{command}' not found. Did you mean:")
                for result in search_results[:5]:
                    self.formatter.print(f"  {result.name} - {result.description}")
                return
            else:
                self.formatter.print_error(f"No help found for '{command}'")
                return

        # Show command help
        self.formatter.print(
            self.formatter.header(f"DevMind Command: {entry.name}")
        )

        self.formatter.print(entry.description)
        self.formatter.print("")

        if entry.usage:
            self.formatter.print(self.formatter.header("Usage", level=2))
            self.formatter.print(self.formatter.code(entry.usage, inline=False))
            self.formatter.print("")

        if entry.arguments:
            self.formatter.print(self.formatter.header("Arguments", level=2))
            for arg in entry.arguments:
                self.formatter.print(f"  {arg}")
            self.formatter.print("")

        if entry.options:
            self.formatter.print(self.formatter.header("Options", level=2))
            for option in entry.options:
                self.formatter.print(f"  {option}")
            self.formatter.print("")

        if entry.examples:
            self.formatter.print(self.formatter.header("Examples", level=2))
            for example in entry.examples:
                self.formatter.print(self.formatter.code(f"  {example}", inline=False))
            self.formatter.print("")

        if entry.details:
            self.formatter.print(self.formatter.header("Details", level=2))
            wrapped_details = textwrap.fill(
                entry.details,
                width=self.formatter.get_terminal_width() - 2
            )
            self.formatter.print(wrapped_details)
            self.formatter.print("")

        if entry.see_also:
            self.formatter.print(self.formatter.header("See Also", level=2))
            self.formatter.print(self.formatter.list_items(entry.see_also))

    def _show_topic_help(self, topic: str):
        """Show help for a topic.

        Args:
            topic: Topic to show help for
        """
        content = self.topics.get(topic, "")
        if not content:
            self.formatter.print_error(f"Topic '{topic}' not found")
            return

        self.formatter.print(
            self.formatter.header(f"Help Topic: {topic.title()}")
        )
        self.formatter.print(content)

    def _show_multiple_matches(self, query: str, matches: List[HelpEntry]):
        """Show multiple matching commands.

        Args:
            query: Original query
            matches: List of matching entries
        """
        self.formatter.print_warning(f"Multiple commands match '{query}':")
        for match in matches:
            self.formatter.print(f"  {match.name} - {match.description}")

    def _show_commands_by_category(self):
        """Show commands organized by category."""
        # Group entries by category
        categories = {}
        for entry in self.entries.values():
            category = entry.category
            if category not in categories:
                categories[category] = []

            # Avoid duplicates (aliases point to same entry)
            if entry not in categories[category]:
                categories[category].append(entry)

        # Define category display order and names
        category_names = {
            "core": "Core Commands",
            "development": "Development Tools",
            "git": "Git Operations",
            "agent": "Agent Operations",
            "worktree": "Worktree Management",
            "system": "System Management",
            "general": "General Commands"
        }

        category_order = ["core", "development", "git", "agent", "worktree", "system", "general"]

        for category in category_order:
            if category in categories:
                category_title = category_names.get(category, category.title())
                self.formatter.print(self.formatter.header(category_title, level=2))

                for entry in sorted(categories[category], key=lambda x: x.name):
                    self.formatter.print(f"  {entry.name:<20} {entry.description}")

                self.formatter.print("")

    def _initialize_builtin_help(self):
        """Initialize built-in help entries."""
        # Core commands
        self.register_help(HelpEntry(
            name="agent",
            description="Launch specialized agents for complex tasks",
            usage="devmind agent <type> [options]",
            examples=[
                "devmind agent general-purpose --prompt 'Research the codebase'",
                "devmind agent Explore --description 'Quick exploration'",
                "devmind agent Plan --prompt 'Plan new feature implementation'"
            ],
            arguments=[
                "type           Agent type (general-purpose, Explore, Plan, etc.)"
            ],
            options=[
                "--prompt TEXT       Task prompt for the agent",
                "--description TEXT  Short task description",
                "--model TEXT        Model to use (haiku, sonnet, opus)",
                "--max-turns INT     Maximum number of turns",
                "--background        Run agent in background"
            ],
            details="Agents are specialized AI assistants that can autonomously handle complex tasks like codebase exploration, planning, and research.",
            see_also=["help background", "help tasks"],
            category="agent"
        ))

        self.register_help(HelpEntry(
            name="git",
            description="Enhanced git operations with AI assistance",
            usage="devmind git <command> [options]",
            examples=[
                "devmind git commit",
                "devmind git pr create",
                "devmind git status"
            ],
            arguments=[
                "command       Git command (commit, pr, status, etc.)"
            ],
            details="Enhanced git integration with smart commit message generation, pull request creation, and safety checks.",
            see_also=["help worktree"],
            category="git"
        ))

        self.register_help(HelpEntry(
            name="worktree",
            description="Manage isolated git worktrees",
            usage="devmind worktree [create] [options]",
            examples=[
                "devmind worktree create",
                "devmind worktree create --name feature-branch",
                "devmind worktree create --branch my-feature"
            ],
            options=[
                "--name TEXT     Worktree name",
                "--branch TEXT   Branch name for the worktree"
            ],
            details="Create isolated git worktrees for safe development without affecting the main working directory.",
            see_also=["help git"],
            category="worktree"
        ))

        # System commands
        self.register_help(HelpEntry(
            name="config",
            description="Manage DevMind configuration",
            usage="devmind config <action> [key] [value]",
            examples=[
                "devmind config list",
                "devmind config get color",
                "devmind config set color true",
                "devmind config reset"
            ],
            arguments=[
                "action        Configuration action (list, get, set, reset)",
                "key           Configuration key (for get/set)",
                "value         Configuration value (for set)"
            ],
            details="Manage DevMind settings like color output, verbosity, and other preferences.",
            category="system"
        ))

        # Command Queue System
        self.register_help(HelpEntry(
            name="queue",
            description="Manage command execution queue",
            usage="devmind queue <action> [options]",
            examples=[
                "devmind queue add --command agent --description 'Explore codebase'",
                "devmind queue list",
                "devmind queue execute",
                "devmind queue status",
                "devmind queue clear --confirm"
            ],
            arguments=[
                "action        Queue action (add, list, remove, execute, status, clear)"
            ],
            options=[
                "--command TEXT         Command to queue",
                "--description TEXT     Command description",
                "--priority TEXT        Command priority (low, normal, high, urgent)",
                "--args JSON           Command arguments",
                "--command-id TEXT     Specific command ID",
                "--status TEXT         Filter by status",
                "--wait                Wait for completion",
                "--confirm             Confirm destructive operations"
            ],
            details="Queue commands for sequential execution with priority support. Similar to Claude Code's command queuing functionality.",
            see_also=["help agent", "help background"],
            category="system"
        ))

        # Topics
        self.register_topic("getting-started", """
DevMind is designed to enhance your development workflow with AI assistance.

Key Concepts:
• Agents: Specialized AI assistants for different tasks
• Tools: Individual operations (git, file management, etc.)
• Worktrees: Isolated development environments
• Memory: Persistent learning across sessions

First Steps:
1. Explore your codebase: devmind agent Explore
2. Get AI help with git: devmind git commit
3. Create isolated workspace: devmind worktree create

Configuration:
• Enable/disable colors: devmind config set color true/false
• Set verbosity: devmind config set verbose true
• View all settings: devmind config list
        """)

        self.register_topic("agents", """
DevMind Agents are specialized AI assistants that can autonomously handle complex, multi-step tasks.

Available Agent Types:
• general-purpose: Research, multi-step tasks, full tool access
• Explore: Fast codebase exploration and understanding
• Plan: Software architecture and implementation planning
• statusline-setup: Configure status line settings

Agent Features:
• Autonomous operation with multiple tool calls
• Resume capabilities for long-running tasks
• Background execution support
• Tool access based on capabilities
• Execution summaries and logging

Examples:
• Research: devmind agent general-purpose --prompt "Find all API endpoints"
• Explore: devmind agent Explore --prompt "Quick codebase overview"
• Plan: devmind agent Plan --prompt "Plan user authentication feature"
        """)

        self.register_topic("queue", """
DevMind Command Queue System allows you to queue commands for sequential execution, similar to Claude Code.

Key Features:
• Priority-based execution (urgent, high, normal, low)
• Auto-execution mode for continuous processing
• Command persistence across sessions
• Background execution support
• Comprehensive status monitoring

Basic Queue Operations:
• Add commands: QueueAdd with command, description, and priority
• List queue: QueueList to see all queued commands
• Execute commands: QueueExecute to start processing
• Monitor status: QueueStatus for detailed statistics
• Clear queue: QueueClear to remove commands

Priority Levels:
• urgent: Execute immediately with highest priority
• high: High priority execution
• normal: Standard priority (default)
• low: Low priority, executed after others

Supported Command Types:
• agent: Spawn AI agents for complex tasks
• git: Enhanced git operations
• tool: Execute any registered tool

Auto-Execution Mode:
Enable automatic command processing that continuously executes queued commands
in the background based on priority and available execution slots.

Examples:
• Queue agent: QueueAdd --command agent --description "Code analysis" --priority high
• List queue: QueueList --show-stats true
• Execute next: QueueExecute --count 3 --wait true
• Clear completed: QueueClear --status completed --confirm true
        """)


# Global help system instance
_help_system = None


def get_help_system() -> HelpSystem:
    """Get the global help system instance."""
    global _help_system
    if _help_system is None:
        _help_system = HelpSystem()
    return _help_system