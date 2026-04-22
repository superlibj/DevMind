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
from .local_models import local_model_manager, OllamaHelper, LlamaCppHelper

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
            "local": self._local_models_command,
            "ollama": self._ollama_command,
            "llamacpp": self._llamacpp_command,
            "save": self._save_command,
            "load": self._load_command,
            "sessions": self._sessions_command,
            "delete": self._delete_command,
            "export": self._export_command,
            "clear": self._clear_command,
            "status": self._status_command,
            "tokens": self._tokens_command,
            "usage": self._usage_command,
            "cost": self._cost_command,
            "iterations": self._iterations_command,
            "debug": self._debug_command,
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
• [cyan]/local[/cyan] - Show local model servers (Ollama, llama.cpp)
• [cyan]/ollama[/cyan] - Show Ollama setup and available models
• [cyan]/llamacpp[/cyan] - Show llama.cpp setup instructions

[bold]Conversation:[/bold]
• [cyan]/clear[/cyan] - Clear current conversation
• [cyan]/status[/cyan] - Show conversation status
• [cyan]/exit[/cyan] or [cyan]/quit[/cyan] - Exit DevMind

[bold]Token Usage & Cost:[/bold]
• [cyan]/tokens[/cyan] - Show current token usage statistics
• [cyan]/usage[/cyan] - Show detailed usage report
• [cyan]/usage --export <file>[/cyan] - Export usage report to file
• [cyan]/cost[/cyan] - Show cost breakdown by model

[bold]Display Options:[/bold]
• [cyan]/iterations[/cyan] - Toggle thinking process display
• [cyan]/iterations on/off[/cyan] - Explicitly enable/disable thinking display

