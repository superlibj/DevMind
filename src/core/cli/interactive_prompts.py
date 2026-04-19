"""
Interactive Prompts for DevMind CLI.

Provides user-friendly interactive prompts, confirmations, and input collection.
"""
import sys
from enum import Enum
from typing import List, Optional, Dict, Any, Union

from .output_formatter import get_output_formatter, OutputStyle


class PromptType(Enum):
    """Types of interactive prompts."""
    TEXT = "text"
    PASSWORD = "password"
    CONFIRM = "confirm"
    CHOICE = "choice"
    MULTISELECT = "multiselect"
    NUMBER = "number"


class InteractivePrompter:
    """Interactive prompt system for user input."""

    def __init__(self):
        """Initialize interactive prompter."""
        self.formatter = get_output_formatter()

    def prompt_text(
        self,
        message: str,
        default: Optional[str] = None,
        required: bool = False,
        validate: Optional[callable] = None
    ) -> Optional[str]:
        """Prompt for text input.

        Args:
            message: Prompt message
            default: Default value
            required: Whether input is required
            validate: Validation function

        Returns:
            User input or None if cancelled
        """
        while True:
            # Format prompt
            prompt_text = self.formatter.style(message, OutputStyle.INFO)
            if default:
                prompt_text += f" [{default}]"
            prompt_text += ": "

            try:
                user_input = input(prompt_text).strip()

                # Use default if no input
                if not user_input and default:
                    user_input = default

                # Check required
                if required and not user_input:
                    self.formatter.print_error("This field is required.")
                    continue

                # Validate input
                if validate and user_input:
                    try:
                        validation_result = validate(user_input)
                        if validation_result is not True:
                            error_msg = validation_result if isinstance(validation_result, str) else "Invalid input."
                            self.formatter.print_error(error_msg)
                            continue
                    except Exception as e:
                        self.formatter.print_error(f"Validation error: {e}")
                        continue

                return user_input if user_input else None

            except (KeyboardInterrupt, EOFError):
                self.formatter.print_warning("\nCancelled by user.")
                return None

    def prompt_password(
        self,
        message: str,
        required: bool = True
    ) -> Optional[str]:
        """Prompt for password input.

        Args:
            message: Prompt message
            required: Whether input is required

        Returns:
            User input or None if cancelled
        """
        import getpass

        while True:
            prompt_text = self.formatter.style(message, OutputStyle.INFO) + ": "

            try:
                user_input = getpass.getpass(prompt_text)

                if required and not user_input:
                    self.formatter.print_error("Password is required.")
                    continue

                return user_input

            except (KeyboardInterrupt, EOFError):
                self.formatter.print_warning("\nCancelled by user.")
                return None

    def prompt_confirm(
        self,
        message: str,
        default: Optional[bool] = None
    ) -> Optional[bool]:
        """Prompt for yes/no confirmation.

        Args:
            message: Prompt message
            default: Default value (True for yes, False for no)

        Returns:
            User choice or None if cancelled
        """
        while True:
            # Format prompt with default
            if default is True:
                choices = "[Y/n]"
            elif default is False:
                choices = "[y/N]"
            else:
                choices = "[y/n]"

            prompt_text = f"{self.formatter.style(message, OutputStyle.INFO)} {choices}: "

            try:
                user_input = input(prompt_text).strip().lower()

                if not user_input and default is not None:
                    return default

                if user_input in ['y', 'yes', 'true', '1']:
                    return True
                elif user_input in ['n', 'no', 'false', '0']:
                    return False
                else:
                    self.formatter.print_error("Please enter 'y' for yes or 'n' for no.")
                    continue

            except (KeyboardInterrupt, EOFError):
                self.formatter.print_warning("\nCancelled by user.")
                return None

    def prompt_choice(
        self,
        message: str,
        choices: List[str],
        default: Optional[str] = None,
        show_numbers: bool = True
    ) -> Optional[str]:
        """Prompt for choice selection.

        Args:
            message: Prompt message
            choices: Available choices
            default: Default choice
            show_numbers: Whether to show numbers for choices

        Returns:
            Selected choice or None if cancelled
        """
        if not choices:
            return None

        while True:
            # Display choices
            self.formatter.print(self.formatter.style(message, OutputStyle.INFO))
            for i, choice in enumerate(choices, 1):
                if show_numbers:
                    choice_text = f"{i}. {choice}"
                else:
                    choice_text = f"  • {choice}"

                if choice == default:
                    choice_text += " (default)"

                self.formatter.print(choice_text)

            # Prompt for selection
            if show_numbers:
                prompt_text = "Enter choice number"
            else:
                prompt_text = "Enter choice"

            if default:
                prompt_text += f" [{default}]"

            prompt_text += ": "

            try:
                user_input = input(prompt_text).strip()

                if not user_input and default:
                    return default

                # Handle numeric input
                if show_numbers and user_input.isdigit():
                    choice_index = int(user_input) - 1
                    if 0 <= choice_index < len(choices):
                        return choices[choice_index]
                    else:
                        self.formatter.print_error(f"Please enter a number between 1 and {len(choices)}.")
                        continue

                # Handle text input
                # Exact match
                if user_input in choices:
                    return user_input

                # Partial match
                matches = [choice for choice in choices if choice.lower().startswith(user_input.lower())]
                if len(matches) == 1:
                    return matches[0]
                elif len(matches) > 1:
                    self.formatter.print_error(f"Ambiguous choice. Matches: {', '.join(matches)}")
                    continue
                else:
                    self.formatter.print_error(f"Invalid choice. Available: {', '.join(choices)}")
                    continue

            except (KeyboardInterrupt, EOFError):
                self.formatter.print_warning("\nCancelled by user.")
                return None

    def prompt_multiselect(
        self,
        message: str,
        choices: List[str],
        defaults: Optional[List[str]] = None
    ) -> Optional[List[str]]:
        """Prompt for multiple choice selection.

        Args:
            message: Prompt message
            choices: Available choices
            defaults: Default selections

        Returns:
            List of selected choices or None if cancelled
        """
        if not choices:
            return []

        defaults = defaults or []
        selected = set(defaults)

        while True:
            # Display current selections
            self.formatter.print(self.formatter.style(message, OutputStyle.INFO))
            self.formatter.print("Current selections:")

            for i, choice in enumerate(choices, 1):
                if choice in selected:
                    status = self.formatter.style("✓", OutputStyle.SUCCESS)
                else:
                    status = " "
                self.formatter.print(f"{status} {i}. {choice}")

            self.formatter.print("\nEnter choice numbers to toggle (space-separated), or 'done' to finish:")

            try:
                user_input = input("> ").strip().lower()

                if user_input in ['done', 'finish', 'ok', '']:
                    return list(selected)

                if user_input in ['clear', 'none']:
                    selected.clear()
                    continue

                if user_input in ['all']:
                    selected.update(choices)
                    continue

                # Parse numbers
                try:
                    numbers = [int(x.strip()) for x in user_input.split() if x.strip().isdigit()]
                    for num in numbers:
                        if 1 <= num <= len(choices):
                            choice = choices[num - 1]
                            if choice in selected:
                                selected.remove(choice)
                            else:
                                selected.add(choice)
                        else:
                            self.formatter.print_error(f"Invalid choice number: {num}")
                            break
                except ValueError:
                    self.formatter.print_error("Please enter valid numbers or 'done'.")
                    continue

            except (KeyboardInterrupt, EOFError):
                self.formatter.print_warning("\nCancelled by user.")
                return None

    def prompt_number(
        self,
        message: str,
        default: Optional[Union[int, float]] = None,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        integer_only: bool = False
    ) -> Optional[Union[int, float]]:
        """Prompt for numeric input.

        Args:
            message: Prompt message
            default: Default value
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            integer_only: Whether to accept only integers

        Returns:
            Numeric input or None if cancelled
        """
        while True:
            # Format prompt
            prompt_text = self.formatter.style(message, OutputStyle.INFO)
            if default is not None:
                prompt_text += f" [{default}]"
            prompt_text += ": "

            try:
                user_input = input(prompt_text).strip()

                if not user_input and default is not None:
                    return default

                if not user_input:
                    self.formatter.print_error("Please enter a number.")
                    continue

                # Parse number
                try:
                    if integer_only:
                        value = int(user_input)
                    else:
                        value = float(user_input)
                except ValueError:
                    self.formatter.print_error("Please enter a valid number.")
                    continue

                # Check bounds
                if min_value is not None and value < min_value:
                    self.formatter.print_error(f"Value must be at least {min_value}.")
                    continue

                if max_value is not None and value > max_value:
                    self.formatter.print_error(f"Value must be at most {max_value}.")
                    continue

                return value

            except (KeyboardInterrupt, EOFError):
                self.formatter.print_warning("\nCancelled by user.")
                return None

    def show_progress(
        self,
        message: str,
        steps: List[str],
        current_step: int = 0
    ):
        """Show progress with steps.

        Args:
            message: Progress message
            steps: List of step descriptions
            current_step: Current step index
        """
        self.formatter.print(self.formatter.style(message, OutputStyle.INFO))

        for i, step in enumerate(steps):
            if i < current_step:
                status = self.formatter.style("✓", OutputStyle.SUCCESS)
            elif i == current_step:
                status = self.formatter.style("●", OutputStyle.WARNING)
            else:
                status = self.formatter.style("○", OutputStyle.MUTED)

            self.formatter.print(f"{status} {step}")

    def show_spinner(self, message: str, frame: int = 0):
        """Show a spinner with message.

        Args:
            message: Spinner message
            frame: Animation frame
        """
        spinner = self.formatter.spinner(frame)
        self.formatter.print(f"{spinner} {message}", end="\r")
        sys.stdout.flush()

    def clear_line(self):
        """Clear the current line."""
        print("\r" + " " * self.formatter.get_terminal_width(), end="\r")
        sys.stdout.flush()

    def prompt_with_suggestions(
        self,
        message: str,
        suggestions: List[str],
        default: Optional[str] = None
    ) -> Optional[str]:
        """Prompt with auto-completion suggestions.

        Args:
            message: Prompt message
            suggestions: Available suggestions
            default: Default value

        Returns:
            User input or None if cancelled
        """
        # For now, show suggestions and use regular text prompt
        # In a full implementation, this would use readline for completion
        if suggestions:
            self.formatter.print(self.formatter.style("Available options:", OutputStyle.MUTED))
            suggestion_text = ", ".join(suggestions[:10])
            if len(suggestions) > 10:
                suggestion_text += f" (and {len(suggestions) - 10} more)"
            self.formatter.print(self.formatter.style(suggestion_text, OutputStyle.MUTED))

        return self.prompt_text(message, default=default)


# Global interactive prompter instance
_interactive_prompter = None


def get_interactive_prompter() -> InteractivePrompter:
    """Get the global interactive prompter instance."""
    global _interactive_prompter
    if _interactive_prompter is None:
        _interactive_prompter = InteractivePrompter()
    return _interactive_prompter