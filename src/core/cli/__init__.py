"""
Enhanced CLI Experience for DevMind.

Provides improved command-line interface features including auto-completion,
enhanced help, interactive prompts, and better output formatting.
"""

from .cli_manager import (
    CLIManager, CLICommand, CLIArgument, ArgumentType,
    get_cli_manager
)
from .help_system import (
    HelpSystem, HelpEntry,
    get_help_system
)
from .output_formatter import (
    OutputFormatter, OutputStyle, Color,
    get_output_formatter
)
from .interactive_prompts import (
    InteractivePrompter, PromptType,
    get_interactive_prompter
)
from .completion_system import (
    CompletionSystem, CompletionProvider,
    get_completion_system
)

__all__ = [
    # CLI Management
    "CLIManager",
    "CLICommand",
    "CLIArgument",
    "ArgumentType",
    "get_cli_manager",

    # Help System
    "HelpSystem",
    "HelpEntry",
    "get_help_system",

    # Output Formatting
    "OutputFormatter",
    "OutputStyle",
    "Color",
    "get_output_formatter",

    # Interactive Prompts
    "InteractivePrompter",
    "PromptType",
    "get_interactive_prompter",

    # Completion System
    "CompletionSystem",
    "CompletionProvider",
    "get_completion_system"
]