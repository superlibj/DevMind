"""
Command Completion System for DevMind CLI.

Provides intelligent auto-completion for commands, arguments, and context-aware suggestions.
"""
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

from .cli_manager import get_cli_manager


class CompletionProvider(ABC):
    """Base class for completion providers."""

    @abstractmethod
    def get_completions(self, context: Dict[str, Any]) -> List[str]:
        """Get completions for the given context.

        Args:
            context: Completion context

        Returns:
            List of completion suggestions
        """
        pass


class CommandCompletionProvider(CompletionProvider):
    """Completion provider for command names."""

    def get_completions(self, context: Dict[str, Any]) -> List[str]:
        """Get command name completions."""
        partial = context.get("partial", "")
        cli_manager = get_cli_manager()

        # Get command suggestions
        suggestions = cli_manager.get_command_suggestions(partial)
        return suggestions


class FileCompletionProvider(CompletionProvider):
    """Completion provider for file paths."""

    def get_completions(self, context: Dict[str, Any]) -> List[str]:
        """Get file path completions."""
        partial = context.get("partial", "")
        directory_only = context.get("directory_only", False)

        # Handle empty partial
        if not partial:
            partial = "."

        # Split into directory and filename parts
        if "/" in partial:
            directory = os.path.dirname(partial)
            filename_partial = os.path.basename(partial)
        else:
            directory = "."
            filename_partial = partial

        # Expand user home directory
        directory = os.path.expanduser(directory)

        # Get directory contents
        try:
            if os.path.isdir(directory):
                items = os.listdir(directory)
            else:
                return []
        except PermissionError:
            return []

        # Filter and format completions
        completions = []
        for item in items:
            # Skip hidden files unless explicitly requested
            if item.startswith('.') and not filename_partial.startswith('.'):
                continue

            # Check if it matches the partial
            if not item.startswith(filename_partial):
                continue

            item_path = os.path.join(directory, item)

            # Filter by type if requested
            if directory_only and not os.path.isdir(item_path):
                continue

            # Format the completion
            if directory == ".":
                completion = item
            else:
                completion = os.path.join(directory, item)

            # Add trailing slash for directories
            if os.path.isdir(item_path):
                completion += "/"

            completions.append(completion)

        return sorted(completions)


