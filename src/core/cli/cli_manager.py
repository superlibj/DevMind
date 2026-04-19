"""
CLI Manager for DevMind Enhanced CLI Experience.

Provides centralized CLI command management, argument parsing, and feature coordination.
"""
import argparse
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union

logger = logging.getLogger(__name__)


class ArgumentType(Enum):
    """Argument types for CLI commands."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    FILE = "file"
    DIRECTORY = "directory"


@dataclass
class CLIArgument:
    """CLI argument specification."""
    name: str
    type: ArgumentType = ArgumentType.STRING
    required: bool = False
    default: Any = None
    help: str = ""
    choices: Optional[List[str]] = None
    metavar: Optional[str] = None
    nargs: Optional[Union[str, int]] = None
    action: Optional[str] = None


@dataclass
class CLICommand:
    """CLI command specification."""
    name: str
    description: str
    handler: Callable
    arguments: List[CLIArgument] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    category: str = "general"
    hidden: bool = False


class CLIManager:
    """Manager for enhanced CLI experience."""

    def __init__(self):
        """Initialize CLI manager."""
        self.commands: Dict[str, CLICommand] = {}
        self.global_arguments: List[CLIArgument] = []
        self.parser: Optional[argparse.ArgumentParser] = None
        self.subparsers: Optional[argparse._SubParsersAction] = None

        # CLI configuration
        self.config = {
            "color": True,
            "interactive": True,
            "verbose": False,
            "debug": False,
            "pager": True,
            "auto_completion": True
        }

        # Command categories
        self.categories = {
            "core": "Core Commands",
            "development": "Development Tools",
            "git": "Git Operations",
            "system": "System Management",
            "agent": "Agent Operations",
            "worktree": "Worktree Management",
            "general": "General Commands"
        }

        # Initialize built-in commands
        self._register_builtin_commands()

    def register_command(self, command: CLICommand):
        """Register a new CLI command.

        Args:
            command: Command specification to register
        """
        self.commands[command.name] = command

        # Register aliases
        for alias in command.aliases:
            self.commands[alias] = command

        logger.debug(f"Registered CLI command: {command.name}")

    def register_global_argument(self, argument: CLIArgument):
        """Register a global argument available to all commands.

        Args:
            argument: Global argument specification
        """
        self.global_arguments.append(argument)

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser with all registered commands.

        Returns:
            Configured ArgumentParser instance
        """
        # Create main parser
        parser = argparse.ArgumentParser(
            prog="devmind",
            description="DevMind - AI-powered development assistant",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_epilog()
        )

        # Add global arguments
        for arg in self.global_arguments:
            self._add_argument_to_parser(parser, arg)

        # Add built-in global options
        parser.add_argument(
            "--color",
            action="store_true",
            default=self.config["color"],
            help="Enable colored output"
        )
        parser.add_argument(
            "--no-color",
            dest="color",
            action="store_false",
            help="Disable colored output"
        )
        parser.add_argument(
            "-v", "--verbose",
            action="store_true",
            default=self.config["verbose"],
            help="Enable verbose output"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            default=self.config["debug"],
            help="Enable debug output"
        )
        parser.add_argument(
            "--version",
            action="version",
            version="%(prog)s 1.0.0"
        )

        # Create subparsers for commands
        subparsers = parser.add_subparsers(
            dest="command",
            title="Commands",
            description="Available DevMind commands",
            help="Use 'devmind <command> --help' for command-specific help"
        )

        # Add commands to subparsers
        added_commands = set()
        for command in self.commands.values():
            if command.hidden:
                continue

            # Skip if already added (handles aliases and duplicates)
            if command.name in added_commands:
                continue

            added_commands.add(command.name)

            cmd_parser = subparsers.add_parser(
                command.name,
                aliases=command.aliases,
                help=command.description,
                description=command.description,
                formatter_class=argparse.RawDescriptionHelpFormatter,
                epilog=self._get_command_epilog(command)
            )

            # Add command arguments
            for arg in command.arguments:
                self._add_argument_to_parser(cmd_parser, arg)

        self.parser = parser
        self.subparsers = subparsers
        return parser

    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse command line arguments.

        Args:
            args: Arguments to parse (uses sys.argv if None)

        Returns:
            Parsed arguments namespace
        """
        if not self.parser:
            self.create_parser()

        return self.parser.parse_args(args)

    async def execute_command(self, args: argparse.Namespace) -> int:
        """Execute a command based on parsed arguments.

        Args:
            args: Parsed command line arguments

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        # Update configuration from arguments
        self.config["color"] = getattr(args, "color", self.config["color"])
        self.config["verbose"] = getattr(args, "verbose", self.config["verbose"])
        self.config["debug"] = getattr(args, "debug", self.config["debug"])

        # Get command
        command_name = getattr(args, "command", None)
        if not command_name:
            # No command specified, show help
            if self.parser:
                self.parser.print_help()
            return 1

        command = self.commands.get(command_name)
        if not command:
            print(f"Unknown command: {command_name}")
            return 1

        try:
            # Execute command handler
            result = await command.handler(args)
            return result if isinstance(result, int) else 0

        except Exception as e:
            if self.config["debug"]:
                logger.exception(f"Command {command_name} failed")
            else:
                logger.error(f"Command {command_name} failed: {e}")
            return 1

    def get_command_suggestions(self, partial_command: str) -> List[str]:
        """Get command name suggestions for partial input.

        Args:
            partial_command: Partial command name

        Returns:
            List of matching command names
        """
        suggestions = []
        partial_lower = partial_command.lower()

        for command_name, command in self.commands.items():
            if command.hidden:
                continue

            # Check name match
            if command_name.lower().startswith(partial_lower):
                suggestions.append(command_name)

            # Check alias match
            for alias in command.aliases:
                if alias.lower().startswith(partial_lower):
                    suggestions.append(alias)

        return sorted(list(set(suggestions)))

    def get_commands_by_category(self) -> Dict[str, List[CLICommand]]:
        """Get commands organized by category.

        Returns:
            Dictionary mapping categories to command lists
        """
        categorized = {}

        for command in self.commands.values():
            if command.hidden:
                continue

            # Skip aliases
            if command.name not in [cmd.name for cmd in self.commands.values()]:
                continue

            category = command.category
            if category not in categorized:
                categorized[category] = []

            if command not in categorized[category]:
                categorized[category].append(command)

        return categorized

    def _register_builtin_commands(self):
        """Register built-in CLI commands."""
        # Help command
        help_cmd = CLICommand(
            name="help",
            description="Show help information for DevMind commands",
            handler=self._handle_help_command,
            arguments=[
                CLIArgument(
                    name="command",
                    type=ArgumentType.STRING,
                    required=False,
                    help="Command to get help for",
                    nargs="?"
                )
            ],
            examples=[
                "devmind help",
                "devmind help agent",
                "devmind help git commit"
            ],
            category="general"
        )
        self.register_command(help_cmd)

        # Version command
        version_cmd = CLICommand(
            name="version",
            description="Show DevMind version information",
            handler=self._handle_version_command,
            category="general"
        )
        self.register_command(version_cmd)

        # Config command
        config_cmd = CLICommand(
            name="config",
            description="Manage DevMind configuration settings",
            handler=self._handle_config_command,
            arguments=[
                CLIArgument(
                    name="action",
                    type=ArgumentType.CHOICE,
                    choices=["get", "set", "list", "reset"],
                    required=True,
                    help="Configuration action to perform"
                ),
                CLIArgument(
                    name="key",
                    type=ArgumentType.STRING,
                    required=False,
                    help="Configuration key",
                    nargs="?"
                ),
                CLIArgument(
                    name="value",
                    type=ArgumentType.STRING,
                    required=False,
                    help="Configuration value",
                    nargs="?"
                )
            ],
            examples=[
                "devmind config list",
                "devmind config get color",
                "devmind config set color true",
                "devmind config reset"
            ],
            category="system"
        )
        self.register_command(config_cmd)

    def _add_argument_to_parser(self, parser: argparse.ArgumentParser, arg: CLIArgument):
        """Add an argument to an ArgumentParser.

        Args:
            parser: ArgumentParser to add to
            arg: Argument specification
        """
        kwargs = {
            "help": arg.help,
            "default": arg.default
        }

        # Set type conversion
        if arg.type == ArgumentType.INTEGER:
            kwargs["type"] = int
        elif arg.type == ArgumentType.FLOAT:
            kwargs["type"] = float
        elif arg.type == ArgumentType.BOOLEAN:
            kwargs["action"] = "store_true" if not arg.default else "store_false"
        elif arg.type == ArgumentType.CHOICE:
            kwargs["choices"] = arg.choices

        # Set required property only for optional arguments
        if arg.required and arg.name.startswith("-"):
            kwargs["required"] = True
        if arg.metavar:
            kwargs["metavar"] = arg.metavar
        if arg.nargs:
            kwargs["nargs"] = arg.nargs
        if arg.action and arg.type != ArgumentType.BOOLEAN:
            kwargs["action"] = arg.action

        # Determine argument name format
        if arg.name.startswith("-"):
            # Optional argument
            parser.add_argument(arg.name, **kwargs)
        else:
            # Positional argument
            parser.add_argument(arg.name, **kwargs)

    def _get_epilog(self) -> str:
        """Get main parser epilog text."""
        return """
Examples:
  devmind help                    Show general help
  devmind agent explore           Launch an exploration agent
  devmind git commit              Create smart commit
  devmind worktree create         Create new worktree

For more information about a specific command:
  devmind <command> --help

Visit https://github.com/your-repo/devmind for documentation.
"""

    def _get_command_epilog(self, command: CLICommand) -> str:
        """Get epilog text for a specific command.

        Args:
            command: Command to get epilog for

        Returns:
            Epilog text
        """
        if not command.examples:
            return ""

        epilog = "\nExamples:\n"
        for example in command.examples:
            epilog += f"  {example}\n"

        return epilog

    async def _handle_help_command(self, args: argparse.Namespace) -> int:
        """Handle the help command."""
        from .help_system import get_help_system

        help_system = get_help_system()
        help_system.show_help(args.command if hasattr(args, 'command') else None)
        return 0

    async def _handle_version_command(self, args: argparse.Namespace) -> int:
        """Handle the version command."""
        print("DevMind 1.0.0")
        print("AI-powered development assistant")
        return 0

    async def _handle_config_command(self, args: argparse.Namespace) -> int:
        """Handle the config command."""
        action = args.action

        if action == "list":
            print("DevMind Configuration:")
            for key, value in self.config.items():
                print(f"  {key}: {value}")

        elif action == "get":
            if not args.key:
                print("Error: key required for 'get' action")
                return 1

            value = self.config.get(args.key)
            if value is None:
                print(f"Configuration key '{args.key}' not found")
                return 1

            print(f"{args.key}: {value}")

        elif action == "set":
            if not args.key or args.value is None:
                print("Error: both key and value required for 'set' action")
                return 1

            # Convert value to appropriate type
            if args.value.lower() in ["true", "false"]:
                self.config[args.key] = args.value.lower() == "true"
            elif args.value.isdigit():
                self.config[args.key] = int(args.value)
            else:
                self.config[args.key] = args.value

            print(f"Set {args.key} = {self.config[args.key]}")

        elif action == "reset":
            self.config = {
                "color": True,
                "interactive": True,
                "verbose": False,
                "debug": False,
                "pager": True,
                "auto_completion": True
            }
            print("Configuration reset to defaults")

        return 0


# Global CLI manager instance
_cli_manager = None


def get_cli_manager() -> CLIManager:
    """Get the global CLI manager instance."""
    global _cli_manager
    if _cli_manager is None:
        _cli_manager = CLIManager()
    return _cli_manager