[bold]Input Tips:[/bold]
• Use [cyan]```[/cyan] for multi-line code input
• Press [cyan]Ctrl+C[/cyan] to cancel operations
• Use natural language - I understand context!

[bold]Examples:[/bold]
```
/save web-project "Working on React components"
/load web-project
/model deepseek
/export web-project ./export.md markdown
```

[bold]Model Examples:[/bold]
• [cyan]claude-3-sonnet-20240229[/cyan] - Anthropic's balanced model
• [cyan]gpt-4-turbo-preview[/cyan] - Latest GPT-4
• [cyan]deepseek[/cyan] - DeepSeek for conversation and coding
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
                # Filter models by provider while keeping keys
                model_items = [(k, v) for k, v in model_config_manager._models.items()
                              if v.provider == provider]
                title = f"{provider_filter.upper()} Models"
            except ValueError:
                console.print(f"[red]Unknown provider: {provider_filter}[/red]")
                return
        else:
            model_items = list(model_config_manager._models.items())
            title = "Available Models"

        if not model_items:
            console.print("[yellow]No models found.[/yellow]")
            return

        # Group by provider
        providers = {}
        for model_key, model_info in model_items:
            provider = model_info.provider.value
            if provider not in providers:
                providers[provider] = []
            providers[provider].append((model_key, model_info))

        for provider_name, provider_models in providers.items():
            console.print(f"\n[bold bright_blue]{provider_name.upper()}:[/bold bright_blue]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Model", style="cyan", width=25)
            table.add_column("Capabilities", style="green", width=20)
            table.add_column("Context", justify="right", style="blue", width=10)
            table.add_column("Cost/1k", justify="right", style="yellow", width=8)
            table.add_column("Description", style="white")

            for model_key, model_info in provider_models:
                capabilities = []
                if model_info.supports_tools:
                    capabilities.append("tools")
                if model_info.supports_streaming:
                    capabilities.append("stream")

                cost = ""
                if model_info.cost_per_1k_input:
                    cost = f"${model_info.cost_per_1k_input:.4f}"

                context = f"{model_info.context_window//1000}k" if model_info.context_window >= 1000 else str(model_info.context_window)

                table.add_row(
                    model_key,  # Show the user-facing model key instead of API name
                    ", ".join(capabilities),
                    context,
                    cost,
                    model_info.description  # Show full description without truncation
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

    async def _tokens_command(self, args: List[str]) -> None:
        """Show current token usage statistics."""
        from .token_counter import token_counter
        token_counter.show_token_stats()

    async def _usage_command(self, args: List[str]) -> None:
        """Show detailed usage report or export to file."""
        from .token_counter import token_counter

        if args:
            # Export to file
            if args[0] == "--export" and len(args) > 1:
                filename = args[1]
                report = token_counter.export_usage_report()
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(report)
                    console.print(f"[green]Usage report exported to: {filename}[/green]")
                except Exception as e:
                    console.print(f"[red]Failed to export report: {e}[/red]")
            else:
                console.print("[yellow]Usage: /usage --export <filename>[/yellow]")
        else:
            # Show detailed report in console
            report = token_counter.export_usage_report()
            console.print("\n" + report)

    async def _cost_command(self, args: List[str]) -> None:
        """Show cost breakdown and estimates."""
        from .token_counter import token_counter

        # Show current session cost breakdown
        session = token_counter.session_stats
        console.print("\n[bold]💰 Cost Analysis[/bold]\n")

        if session.total_requests == 0:
            console.print("[yellow]No requests made in this session yet.[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan")
        table.add_column("Requests", justify="right", style="white")
        table.add_column("Avg Tokens/Req", justify="right", style="green")
        table.add_column("Est. Cost/Req", justify="right", style="yellow")

        # Calculate per-model statistics
        model_stats = {}
        for usage in session.request_history:
            if usage.model not in model_stats:
                model_stats[usage.model] = {
                    'requests': 0,
                    'total_tokens': 0,
                    'total_cost': 0.0
                }
            model_stats[usage.model]['requests'] += 1
            model_stats[usage.model]['total_tokens'] += usage.total_tokens
            model_stats[usage.model]['total_cost'] += usage.total_cost

        for model, stats in model_stats.items():
            avg_tokens = stats['total_tokens'] / stats['requests']
            avg_cost = stats['total_cost'] / stats['requests']
            table.add_row(
                model,
                f"{stats['requests']}",
                f"{avg_tokens:.0f}",
                f"${avg_cost:.6f}"
            )

        console.print(table)
        console.print(f"\n[bold]Session Total: ${session.total_cost:.6f}[/bold]")

        # Show cost breakdown
        if session.total_tokens > 0:
            avg_cost_per_1k = (session.total_cost / session.total_tokens) * 1000
            console.print(f"Average cost per 1K tokens: ${avg_cost_per_1k:.6f}")

    async def _iterations_command(self, args: List[str]) -> None:
        """Toggle iteration display or show current setting."""
        if hasattr(self.repl, 'agent_interface') and hasattr(self.repl.agent_interface, 'hide_iterations'):
            current = self.repl.agent_interface.hide_iterations

            if args and args[0].lower() in ['on', 'show', 'true']:
                self.repl.agent_interface.hide_iterations = False
                console.print("[green]Thinking process display enabled[/green]")
            elif args and args[0].lower() in ['off', 'hide', 'false']:
                self.repl.agent_interface.hide_iterations = True
                console.print("[yellow]Thinking process display disabled[/yellow]")
            else:
                # Toggle
                self.repl.agent_interface.hide_iterations = not current
                status = "disabled" if self.repl.agent_interface.hide_iterations else "enabled"
                console.print(f"[cyan]Thinking process display is {status}[/cyan]")
        else:
            console.print("[red]Unable to control thinking process display[/red]")

    async def _local_models_command(self, args: List[str]) -> None:
        """Show local model servers and available models."""
        console.print("[bold cyan]🏠 Discovering Local Models...[/bold cyan]\n")

        try:
            # Discover models from local servers
            discovered = await local_model_manager.discover_models()

            # Show server status table
            local_model_manager.show_local_models_table()

            # Show summary
            summary = local_model_manager.get_server_status_summary()
            console.print(f"\n{summary}")

            # Show usage examples if models found
            active_models = []
            for server_models in discovered.values():
                active_models.extend(server_models)

            if active_models:
                console.print(f"\n[bold]💡 Usage Examples:[/bold]")
                for model in active_models[:3]:  # Show first 3 models
                    console.print(f"  [cyan]/model {model}[/cyan]")
                if len(active_models) > 3:
                    console.print(f"  ... and {len(active_models) - 3} more models")
            else:
                console.print("\n[yellow]No local models found. Use [cyan]/ollama[/cyan] or [cyan]/llamacpp[/cyan] for setup instructions.[/yellow]")

        except Exception as e:
            console.print(f"[red]Error discovering local models: {e}[/red]")

    async def _ollama_command(self, args: List[str]) -> None:
        """Show Ollama information and setup instructions."""
        if args and args[0] == "setup":
            # Show setup instructions
            OllamaHelper.show_setup_instructions()
        else:
            # Show available Ollama models and quick setup
            console.print("[bold cyan]🦙 Ollama Integration[/bold cyan]\n")

            try:
                # Try to discover Ollama models
                discovered = await local_model_manager.discover_models()
                ollama_models = discovered.get("ollama", [])

                if ollama_models:
                    console.print(f"[green]✓[/green] Ollama server found with [cyan]{len(ollama_models)}[/cyan] models:")
                    for model in ollama_models:
                        console.print(f"  • [cyan]{model}[/cyan]")

                    console.print(f"\n[bold]Quick start:[/bold]")
                    console.print(f"  [cyan]/model {ollama_models[0]}[/cyan]")
                else:
                    console.print("[yellow]⚠[/yellow] Ollama server not found or no models installed")
                    console.print("\n[bold]Recommended models for coding:[/bold]")
                    for model in OllamaHelper.get_recommended_coding_models():
                        console.print(f"  ollama pull [cyan]{model}[/cyan]")

            except Exception as e:
                console.print(f"[red]Error checking Ollama: {e}[/red]")

            console.print(f"\n[dim]Use [cyan]/ollama setup[/cyan] for detailed setup instructions.[/dim]")

    async def _llamacpp_command(self, args: List[str]) -> None:
        """Show llama.cpp information and setup instructions."""
        console.print("[bold cyan]🦙 llama.cpp Integration[/bold cyan]\n")

        try:
            # Try to discover llama.cpp models
            discovered = await local_model_manager.discover_models()
            llamacpp_models = discovered.get("llama.cpp", [])

            if llamacpp_models:
                console.print(f"[green]✓[/green] llama.cpp server found with [cyan]{len(llamacpp_models)}[/cyan] models:")
                for model in llamacpp_models:
                    console.print(f"  • [cyan]{model}[/cyan]")

                console.print(f"\n[bold]Quick start:[/bold]")
                console.print(f"  [cyan]/model llama-cpp[/cyan]")
            else:
                console.print("[yellow]⚠[/yellow] llama.cpp server not found (http://localhost:8080)")
                LlamaCppHelper.show_setup_instructions()

        except Exception as e:
            console.print(f"[red]Error checking llama.cpp: {e}[/red]")

    async def _debug_command(self, args: List[str]) -> None:
        """Debug command for troubleshooting model and API issues."""
        console.print("[bold cyan]🔧 DevMind Debug Information[/bold cyan]\n")

        try:
            # Get current model info
            current_model = getattr(self.repl.agent_interface.agent, 'llm', None)
            if current_model and hasattr(current_model, 'config'):
                model_name = current_model.config.model
                console.print(f"[bold]Current Model:[/bold] {model_name}")

                # Check if it's a Deepseek model and provide specific diagnostics
                if "deepseek" in model_name.lower():
                    console.print(f"[yellow]⚠ Deepseek model detected[/yellow]")

                    # Get Deepseek diagnostics if available
                    if hasattr(current_model, 'diagnose_deepseek_issues'):
                        diagnosis = current_model.diagnose_deepseek_issues()

                        if diagnosis["issues"]:
                            console.print("\n[red]🐛 Issues Found:[/red]")
                            for issue in diagnosis["issues"]:
                                console.print(f"  • {issue}")

                        if diagnosis["suggestions"]:
                            console.print("\n[green]💡 Suggestions:[/green]")
                            for suggestion in diagnosis["suggestions"]:
                                console.print(f"  • {suggestion}")

                        console.print("\n[blue]🔄 Alternative Models:[/blue]")
                        alternatives = [
                            "gpt-3.5-turbo (OpenAI - fast and reliable)",
                            "claude-3-haiku-20240307 (Anthropic - fast)",
                            "claude-3-sonnet-20240229 (Anthropic - balanced)"
                        ]
                        for alt in alternatives:
                            console.print(f"  • {alt}")

                        console.print(f"\n[dim]Use: /model <model_name> to switch[/dim]")

                else:
                    console.print(f"[green]✓ Non-Deepseek model in use[/green]")

            else:
                console.print("[red]Unable to detect current model[/red]")

            # General troubleshooting
            console.print(f"\n[bold]General Troubleshooting:[/bold]")
            console.print("• Check your internet connection")
            console.print("• Verify API keys are set correctly")
            console.print("• Try `/local` to see local models (Ollama/llama.cpp)")
            console.print("• Use `/model list` to see available models")
            console.print("• Report issues at: https://github.com/anthropics/claude-code/issues")

        except Exception as e:
            console.print(f"[red]Debug error: {e}[/red]")

    async def _exit_command(self, args: List[str]) -> None:
        """Exit command."""
        console.print("[yellow]Goodbye![/yellow]")
        self.repl.running = False