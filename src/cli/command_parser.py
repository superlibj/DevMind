"""
Command parser for DevMind CLI special commands.

Handles parsing and execution of special commands like /help, /save, /load, etc.
"""
import shlex
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..core.llm.model_config import model_config_manager

console = Console()


class CommandParser:
    """Parser for special CLI commands."""

    def __init__(self, repl_instance):
        """Initialize command parser.

        Args:
            repl_instance: Reference to the REPL instance
        """
        self.repl = repl_instance

        # Define available commands
        self.commands = {
            "help": self._help_command,
            "model": self._model_command,
            "models": self._list_models_command,
            "save": self._save_command,
            "load": self._load_command,
            "sessions": self._sessions_command,
            "delete": self._delete_command,
            "export": self._export_command,
            "clear": self._clear_command,
            "status": self._status_command,
            "exit": self._exit_command,
            "quit": self._exit_command,
        }

    async def parse_and_execute(self, command_line: str) -> bool:
        """Parse and execute a command.

        Args:
            command_line: Full command line starting with /

        Returns:
            True if command was handled, False otherwise
        """
        if not command_line.startswith("/"):
            return False

        try:
            # Remove the leading slash and parse arguments
            command_parts = shlex.split(command_line[1:])
            if not command_parts:
                return False

            command_name = command_parts[0].lower()
            args = command_parts[1:]

            # Execute command
            if command_name in self.commands:
                await self.commands[command_name](args)
                return True
            else:
                console.print(f"[red]Unknown command: /{command_name}[/red]")
                console.print("Type [cyan]/help[/cyan] to see available commands.")
                return True

        except Exception as e:
            console.print(f"[red]Command error: {e}[/red]")
            return True

    async def _help_command(self, args: List[str]) -> None:
        """Show help information."""
        help_text = """
[bold cyan]DevMind Commands[/bold cyan]

[bold]Session Management:[/bold]
• [cyan]/save <name> [description][/cyan] - Save current conversation
• [cyan]/load <name>[/cyan] - Load a saved session
• [cyan]/sessions[/cyan] - List all saved sessions
• [cyan]/delete <name>[/cyan] - Delete a session
• [cyan]/export <name> <file> [format][/cyan] - Export session (markdown/json)

[bold]Model Management:[/bold]
• [cyan]/model <model_name>[/cyan] - Switch to a different model
• [cyan]/models [provider][/cyan] - List available models

[bold]Conversation:[/bold]
• [cyan]/clear[/cyan] - Clear current conversation
• [cyan]/status[/cyan] - Show conversation status
• [cyan]/exit[/cyan] or [cyan]/quit[/cyan] - Exit DevMind

[bold]Input Tips:[/bold]
• Use [cyan]```[/cyan] for multi-line code input
• Press [cyan]Ctrl+C[/cyan] to cancel operations
• Use natural language - I understand context!

[bold]Examples:[/bold]
```
/save web-project "Working on React components"
/load web-project
/model deepseek-chat
/export web-project ./export.md markdown
```

[bold]Model Examples:[/bold]
• [cyan]claude-3-sonnet-20240229[/cyan] - Anthropic's balanced model
• [cyan]gpt-4-turbo-preview[/cyan] - Latest GPT-4
• [cyan]deepseek-chat[/cyan] - DeepSeek conversation model
• [cyan]deepseek-coder-v2[/cyan] - DeepSeek coding specialist
        """

        console.print(Panel(
            help_text,
            title="[bold blue]Help[/bold blue]",
            border_style="bright_blue"
        ))

    async def _model_command(self, args: List[str]) -> None:
        """Switch model command."""
        if not args:
            current_model = self.repl.llm.config.model
            console.print(f"Current model: [cyan]{current_model}[/cyan]")
            console.print("Use [cyan]/models[/cyan] to list available models.")
            console.print("Use [cyan]/model <model_name>[/cyan] to switch.")
            return

        model_name = args[0]

        # Validate model
        model_info = model_config_manager.get_model_info(model_name)
        if not model_info:
            console.print(f"[red]Model '{model_name}' not found.[/red]")
            console.print("Use [cyan]/models[/cyan] to see available models.")
            return

        # Switch model
        success = self.repl.switch_model(model_name)
        if success:
            console.print(f"[green]✓[/green] Switched to [cyan]{model_name}[/cyan]")
            console.print(f"Provider: [blue]{model_info.provider.value}[/blue]")
            console.print(f"Description: [dim]{model_info.description}[/dim]")

    async def _list_models_command(self, args: List[str]) -> None:
        """List available models."""
        provider_filter = args[0] if args else None

        if provider_filter:
            try:
                from ..core.llm.model_config import ProviderType
                provider = ProviderType(provider_filter.lower())
                models = model_config_manager.list_models(provider=provider)
                title = f"{provider_filter.upper()} Models"
            except ValueError:
                console.print(f"[red]Unknown provider: {provider_filter}[/red]")
                return
        else:
            models = list(model_config_manager._models.values())
            title = "Available Models"

        if not models:
            console.print("[yellow]No models found.[/yellow]")
            return

        # Group by provider
        providers = {}
        for model in models:
            provider = model.provider.value
            if provider not in providers:
                providers[provider] = []
            providers[provider].append(model)

        for provider_name, provider_models in providers.items():
            console.print(f"\n[bold bright_blue]{provider_name.upper()}:[/bold bright_blue]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Model", style="cyan", width=25)
            table.add_column("Capabilities", style="green", width=20)
            table.add_column("Context", justify="right", style="blue", width=10)
            table.add_column("Cost/1k", justify="right", style="yellow", width=8)
            table.add_column("Description", style="white", width=40)

            for model in provider_models:
                capabilities = []
                if model.supports_tools:
                    capabilities.append("tools")
                if model.supports_streaming:
                    capabilities.append("stream")

                cost = ""
                if model.cost_per_1k_input:
                    cost = f"${model.cost_per_1k_input:.4f}"

                context = f"{model.context_window//1000}k" if model.context_window >= 1000 else str(model.context_window)

                table.add_row(
                    model.name,
                    ", ".join(capabilities),
                    context,
                    cost,
                    model.description[:35] + "..." if len(model.description) > 35 else model.description
                )

            console.print(table)

    async def _save_command(self, args: List[str]) -> None:
        """Save session command."""
        if not args:
            console.print("[red]Please provide a session name.[/red]")
            console.print("Usage: [cyan]/save <name> [description][/cyan]")
            return

        session_name = args[0]
        description = " ".join(args[1:]) if len(args) > 1 else None

        success = await self.repl.save_session(session_name, description)
        if success:
            console.print(f"[green]✓[/green] Session saved as '[cyan]{session_name}[/cyan]'")

    async def _load_command(self, args: List[str]) -> None:
        """Load session command."""
        if not args:
            console.print("[red]Please provide a session name.[/red]")
            console.print("Usage: [cyan]/load <name>[/cyan]")
            console.print("Use [cyan]/sessions[/cyan] to list available sessions.")
            return

        session_name = args[0]

        success = await self.repl.load_session(session_name)
        if success:
            console.print(f"[green]✓[/green] Session '[cyan]{session_name}[/cyan]' loaded")
        else:
            console.print(f"[red]Failed to load session: {session_name}[/red]")

    async def _sessions_command(self, args: List[str]) -> None:
        """List sessions command."""
        self.repl.session_manager.show_sessions_table()

    async def _delete_command(self, args: List[str]) -> None:
        """Delete session command."""
        if not args:
            console.print("[red]Please provide a session name.[/red]")
            console.print("Usage: [cyan]/delete <name>[/cyan]")
            return

        session_name = args[0]

        # Confirm deletion
        console.print(f"[yellow]Are you sure you want to delete session '{session_name}'? [y/N][/yellow]")
        try:
            response = input().lower().strip()
            if response in ['y', 'yes']:
                if self.repl.session_manager.delete_session(session_name):
                    if self.repl.session_name == session_name:
                        self.repl.session_name = None
                        console.print("[yellow]Current session cleared.[/yellow]")
            else:
                console.print("[yellow]Deletion cancelled.[/yellow]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Deletion cancelled.[/yellow]")

    async def _export_command(self, args: List[str]) -> None:
        """Export session command."""
        if len(args) < 2:
            console.print("[red]Usage: /export <session_name> <output_file> [format][/red]")
            console.print("Format can be 'markdown' or 'json' (default: markdown)")
            return

        session_name = args[0]
        output_file = args[1]
        format_type = args[2] if len(args) > 2 else "markdown"

        from pathlib import Path
        output_path = Path(output_file)

        success = self.repl.session_manager.export_session(
            session_name,
            output_path,
            format_type
        )

        if success:
            console.print(f"[green]✓[/green] Session exported to '[cyan]{output_file}[/cyan]'")

    async def _clear_command(self, args: List[str]) -> None:
        """Clear conversation command."""
        self.repl.clear_conversation()

    async def _status_command(self, args: List[str]) -> None:
        """Show status command."""
        summary = self.repl.get_conversation_summary()
        task_summary = self.repl.agent.get_task_summary()

        status_text = f"""
[bold]Conversation Status:[/bold]
{summary}

[bold]Agent Status:[/bold]
State: [cyan]{task_summary.get('state', 'unknown')}[/cyan]
Iterations: {task_summary.get('iteration_count', 0)}/{task_summary.get('max_iterations', 0)}
Available Tools: {task_summary.get('available_tools', 0)}
        """

        console.print(Panel(
            status_text.strip(),
            title="[bold blue]Status[/bold blue]",
            border_style="bright_blue"
        ))

    async def _exit_command(self, args: List[str]) -> None:
        """Exit command."""
        console.print("[yellow]Goodbye![/yellow]")
        self.repl.running = False