class GitBranchCompletionProvider(CompletionProvider):
    """Completion provider for git branch names."""

    def get_completions(self, context: Dict[str, Any]) -> List[str]:
        """Get git branch completions."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "branch", "-a"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                return []

            branches = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    continue

                # Remove current branch indicator and remote prefixes
                if line.startswith('*'):
                    line = line[1:].strip()

                if line.startswith('remotes/origin/'):
                    line = line.replace('remotes/origin/', '')

                # Skip HEAD references
                if 'HEAD' in line or '->' in line:
                    continue

                branches.append(line)

            # Remove duplicates and sort
            return sorted(list(set(branches)))

        except Exception:
            return []


class AgentTypeCompletionProvider(CompletionProvider):
    """Completion provider for agent types."""

    def get_completions(self, context: Dict[str, Any]) -> List[str]:
        """Get agent type completions."""
        from ..tools.agent_system import AgentType

        agent_types = [agent_type.value for agent_type in AgentType]
        return agent_types


class ToolCompletionProvider(CompletionProvider):
    """Completion provider for tool names."""

    def get_completions(self, context: Dict[str, Any]) -> List[str]:
        """Get tool name completions."""
        from ..tools import acp_registry

        tool_names = [spec.name for spec in acp_registry.list_tools()]
        return sorted(tool_names)


class CompletionSystem:
    """Central completion system managing all completion providers."""

    def __init__(self):
        """Initialize completion system."""
        self.providers: Dict[str, CompletionProvider] = {}

        # Register built-in providers
        self._register_builtin_providers()

    def register_provider(self, name: str, provider: CompletionProvider):
        """Register a completion provider.

        Args:
            name: Provider name
            provider: Completion provider instance
        """
        self.providers[name] = provider

    def get_completions(
        self,
        provider_name: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Get completions from a specific provider.

        Args:
            provider_name: Name of the provider to use
            context: Completion context

        Returns:
            List of completion suggestions
        """
        provider = self.providers.get(provider_name)
        if not provider:
            return []

        try:
            return provider.get_completions(context)
        except Exception:
            return []

    def get_command_completions(self, partial: str) -> List[str]:
        """Get command completions.

        Args:
            partial: Partial command

        Returns:
            List of command suggestions
        """
        return self.get_completions("commands", {"partial": partial})

    def get_file_completions(
        self,
        partial: str,
        directory_only: bool = False
    ) -> List[str]:
        """Get file path completions.

        Args:
            partial: Partial file path
            directory_only: Whether to show only directories

        Returns:
            List of file path suggestions
        """
        return self.get_completions("files", {
            "partial": partial,
            "directory_only": directory_only
        })

    def get_contextual_completions(
        self,
        command: str,
        argument: str,
        partial: str
    ) -> List[str]:
        """Get context-aware completions based on command and argument.

        Args:
            command: Current command
            argument: Current argument
            partial: Partial input

        Returns:
            List of contextual suggestions
        """
        # Map commands to appropriate completion providers
        completion_mapping = {
            "agent": {
                "type": "agent_types",
                "subagent_type": "agent_types"
            },
            "git": {
                "branch": "git_branches"
            },
            "worktree": {
                "name": "files",  # Could be enhanced
                "branch": "git_branches"
            },
            "config": {
                "key": lambda: ["color", "verbose", "debug", "interactive", "pager", "auto_completion"]
            }
        }

        # Check if we have specific completion rules for this command
        if command in completion_mapping:
            arg_mapping = completion_mapping[command]

            if argument in arg_mapping:
                provider_or_func = arg_mapping[argument]

                if callable(provider_or_func):
                    # Direct function
                    return provider_or_func()
                else:
                    # Provider name
                    return self.get_completions(provider_or_func, {"partial": partial})

        # Default to file completions for most arguments
        return self.get_file_completions(partial)

    def generate_bash_completion_script(self) -> str:
        """Generate bash completion script for DevMind.

        Returns:
            Bash completion script
        """
        script = '''
_devmind_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Command completions
    if [ $COMP_CWORD -eq 1 ]; then
        opts="agent git worktree config help version"
        COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
        return 0
    fi

    # Subcommand completions
    case "${COMP_WORDS[1]}" in
        agent)
            case $COMP_CWORD in
                2)
                    opts="general-purpose Explore Plan statusline-setup"
                    COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
                    ;;
                *)
                    # File completion for other arguments
                    COMPREPLY=($(compgen -f -- ${cur}))
                    ;;
            esac
            ;;
        git)
            case $COMP_CWORD in
                2)
                    opts="commit status pull push branch"
                    COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
                    ;;
            esac
            ;;
        config)
            case $COMP_CWORD in
                2)
                    opts="list get set reset"
                    COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
                    ;;
                3)
                    if [ "$prev" = "get" ] || [ "$prev" = "set" ]; then
                        opts="color verbose debug interactive pager auto_completion"
                        COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
                    fi
                    ;;
            esac
            ;;
        *)
            # Default file completion
            COMPREPLY=($(compgen -f -- ${cur}))
            ;;
    esac
}

complete -F _devmind_completion devmind
'''
        return script.strip()

    def generate_zsh_completion_script(self) -> str:
        """Generate zsh completion script for DevMind.

        Returns:
            Zsh completion script
        """
        script = '''
#compdef devmind

_devmind() {
    local context state state_descr line
    typeset -A opt_args

    _arguments -C \\
        '1:command:->commands' \\
        '*::arg:->args'

    case $state in
        commands)
            _values 'devmind commands' \\
                'agent[Launch specialized agents]' \\
                'git[Enhanced git operations]' \\
                'worktree[Manage worktrees]' \\
                'config[Manage configuration]' \\
                'help[Show help]' \\
                'version[Show version]'
            ;;
        args)
            case $words[1] in
                agent)
                    case $CURRENT in
                        2)
                            _values 'agent types' \\
                                'general-purpose[General-purpose agent]' \\
                                'Explore[Exploration agent]' \\
                                'Plan[Planning agent]' \\
                                'statusline-setup[Statusline setup]'
                            ;;
                        *)
                            _files
                            ;;
                    esac
                    ;;
                git)
                    _values 'git commands' \\
                        'commit[Smart commit]' \\
                        'status[Git status]' \\
                        'pull[Git pull]' \\
                        'push[Git push]'
                    ;;
                config)
                    case $CURRENT in
                        2)
                            _values 'config actions' \\
                                'list[List settings]' \\
                                'get[Get setting]' \\
                                'set[Set setting]' \\
                                'reset[Reset settings]'
                            ;;
                        3)
                            _values 'config keys' \\
                                'color' 'verbose' 'debug' 'interactive' 'pager' 'auto_completion'
                            ;;
                        *)
                            _files
                            ;;
                    esac
                    ;;
                *)
                    _files
                    ;;
            esac
            ;;
    esac
}

_devmind "$@"
'''
        return script.strip()

    def _register_builtin_providers(self):
        """Register built-in completion providers."""
        self.register_provider("commands", CommandCompletionProvider())
        self.register_provider("files", FileCompletionProvider())
        self.register_provider("git_branches", GitBranchCompletionProvider())
        self.register_provider("agent_types", AgentTypeCompletionProvider())
        self.register_provider("tools", ToolCompletionProvider())


# Global completion system instance
_completion_system = None


def get_completion_system() -> CompletionSystem:
    """Get the global completion system instance."""
    global _completion_system
    if _completion_system is None:
        _completion_system = CompletionSystem()
    return _completion_system