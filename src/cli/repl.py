"""
Interactive REPL for DevMind CLI.

Provides a Rich-powered terminal interface with streaming responses,
command history, completion, and real-time tool execution feedback.
"""
import asyncio
import os
import signal
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.align import Align

from ..core.agent.react_agent import ReActAgent
from ..core.llm import create_llm
from .session_manager import SessionManager
from .command_parser import CommandParser
from .output_formatter import OutputFormatter
from .streaming_agent import StreamingReActAgent, CLIAgentInterface

console = Console()


class DevMindREPL:
    """DevMind Interactive REPL."""

    def __init__(
        self,
        model: Optional[str] = None,
        session_manager: Optional[SessionManager] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: int = 60,
        max_iterations: int = 100
    ):
        """Initialize the REPL.

        Args:
            model: LLM model to use
            session_manager: Session manager instance
            temperature: Model temperature override
            max_tokens: Max tokens override
            timeout: API request timeout in seconds
            max_iterations: Maximum number of agent iterations for complex tasks
        """
        self.session_manager = session_manager or SessionManager()
        self.command_parser = CommandParser(self)
        self.output_formatter = OutputFormatter()

        # Initialize agent with custom LLM if specified
        llm_config = {}
        if temperature is not None:
            llm_config["temperature"] = temperature
        if max_tokens is not None:
            llm_config["max_tokens"] = max_tokens
        llm_config["timeout"] = timeout

        # Determine which model to use
        if model:
            target_model = model
        else:
            # Get recommended model for code tasks
            from ..core.llm.llm_factory import llm_factory
            target_model = llm_factory.get_recommended_model("code")

        self.llm = create_llm(model=target_model, **llm_config)

        # Create ReAct agent and wrap it with streaming capabilities
        react_agent = ReActAgent(llm=self.llm, max_iterations=max_iterations)
        self.streaming_agent = StreamingReActAgent(react_agent, self.output_formatter)
        self.agent_interface = CLIAgentInterface(self.streaming_agent)

        # For compatibility, expose the underlying agent
        self.agent = react_agent

        # Session state
        self.current_session = None
        self.session_name = None
        self.running = False

        # Command history
        self.command_history: List[str] = []
        self.history_index = 0

        # Multi-line input buffer
        self.input_buffer: List[str] = []
        self.in_multiline = False

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C interrupt."""
        if self.in_multiline and self.input_buffer:
            # Clear multi-line input
            self.input_buffer.clear()
            self.in_multiline = False
            console.print("\n[yellow]Multi-line input cleared.[/yellow]")
            return

        # Exit REPL
        console.print("\n[yellow]Goodbye![/yellow]")
        self.running = False

    async def run(self) -> None:
        """Run the interactive REPL."""
        self.running = True

        # Show initial help
        self._show_welcome()

        try:
            while self.running:
                try:
                    user_input = await self._get_user_input()

                    if user_input is None:  # EOF or exit
                        break

                    if user_input.strip() == "":
                        continue

                    # Add to history
                    self.command_history.append(user_input)

                    # Check for special commands
                    if await self._handle_special_commands(user_input):
                        continue

                    # Process with agent
                    await self._process_user_message(user_input)

                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")

        finally:
            await self._cleanup()

    def _show_welcome(self) -> None:
        """Show welcome message and basic commands."""
        welcome_text = """
Welcome to [bold cyan]DevMind[/bold cyan]! 🚀

I'm your interactive development assistant. I can help with:
• Code generation and review
• File operations and git commands
• Debugging and refactoring
• Architecture discussions

[bold]Special Commands:[/bold]
• [cyan]/help[/cyan] - Show detailed help
• [cyan]/model[/cyan] - Switch LLM model
• [cyan]/save <name>[/cyan] - Save current session
• [cyan]/load <name>[/cyan] - Load saved session
• [cyan]/sessions[/cyan] - List saved sessions
• [cyan]/clear[/cyan] - Clear conversation
• [cyan]/exit[/cyan] - Exit DevMind

