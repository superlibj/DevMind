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

# Enhanced input handling with auto-completion
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import radiolist_dialog, checkboxlist_dialog, yes_no_dialog
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
import re

from ..core.agent.react_agent import ReActAgent
from ..core.llm import create_llm
from ..core.tools import initialize_acp_integration
from .session_manager import SessionManager
from .command_parser import CommandParser
from .output_formatter import OutputFormatter
from .streaming_agent import StreamingReActAgent, CLIAgentInterface
from .completion import create_completer, DevMindCommandSelector

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
        max_iterations: int = 8,
        hide_iterations: bool = False
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
        # Initialize ACP tool integration (including location and weather tools)
        try:
            initialize_acp_integration()
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to initialize ACP tools: {e}[/yellow]")

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
        self.agent_interface = CLIAgentInterface(self.streaming_agent, hide_iterations=hide_iterations)

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

        # Set up enhanced input handling with auto-completion
        self.completer = create_completer(self)
        self.command_selector = DevMindCommandSelector(self.completer)
        self.history = InMemoryHistory()

        # Create prompt session with completion
        self.prompt_session = PromptSession(
            completer=self.completer,
            complete_style=CompleteStyle.MULTI_COLUMN,
            history=self.history,
            key_bindings=self._create_key_bindings()
        )

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings for enhanced input."""
        kb = KeyBindings()

        @kb.add('c-c')
        def _(event):
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
            event.app.exit()

        @kb.add('/')
        def _(event):
            """Show command selector when '/' is typed."""
            # Insert the '/' character first
            event.current_buffer.insert_text('/')

            # If this is the only character, show command help
            if len(event.current_buffer.text.strip()) == 1:
                self._show_command_help_inline()

        return kb

    def _show_command_help_inline(self):
        """Show brief command help inline."""
        console.print("\n[dim]💡 Available commands (press [b]Tab[/b] for completion):[/dim]")

        # Show commands in columns for better display
        commands = list(self.command_selector.completer.commands.items())

        # Display in 2 columns with better formatting
        for i in range(0, len(commands), 2):
            line = ""
            for j in range(2):
                if i + j < len(commands):
                    cmd, desc = commands[i + j]
                    # Truncate long descriptions
                    short_desc = desc[:28] + "..." if len(desc) > 28 else desc
                    line += f"[cyan]/{cmd:<12}[/cyan][dim]{short_desc:<32}[/dim]"
            console.print(line.rstrip())

        console.print("[dim]Press [b]Tab[/b] after typing command name for auto-completion[/dim]")

    def _detect_options_in_text(self, text: str) -> List[tuple]:
        """Detect option lists in agent response text.

        Args:
            text: Response text to analyze

        Returns:
            List of (option_value, option_label) tuples, or empty list if no options found
        """
        options = []

        # Pattern 1: Numbered options (1. Option A, 2. Option B, etc.)
        numbered_pattern = r'^\s*(\d+)[.)]\s*(.+)$'
        numbered_matches = re.findall(numbered_pattern, text, re.MULTILINE)

        if numbered_matches and len(numbered_matches) >= 2:
            for num, label in numbered_matches:
                clean_label = label.strip()
                # Remove checkbox notation if present ([ ], [x], [X], or [✓])
                clean_label = re.sub(r'^\[\s*[xX✓\s]*\]\s*', '', clean_label)
                options.append((num, f"{num}. {clean_label}"))
            return options

        # Pattern 2: Lettered options (A. Option A, B. Option B, etc.)
        lettered_pattern = r'^\s*([A-Za-z])[.)]\s*(.+)$'
        lettered_matches = re.findall(lettered_pattern, text, re.MULTILINE)

        if lettered_matches and len(lettered_matches) >= 2:
            for letter, label in lettered_matches:
                clean_label = label.strip()
                # Remove checkbox notation if present ([ ], [x], [X], or [✓])
                clean_label = re.sub(r'^\[\s*[xX✓\s]*\]\s*', '', clean_label)
                options.append((letter.lower(), f"{letter.upper()}. {clean_label}"))
            return options

        # Pattern 3: Bullet points with clear options (including checkbox format)
        bullet_pattern = r'^\s*[•\-\*]\s*(.+)$'
        bullet_matches = re.findall(bullet_pattern, text, re.MULTILINE)

        if bullet_matches and len(bullet_matches) >= 2:
            for i, label in enumerate(bullet_matches, 1):
                clean_label = label.strip()

                # Remove checkbox notation if present ([ ] or [x])
                clean_label = re.sub(r'^\[\s*[x\s]*\]\s*', '', clean_label)

                if len(clean_label) > 5 and len(clean_label) < 100:  # Reasonable option length
                    options.append((str(i), f"{i}. {clean_label}"))
            return options if len(options) >= 2 else []

        # Pattern 4: Options with keywords (choose from, select, pick one of)
        choice_keywords = [
            r'choose\s+(?:from|one\s+of)\s*:?\s*(.+)',
            r'select\s+(?:from|one\s+of)\s*:?\s*(.+)',
            r'pick\s+(?:from|one\s+of)\s*:?\s*(.+)',
            r'options?\s*:?\s*(.+)'
        ]

        for pattern in choice_keywords:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                choice_text = matches[0]
                # Look for comma-separated options
                comma_options = [opt.strip() for opt in choice_text.split(',')]
                if len(comma_options) >= 2:
                    for i, opt in enumerate(comma_options, 1):
                        if len(opt.strip()) > 2:
                            options.append((str(i), f"{i}. {opt.strip()}"))
                    if options:
                        return options

        return []

    def _should_use_multiselect(self, text: str, options: List[tuple]) -> bool:
        """Detect if multiselect mode should be used based on context.

        Args:
            text: Response text to analyze
            options: Detected options list

        Returns:
            True if multiselect should be used, False for single select
        """
        text_lower = text.lower()

        # Check recent conversation history for multiselect indicators
        try:
            history = self.streaming_agent.get_conversation_history()
            # Check last few user messages for multiselect requests
            recent_user_messages = [
                msg.get("content", "").lower()
                for msg in history[-5:]
                if msg.get("role") == "user"
            ]

            # If user explicitly requested multiselect in recent messages
            for msg_content in recent_user_messages:
                if any(keyword in msg_content for keyword in ['multiselect', 'multi-select', 'multi select', 'multiple', 'several']):
                    return True
        except Exception:
            # If we can't access history, fall back to response analysis
            pass

        # Explicit multiselect indicators
        multiselect_keywords = [
            'select multiple', 'choose multiple', 'pick multiple', 'select all that apply',
            'choose all that apply', 'pick all that apply', 'select several', 'choose several',
            'which ones', 'what features', 'what requirements', 'which features',
            'which requirements', 'multiple', 'several', 'all that apply', 'multiselect',
            'multi-select', 'multi select'
        ]

        for keyword in multiselect_keywords:
            if keyword in text_lower:
                return True

        # Context-based detection for feature/requirement lists
        feature_context = [
            'features', 'requirements', 'capabilities', 'functionalities',
            'options', 'components', 'modules', 'tools', 'plugins'
        ]

        for context in feature_context:
            if context in text_lower and len(options) > 3:
                # If it's a feature list and has many options, likely multiselect
                return True

        # Question patterns that suggest multiselect
        multiselect_patterns = [
            r'what.*(?:features|requirements|options).*(?:do you|would you).*(?:need|want|like)',
            r'which.*(?:features|requirements|options).*(?:are|would be).*important',
            r'select.*(?:features|requirements|options).*(?:that|you)',
            r'choose.*(?:features|requirements|options).*(?:that|you)'
        ]

        for pattern in multiselect_patterns:
            if re.search(pattern, text_lower):
                return True

        # Special case: Large feature lists with categories suggest multiselect
        if len(options) >= 5 and any(
            indicator in text_lower
            for indicator in ['features', 'functions', 'capabilities', 'components', 'options']
        ):
            return True

        # Special case: When response contains structured feature lists
        if ('•' in text or '[ ]' in text) and len(options) >= 4:
            # Response contains checkboxes or bullet points with many options
            return True

        # Default to single select for simple choice questions
        return False

    async def _show_interactive_options(
        self,
        options: List[tuple],
        title: str = "Select an option",
        multiselect: bool = False
    ) -> Optional[str]:
        """Show interactive option selector with single or multi-selection.

        Args:
            options: List of (value, display_text) tuples
            title: Title for the selection dialog
            multiselect: Whether to allow multiple selections

        Returns:
            Selected option value(s) or None if cancelled.
            For single select: returns string value (e.g., "1")
            For multiselect: returns comma-separated values (e.g., "1,3,5")
        """
        if not options:
            return None

        try:
            # Create custom style for better visibility
            option_style = Style.from_dict({
                'dialog':             'bg:#4444aa',
                'dialog.body':        'bg:#ffffff #000000',
                'dialog.shadow':      'bg:#003366',
                'dialog frame.label': 'bg:#ffffff #000000 bold',
                'radiolist':          'bg:#ffffff',
                'radiolist focused':  'bg:#ffaa00 #000000 bold',
                'radiolist selected': 'bg:#00aa00 #ffffff bold',
                'checkbox-list':      'bg:#ffffff',
                'checkbox-list focused': 'bg:#ffaa00 #000000 bold',
                'checkbox-list selected': 'bg:#00aa00 #ffffff bold',
            })

            # Display appropriate instructions based on selection mode
            if multiselect:
                console.print(f"\n[cyan]🎯 {title} (Multi-Select)[/cyan]")
                console.print("[dim]Use ↑↓ arrows to navigate, [bold]Space[/bold] to toggle selection, [bold]Enter[/bold] to confirm[/dim]")
                console.print("[dim][yellow]Tip: You can select multiple options[/yellow][/dim]")

                # Show the checkboxlist dialog for multiselect
                app = checkboxlist_dialog(
                    title=title,
                    text="Use arrow keys to navigate and spacebar to toggle multiple selections:",
                    values=options,
                    style=option_style
                )
            else:
                console.print(f"\n[cyan]🎯 {title} (Single-Select)[/cyan]")
                console.print("[dim]Use ↑↓ arrows to navigate, [bold]Space[/bold] to select, [bold]Enter[/bold] to confirm[/dim]")

                # Show the radiolist dialog for single select
                app = radiolist_dialog(
                    title=title,
                    text="Use arrow keys to navigate and spacebar to select:",
                    values=options,
                    style=option_style
                )

            # Execute the application async to get the actual result
            result = await app.run_async()

            if result:
                if multiselect:
                    # For multiselect, result is a list of selected values
                    if isinstance(result, list) and result:
                        selected_values = [str(item) for item in result]
                        selected_text = ", ".join(selected_values)
                        console.print(f"[green]✅ Selected: {selected_text}[/green]")
                        return ",".join(selected_values)  # Return comma-separated values
                    else:
                        console.print(f"[yellow]❌ No items selected[/yellow]")
                        return None
                else:
                    # For single select, result is a single value
                    console.print(f"[green]✅ Selected: {result}[/green]")
                    return str(result)
            else:
                console.print(f"[yellow]❌ Selection cancelled[/yellow]")
                return None

        except Exception as e:
            console.print(f"[red]Error in option selector: {e}[/red]")
            # Fallback to text input
            return None

    async def _handle_agent_response_with_options(self, response: str) -> Optional[str]:
        """Process agent response and handle interactive options if detected.

        Args:
            response: Agent response text

        Returns:
            User's selection if options were detected, None otherwise
        """
        # Check if the response contains options
        options = self._detect_options_in_text(response)

        if not options:
            return None

        # Only show interactive selection if user explicitly requested it
        user_requested_interactive = False
        try:
            history = self.streaming_agent.get_conversation_history()
            # Check last 2-3 user messages for explicit interactive requests
            recent_user_messages = [
                msg.get("content", "").lower()
                for msg in history[-3:]
                if msg.get("role") == "user"
            ]

            # Keywords that indicate user wants interactive selection
            interactive_keywords = [
                'interactive', 'multiselect', 'multi-select', 'multi select',
                'select multiple', 'choose multiple', 'interactive selection',
                'space to select', 'spacebar'
            ]

            for msg_content in recent_user_messages:
                if any(keyword in msg_content for keyword in interactive_keywords):
                    user_requested_interactive = True
                    break

        except Exception:
            # If we can't access history, default to not showing interactive
            user_requested_interactive = False

        # If user didn't explicitly request interactive selection, don't show it
        if not user_requested_interactive:
            return None

        # Detect if multiselect should be used
        is_multiselect = self._should_use_multiselect(response, options)
        selection_type = "Multi-Select" if is_multiselect else "Single-Select"

        # Ask user if they want interactive selection
        console.print(f"\n[yellow]🔍 Detected {len(options)} options in response.[/yellow]")
        console.print(f"[dim]Selection mode: [bold]{selection_type}[/bold][/dim]")
        console.print("[dim]Options found:[/dim]")
        for value, label in options[:3]:  # Show first 3 as preview
            console.print(f"  [cyan]{label}[/cyan]")
        if len(options) > 3:
            console.print(f"  [dim]... and {len(options) - 3} more[/dim]")

        # Ask if they want interactive selection
        selection_prompt = (
            "Would you like to use interactive selection?\n"
            f"Mode: {selection_type}\n"
            "Controls: ↑↓ arrows to navigate, Space to select/toggle, Enter to confirm"
        )

        dialog_app = yes_no_dialog(
            title="Interactive Selection",
            text=selection_prompt
        )
        use_interactive = await dialog_app.run_async()

        if use_interactive:
            if is_multiselect:
                title = "Choose Multiple Options"
                return await self._show_interactive_options(options, title, multiselect=True)
            else:
                title = "Choose One Option"
                return await self._show_interactive_options(options, title, multiselect=False)

        return None

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

[bold]Enhanced Input Features:[/bold]
• [green]🔥 Tab completion[/green] - Press [cyan]Tab[/cyan] for command/file completion
• [green]📋 Command suggestions[/green] - Type [cyan]/[/cyan] to see available commands
• [green]⬆️ History navigation[/green] - Use [cyan]↑↓[/cyan] arrows for command history
• [green]🎯 Interactive selection[/green] - Single/multi-select with [cyan]Spacebar[/cyan] when DevMind presents choices

[bold]Special Commands:[/bold]
• [cyan]/help[/cyan] - Show detailed help
• [cyan]/model[/cyan] - Switch LLM model
• [cyan]/save <name>[/cyan] - Save current session
• [cyan]/load <name>[/cyan] - Load saved session
• [cyan]/sessions[/cyan] - List saved sessions
• [cyan]/tokens[/cyan] - Show token usage & cost
• [cyan]/clear[/cyan] - Clear conversation
• [cyan]/exit[/cyan] - Exit DevMind

[bold]Input Tips:[/bold]
• Use [cyan]```[/cyan] for multi-line code input
• Press [cyan]Tab[/cyan] to complete commands and filenames
• Type [cyan]/[/cyan] and press [cyan]Tab[/cyan] to see all commands
• When DevMind shows options, use [cyan]↑↓ arrows + Spacebar[/cyan] for single/multi-selection
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
        """Get user input with enhanced auto-completion and command suggestions."""

        if self.in_multiline:
            prompt_text = "... "
        else:
            prompt_text = "devmind> "

        try:
            # Use enhanced prompt session with auto-completion
            # Disable completion in multi-line mode for better experience
            use_completion = not self.in_multiline

            if use_completion:
                user_input = await asyncio.to_thread(
                    self.prompt_session.prompt,
                    f"{prompt_text}",
                    complete_style=CompleteStyle.MULTI_COLUMN
                )
            else:
                # Simple input for multi-line mode
                user_input = await asyncio.to_thread(
                    lambda: input(f"{prompt_text}")
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
        except KeyboardInterrupt:
            console.print("\n[yellow]Input cancelled.[/yellow]")
            return ""

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

            # Check if the agent response contains options for interactive selection
            if response and isinstance(response, str):
                selected_option = await self._handle_agent_response_with_options(response)

                if selected_option:
                    # User made a selection, send it back to the agent
                    console.print(f"\n[cyan]📤 Sending selection to DevMind: {selected_option}[/cyan]")

                    # Process the selection as a follow-up message
                    await self.agent_interface.process_message_with_display(selected_option)

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

        # Show session summary
        try:
            from .token_counter import token_counter
            console.print("\n")
            console.print(token_counter.get_session_summary())
        except Exception:
            pass  # Silently ignore if token counter fails

        console.print("\n[dim]Session ended.[/dim]")