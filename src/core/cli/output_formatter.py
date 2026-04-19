"""
Output Formatter for DevMind Enhanced CLI Experience.

Provides colored output, styled text, tables, and progress indicators.
"""
import shutil
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Union, TextIO


class Color(Enum):
    """ANSI color codes."""
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"


class OutputStyle(Enum):
    """Output style presets."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    HEADER = "header"
    SUBHEADER = "subheader"
    EMPHASIS = "emphasis"
    MUTED = "muted"
    CODE = "code"


@dataclass
class ProgressBar:
    """Progress bar display configuration."""
    total: int
    current: int = 0
    width: int = 40
    prefix: str = ""
    suffix: str = ""
    fill: str = "█"
    empty: str = "░"


class OutputFormatter:
    """Enhanced output formatter with color support and styling."""

    def __init__(self):
        """Initialize output formatter."""
        self.color_enabled = self._supports_color()

        # Style definitions
        self.styles = {
            OutputStyle.SUCCESS: [Color.BRIGHT_GREEN, Color.BOLD],
            OutputStyle.ERROR: [Color.BRIGHT_RED, Color.BOLD],
            OutputStyle.WARNING: [Color.BRIGHT_YELLOW, Color.BOLD],
            OutputStyle.INFO: [Color.BRIGHT_BLUE],
            OutputStyle.DEBUG: [Color.BRIGHT_BLACK],
            OutputStyle.HEADER: [Color.BRIGHT_WHITE, Color.BOLD],
            OutputStyle.SUBHEADER: [Color.WHITE, Color.BOLD],
            OutputStyle.EMPHASIS: [Color.BRIGHT_CYAN],
            OutputStyle.MUTED: [Color.BRIGHT_BLACK],
            OutputStyle.CODE: [Color.YELLOW]
        }

        # Unicode symbols
        self.symbols = {
            "check": "✓",
            "cross": "✗",
            "warning": "⚠",
            "info": "ℹ",
            "arrow": "→",
            "bullet": "•",
            "spinner": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        }

    def enable_color(self, enabled: bool = True):
        """Enable or disable color output.

        Args:
            enabled: Whether to enable colors
        """
        self.color_enabled = enabled

    def colorize(self, text: str, *colors: Color) -> str:
        """Apply colors to text.

        Args:
            text: Text to colorize
            *colors: Color codes to apply

        Returns:
            Colored text if colors are enabled, otherwise plain text
        """
        if not self.color_enabled or not colors:
            return text

        color_codes = "".join(color.value for color in colors)
        return f"{color_codes}{text}{Color.RESET.value}"

    def style(self, text: str, style: OutputStyle) -> str:
        """Apply a predefined style to text.

        Args:
            text: Text to style
            style: Style preset to apply

        Returns:
            Styled text
        """
        colors = self.styles.get(style, [])
        return self.colorize(text, *colors)

    def success(self, message: str, prefix: bool = True) -> str:
        """Format a success message.

        Args:
            message: Success message
            prefix: Whether to add success symbol

        Returns:
            Formatted success message
        """
        symbol = f"{self.symbols['check']} " if prefix else ""
        return self.style(f"{symbol}{message}", OutputStyle.SUCCESS)

    def error(self, message: str, prefix: bool = True) -> str:
        """Format an error message.

        Args:
            message: Error message
            prefix: Whether to add error symbol

        Returns:
            Formatted error message
        """
        symbol = f"{self.symbols['cross']} " if prefix else ""
        return self.style(f"{symbol}{message}", OutputStyle.ERROR)

    def warning(self, message: str, prefix: bool = True) -> str:
        """Format a warning message.

        Args:
            message: Warning message
            prefix: Whether to add warning symbol

        Returns:
            Formatted warning message
        """
        symbol = f"{self.symbols['warning']} " if prefix else ""
        return self.style(f"{symbol}{message}", OutputStyle.WARNING)

    def info(self, message: str, prefix: bool = True) -> str:
        """Format an info message.

        Args:
            message: Info message
            prefix: Whether to add info symbol

        Returns:
            Formatted info message
        """
        symbol = f"{self.symbols['info']} " if prefix else ""
        return self.style(f"{symbol}{message}", OutputStyle.INFO)

    def header(self, text: str, level: int = 1) -> str:
        """Format a header.

        Args:
            text: Header text
            level: Header level (1 for main, 2 for sub)

        Returns:
            Formatted header
        """
        if level == 1:
            return self.style(text, OutputStyle.HEADER)
        else:
            return self.style(text, OutputStyle.SUBHEADER)

    def code(self, text: str, inline: bool = True) -> str:
        """Format code text.

        Args:
            text: Code text
            inline: Whether this is inline code

        Returns:
            Formatted code text
        """
        if inline:
            return self.style(f"`{text}`", OutputStyle.CODE)
        else:
            lines = text.split('\n')
            formatted_lines = [self.style(f"  {line}", OutputStyle.CODE) for line in lines]
            return '\n'.join(formatted_lines)

    def table(self,
              headers: List[str],
              rows: List[List[str]],
              align: Optional[List[str]] = None) -> str:
        """Format a table.

        Args:
            headers: Table headers
            rows: Table rows
            align: Column alignments ('left', 'center', 'right')

        Returns:
            Formatted table
        """
        if not headers or not rows:
            return ""

        # Determine column widths
        all_rows = [headers] + rows
        col_widths = [max(len(str(row[i])) if i < len(row) else 0 for row in all_rows)
                      for i in range(len(headers))]

        # Default alignment
        if not align:
            align = ['left'] * len(headers)

        def format_row(row: List[str], is_header: bool = False) -> str:
            formatted_cells = []
            for i, cell in enumerate(row):
                width = col_widths[i]
                cell_str = str(cell)

                if align[i] == 'center':
                    formatted_cell = cell_str.center(width)
                elif align[i] == 'right':
                    formatted_cell = cell_str.rjust(width)
                else:
                    formatted_cell = cell_str.ljust(width)

                if is_header:
                    formatted_cell = self.style(formatted_cell, OutputStyle.HEADER)

                formatted_cells.append(formatted_cell)

            return f"| {' | '.join(formatted_cells)} |"

        # Build table
        result = []

        # Header
        result.append(format_row(headers, is_header=True))

        # Separator
        separator_cells = ["-" * width for width in col_widths]
        result.append(f"| {' | '.join(separator_cells)} |")

        # Rows
        for row in rows:
            result.append(format_row(row))

        return '\n'.join(result)

    def list_items(self, items: List[str], bullet: str = None) -> str:
        """Format a bulleted list.

        Args:
            items: List items
            bullet: Bullet character (uses default if None)

        Returns:
            Formatted list
        """
        if not items:
            return ""

        bullet_char = bullet or self.symbols['bullet']
        formatted_items = [f"{bullet_char} {item}" for item in items]
        return '\n'.join(formatted_items)

    def progress_bar(self, progress: ProgressBar) -> str:
        """Format a progress bar.

        Args:
            progress: Progress bar configuration

        Returns:
            Formatted progress bar
        """
        percent = progress.current / progress.total if progress.total > 0 else 0
        filled_width = int(progress.width * percent)
        empty_width = progress.width - filled_width

        bar = progress.fill * filled_width + progress.empty * empty_width
        percent_str = f"{percent * 100:.1f}%"

        return f"{progress.prefix}[{bar}] {percent_str} {progress.suffix}".strip()

    def spinner(self, frame: int = 0) -> str:
        """Get a spinner character for the given frame.

        Args:
            frame: Animation frame number

        Returns:
            Spinner character
        """
        return self.symbols['spinner'][frame % len(self.symbols['spinner'])]

    def wrap_text(self, text: str, width: Optional[int] = None) -> str:
        """Wrap text to terminal width.

        Args:
            text: Text to wrap
            width: Wrap width (terminal width if None)

        Returns:
            Wrapped text
        """
        if width is None:
            width = self.get_terminal_width()

        import textwrap
        return textwrap.fill(text, width=width)

    def get_terminal_width(self) -> int:
        """Get terminal width.

        Returns:
            Terminal width in characters
        """
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80  # Default width

    def get_terminal_height(self) -> int:
        """Get terminal height.

        Returns:
            Terminal height in lines
        """
        try:
            return shutil.get_terminal_size().lines
        except Exception:
            return 24  # Default height

    def print(self, *args, style: Optional[OutputStyle] = None, file: TextIO = sys.stdout, **kwargs):
        """Enhanced print function with styling support.

        Args:
            *args: Arguments to print
            style: Style to apply
            file: Output file
            **kwargs: Additional print arguments
        """
        if style:
            styled_args = [self.style(str(arg), style) for arg in args]
            print(*styled_args, file=file, **kwargs)
        else:
            print(*args, file=file, **kwargs)

    def print_success(self, message: str, **kwargs):
        """Print a success message."""
        self.print(self.success(message), **kwargs)

    def print_error(self, message: str, **kwargs):
        """Print an error message."""
        # Extract file parameter if provided to avoid conflict
        file = kwargs.pop('file', sys.stderr)
        self.print(self.error(message), file=file, **kwargs)

    def print_warning(self, message: str, **kwargs):
        """Print a warning message."""
        self.print(self.warning(message), **kwargs)

    def print_info(self, message: str, **kwargs):
        """Print an info message."""
        self.print(self.info(message), **kwargs)

    def _supports_color(self) -> bool:
        """Check if terminal supports color output.

        Returns:
            True if colors are supported
        """
        # Check if output is a terminal
        if not sys.stdout.isatty():
            return False

        # Check environment variables
        import os

        # NO_COLOR environment variable disables color
        if os.environ.get('NO_COLOR'):
            return False

        # FORCE_COLOR enables color
        if os.environ.get('FORCE_COLOR'):
            return True

        # Check TERM variable
        term = os.environ.get('TERM', '')
        if 'color' in term or term.endswith('256') or term == 'xterm':
            return True

        # Default to no color for unknown terminals
        return False


# Global output formatter instance
_output_formatter = None


def get_output_formatter() -> OutputFormatter:
    """Get the global output formatter instance."""
    global _output_formatter
    if _output_formatter is None:
        _output_formatter = OutputFormatter()
    return _output_formatter