[bold]Tips:[/bold]
• Use [cyan]```[/cyan] for multi-line code input
• Press [cyan]Ctrl+C[/cyan] to cancel current operation
• Type naturally - I'll understand context from our conversation

Ready to help! What would you like to work on?
        """

        console.print(Panel(
            welcome_text,
            title="[bold blue]DevMind - Interactive Development Assistant[/bold blue]",
            border_style="bright_blue",
            padding=(1, 2)
        ))

    async def _get_user_input(self) -> Optional[str]:
        """Get user input with support for multi-line input."""

        if self.in_multiline:
            prompt_text = "... "
        else:
            prompt_text = "devmind> "

        try:
            # Simple input for now - can enhance with prompt_toolkit later
            user_input = await asyncio.to_thread(
                input,
                f"\n{prompt_text}"
            )

            # Check for multi-line input
            if user_input.strip() == "```" and not self.in_multiline:
                # Start multi-line input
                self.in_multiline = True
                self.input_buffer = []
                console.print("[dim]Multi-line input mode. Type '```' on a new line to finish.[/dim]")
                return await self._get_user_input()

            elif user_input.strip() == "```" and self.in_multiline:
                # End multi-line input
                self.in_multiline = False
                complete_input = "\n".join(self.input_buffer)
                self.input_buffer = []
                return complete_input

            elif self.in_multiline:
                # Add to buffer
                self.input_buffer.append(user_input)
                return await self._get_user_input()

            else:
                return user_input

        except EOFError:
            return None

    async def _handle_special_commands(self, user_input: str) -> bool:
        """Handle special commands.

        Args:
            user_input: User input string

        Returns:
            True if command was handled, False otherwise
        """
        if not user_input.startswith("/"):
            return False

        return await self.command_parser.parse_and_execute(user_input)

    async def _process_user_message(self, message: str) -> None:
        """Process user message with the agent.

        Args:
            message: User message to process
        """
        try:
            # Process with streaming display
            response = await self.agent_interface.process_message_with_display(message)

            # Auto-save session if named
            if self.session_name:
                await self._auto_save_session()

        except Exception as e:
            self.output_formatter.display_error(f"Agent error: {str(e)}")
            console.print_exception() if console.is_terminal else None

    async def _auto_save_session(self) -> None:
        """Auto-save current session."""
        try:
            conversation_data = self.streaming_agent.export_session()
            self.session_manager.save_session(
                self.session_name,
                conversation_data,
                model=self.llm.config.model
            )
        except Exception as e:
            console.print(f"[yellow]Warning: Could not auto-save session: {e}[/yellow]")

    async def load_session(self, session_name: str) -> bool:
        """Load a session.

        Args:
            session_name: Name of session to load

        Returns:
            True if loaded successfully
        """
        session_data = self.session_manager.load_session(session_name)

        if session_data:
            try:
                self.streaming_agent.import_session(session_data)
                self.session_name = session_name
                return True
            except Exception as e:
                console.print(f"[red]Failed to import session: {e}[/red]")

        return False

    async def save_session(self, session_name: str, description: Optional[str] = None) -> bool:
        """Save current session.

        Args:
            session_name: Name for the session
            description: Optional description

        Returns:
            True if saved successfully
        """
        try:
            conversation_data = self.streaming_agent.export_session()

            success = self.session_manager.save_session(
                session_name,
                conversation_data,
                model=self.llm.config.model,
                description=description
            )

            if success:
                self.session_name = session_name

            return success

        except Exception as e:
            console.print(f"[red]Failed to save session: {e}[/red]")
            return False

    def clear_conversation(self) -> None:
        """Clear current conversation."""
        self.streaming_agent.clear_memory()
        self.session_name = None
        console.print("[green]Conversation cleared.[/green]")

    def switch_model(self, model_name: str) -> bool:
        """Switch to a different model.

        Args:
            model_name: Name of model to switch to

        Returns:
            True if switched successfully
        """
        try:
            # Create new LLM instance
            new_llm = create_llm(
                model=model_name,
                temperature=self.llm.config.temperature,
                max_tokens=self.llm.config.max_tokens
            )

            # Update agents
            self.llm = new_llm
            self.agent.llm = new_llm
            self.streaming_agent.agent.llm = new_llm

            console.print(f"[green]Switched to model: {model_name}[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Failed to switch model: {e}[/red]")
            return False

    def get_conversation_summary(self) -> str:
        """Get a summary of the current conversation."""
        history = self.streaming_agent.get_conversation_history()
        if not history:
            return "No conversation history."

        user_messages = [msg for msg in history if msg.get("role") == "user"]
        assistant_messages = [msg for msg in history if msg.get("role") == "assistant"]

        summary = f"Conversation: {len(user_messages)} user messages, {len(assistant_messages)} assistant responses"

        if self.session_name:
            summary += f"\nSession: {self.session_name}"

        summary += f"\nModel: {self.llm.config.model}"

        return summary

    async def _cleanup(self) -> None:
        """Clean up resources."""
        # Auto-save if we have a named session
        if self.session_name:
            await self._auto_save_session()

        console.print("\n[dim]Session ended.[/dim]")