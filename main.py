#!/usr/bin/env python3
"""
DevMind Interactive Development Assistant - Main CLI Entry Point

A DevMind interactive development assistant that works as a CLI tool
directly integrated with the development environment.

Usage:
    devmind                        # Start interactive REPL
    devmind --model <model>        # Start with specific model
    devmind --session <name>       # Load/create named session
    devmind --help                # Show help
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.cli.repl import DevMindREPL
from src.cli.session_manager import SessionManager
from src.core.llm.model_config import model_config_manager, ProviderType
from config.settings import settings

console = Console()
app = typer.Typer(
    name="devmind",
    help="DevMind Interactive Development Assistant",
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=False
)


def print_banner():
    """Print the DevMind banner."""
    banner = r"""
    ____              __  __ _           _
   |  _ \  _____   ____|  \/  (_)_ __   __| |
   | | | |/ _ \ \ / / _` |\/| | | '_ \ / _` |
   | |_| |  __/\ V / (_| |  | | | | | | (_| |
   |____/ \___| \_/ \__,_|  |_|_|_| |_|\__,_|

         Interactive Development Assistant
    """
    console.print(Panel(
        Text(banner, style="bright_cyan"),
        title="[bold blue]Welcome to DevMind[/bold blue]",
        border_style="bright_blue"
    ))


def list_available_models():
    """List all available models grouped by provider."""
    console.print("\n[bold]Available Models:[/bold]\n")

    providers = {}
    for provider in ProviderType:
        models = model_config_manager.list_models(provider=provider)
        if models:
            providers[provider] = models

    for provider, models in providers.items():
        console.print(f"[bold bright_blue]{provider.value.upper()}:[/bold bright_blue]")
        for model in models:
            capabilities = ", ".join([cap.value for cap in model.capabilities])
            cost_info = ""
            if model.cost_per_1k_input:
                cost_info = f" (${model.cost_per_1k_input:.4f}/1k tokens)"

            console.print(f"  • [cyan]{model.name}[/cyan]{cost_info}")
            console.print(f"    {model.description}")
            if model.supports_tools:
                console.print("    [green]✓[/green] Supports tools")
            if model.supports_streaming:
                console.print("    [green]✓[/green] Supports streaming")
            console.print(f"    [dim]Capabilities: {capabilities}[/dim]\n")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        help="LLM model to use (e.g., 'deepseek-chat', 'gpt-4', 'claude-3-sonnet')"
    ),
    session: Optional[str] = typer.Option(
        None,
        "--session", "-s",
        help="Session name to load or create"
    ),
    list_models: bool = typer.Option(
        False,
        "--list-models", "-l",
        help="List all available models and exit"
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider", "-p",
        help="Filter models by provider (openai, anthropic, deepseek, etc.)"
    ),
    temperature: Optional[float] = typer.Option(
        None,
        "--temperature", "-t",
        help="Temperature for model responses (0.0-1.0)"
    ),
    max_tokens: Optional[int] = typer.Option(
        None,
        "--max-tokens",
        help="Maximum tokens in model response"
    ),
    timeout: int = typer.Option(
        60,
        "--timeout",
        help="Timeout in seconds for API requests (default: 60)"
    ),
    max_iterations: int = typer.Option(
        100,
        "--max-iterations",
        help="Maximum number of agent iterations for complex tasks (default: 100)"
    ),
    hide_iterations: bool = typer.Option(
        False,
        "--hide-iterations",
        help="Hide iteration progress for cleaner output"
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug logging"
    )
):
    """
    Start the DevMind interactive development assistant.

    This creates a DevMind experience in your terminal with:
    - Streaming conversational responses
    - Real-time tool execution with progress indicators
    - Session persistence across CLI restarts
    - Multi-model support including DeepSeek
    - Direct filesystem and git integration
    """
    # If a subcommand was invoked, don't run the main logic
    if ctx.invoked_subcommand is not None:
        return

    if list_models:
        if provider:
            try:
                provider_type = ProviderType(provider.lower())
                models = model_config_manager.list_models(provider=provider_type)
                console.print(f"\n[bold]{provider.upper()} Models:[/bold]\n")
                for model in models:
                    console.print(f"• [cyan]{model.name}[/cyan] - {model.description}")
            except ValueError:
                console.print(f"[red]Unknown provider: {provider}[/red]")
                console.print("Available providers: " + ", ".join([p.value for p in ProviderType]))
                raise typer.Exit(1)
        else:
            list_available_models()
        raise typer.Exit(0)

    # Validate model if provided
    if model:
        model_info = model_config_manager.get_model_info(model)
        if not model_info:
            console.print(f"[red]Model '{model}' not found.[/red]")
            console.print("\nUse --list-models to see available models.")
            raise typer.Exit(1)

    # Show banner
    print_banner()

    # Initialize session manager
    session_manager = SessionManager()

    # Start the interactive REPL
    try:
        asyncio.run(start_interactive_session(
            model=model,
            session_name=session,
            session_manager=session_manager,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_iterations=max_iterations,
            hide_iterations=hide_iterations,
            debug=debug
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        if debug:
            console.print_exception()
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


async def start_interactive_session(
    model: Optional[str] = None,
    session_name: Optional[str] = None,
    session_manager: SessionManager = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: int = 60,
    max_iterations: int = 100,
    hide_iterations: bool = False,
    debug: bool = False
):
    """Start the interactive REPL session."""

    # Set debug logging
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # Initialize REPL
    repl = DevMindREPL(
        model=model,
        session_manager=session_manager,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_iterations=max_iterations,
        hide_iterations=hide_iterations
    )

    # Load session if specified
    if session_name:
        await repl.load_session(session_name)
        console.print(f"[green]Loaded session: {session_name}[/green]\n")

    # Start the REPL
    await repl.run()


@app.command("version")
def version():
    """Show version information."""
    console.print(f"DevMind Interactive Development Assistant v{settings.app.version}")
    console.print("Built with ♥ using Rich, Typer, and LiteLLM")


@app.command("config")
def config_cmd():
    """Show current configuration."""
    console.print("[bold]Current Configuration:[/bold]\n")

    console.print(f"Default Provider: [cyan]{settings.llm.default_provider}[/cyan]")
    console.print(f"Default Model: [cyan]{getattr(settings.llm, f'{settings.llm.default_provider}_model')}[/cyan]")
    console.print(f"Max Tokens: [cyan]{settings.llm.max_tokens}[/cyan]")
    console.print(f"Temperature: [cyan]{settings.llm.temperature}[/cyan]")
    console.print(f"Timeout: [cyan]{settings.llm.timeout_seconds}s[/cyan]")

    # Check API keys
    console.print("\n[bold]API Keys Status:[/bold]")
    providers = {
        "OpenAI": settings.llm.openai_api_key,
        "Anthropic": settings.llm.anthropic_api_key,
        "DeepSeek": settings.llm.deepseek_api_key,
    }

    for provider, key in providers.items():
        if key:
            console.print(f"  {provider}: [green]✓ Configured[/green]")
        else:
            console.print(f"  {provider}: [red]✗ Not configured[/red]")


if __name__ == "__main__":
    app()