"""
Output formatter for DevMind CLI.

Handles formatting and displaying streaming responses with syntax highlighting,
progress indicators, and structured output formatting.
"""
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.columns import Columns

console = Console()


class OutputFormatter:
    """Formats and displays agent responses with Rich styling."""

    def __init__(self):
        """Initialize output formatter."""
        # Language detection patterns
        self.language_patterns = {
            r'```python': 'python',
            r'```py': 'python',
            r'```javascript': 'javascript',
            r'```js': 'javascript',
            r'```typescript': 'typescript',
            r'```ts': 'typescript',
            r'```bash': 'bash',
            r'```shell': 'bash',
            r'```sh': 'bash',
            r'```sql': 'sql',
            r'```html': 'html',
            r'```css': 'css',
            r'```json': 'json',
            r'```yaml': 'yaml',
            r'```yml': 'yaml',
            r'```xml': 'xml',
            r'```java': 'java',
            r'```cpp': 'cpp',
            r'```c\+\+': 'cpp',
            r'```c': 'c',
            r'```go': 'go',
            r'```rust': 'rust',
            r'```php': 'php',
            r'```ruby': 'ruby',
            r'```swift': 'swift',
            r'```kotlin': 'kotlin',
        }

    def display_agent_response(self, response: str) -> None:
        """Display an agent response with formatting.

        Args:
            response: Raw agent response text
        """
        # Parse and format the response
        formatted_response = self._format_response(response)

        # Display with appropriate styling
        console.print("\n")  # Add spacing
        console.print(formatted_response)

    def _format_response(self, response: str) -> Any:
        """Format agent response with syntax highlighting and structure.

        Args:
            response: Raw response text

        Returns:
            Formatted Rich renderable
        """
        # Check if response contains code blocks
        if "```" in response:
            return self._format_response_with_code(response)
        else:
            return self._format_plain_response(response)

    def _format_response_with_code(self, response: str) -> Any:
        """Format response containing code blocks.

        Args:
            response: Response with code blocks

        Returns:
            Formatted Rich renderable
        """
        parts = []
        current_part = ""
        in_code_block = False
        code_language = None
        code_content = ""

        lines = response.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for code block start
            if line.strip().startswith('```') and not in_code_block:
                # Save any preceding text
                if current_part.strip():
                    parts.append(self._create_text_panel(current_part.strip()))
                    current_part = ""

                # Determine language
                code_language = self._detect_code_language(line)
                in_code_block = True
                code_content = ""

            # Check for code block end
            elif line.strip() == '```' and in_code_block:
                # Create syntax-highlighted code block
                if code_content.strip():
                    parts.append(self._create_code_panel(code_content.strip(), code_language))

                in_code_block = False
                code_language = None
                code_content = ""

            # Inside code block
            elif in_code_block:
                code_content += line + "\n"

            # Regular text
            else:
                current_part += line + "\n"

            i += 1

        # Add any remaining text
        if current_part.strip():
            parts.append(self._create_text_panel(current_part.strip()))

        # Add any remaining code (unclosed block)
        if in_code_block and code_content.strip():
            parts.append(self._create_code_panel(code_content.strip(), code_language))

        return Columns(parts, expand=False) if len(parts) > 1 else parts[0] if parts else Text(response)

    def _format_plain_response(self, response: str) -> Any:
        """Format plain text response.

        Args:
            response: Plain text response

        Returns:
            Formatted Rich renderable
        """
        # Check if it looks like markdown
        if self._looks_like_markdown(response):
            return self._create_markdown_panel(response)
        else:
            return self._create_text_panel(response)

    def _detect_code_language(self, code_line: str) -> Optional[str]:
        """Detect code language from opening line.

        Args:
            code_line: Line with code block opening

        Returns:
            Detected language or None
        """
        for pattern, language in self.language_patterns.items():
            if re.match(pattern, code_line, re.IGNORECASE):
                return language

        # Check for just the language name after ```
        match = re.match(r'```(\w+)', code_line)
        if match:
            return match.group(1).lower()

        return None

    def _looks_like_markdown(self, text: str) -> bool:
        """Check if text looks like markdown.

        Args:
            text: Text to check

        Returns:
            True if likely markdown
        """
        markdown_indicators = [
            r'^#{1,6}\s',  # Headers
            r'^\*\s',      # Unordered list
            r'^\d+\.\s',   # Ordered list
            r'\*\*.*\*\*', # Bold
            r'\*.*\*',     # Italic
            r'`.*`',       # Inline code
            r'^\-\s',      # Dash list
            r'^\>\s',      # Blockquote
        ]

        for pattern in markdown_indicators:
            if re.search(pattern, text, re.MULTILINE):
                return True

        return False

    def _create_text_panel(self, text: str) -> Panel:
        """Create a text panel.

        Args:
            text: Text content

        Returns:
            Rich Panel
        """
        return Panel(
            Text(text),
            border_style="bright_black",
            padding=(0, 1)
        )

    def _create_markdown_panel(self, text: str) -> Panel:
        """Create a markdown panel.

        Args:
            text: Markdown content

        Returns:
            Rich Panel
        """
        return Panel(
            Markdown(text),
            border_style="bright_blue",
            title="[bold blue]Response[/bold blue]",
            padding=(0, 1)
        )

    def _create_code_panel(self, code: str, language: Optional[str]) -> Panel:
        """Create a syntax-highlighted code panel.

        Args:
            code: Code content
            language: Programming language

        Returns:
            Rich Panel with syntax highlighting
        """
        if language:
            syntax = Syntax(
                code,
                language,
                theme="monokai",
                line_numbers=True,
                background_color="default"
            )
            title = f"[bold green]{language.upper()}[/bold green]"
        else:
            syntax = Syntax(
                code,
                "text",
                theme="monokai",
                background_color="default"
            )
            title = "[bold green]CODE[/bold green]"

        return Panel(
            syntax,
            title=title,
            border_style="bright_green",
            padding=(0, 1)
        )

    def display_tool_execution(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Display tool execution start.

        Args:
            tool_name: Name of the tool
            args: Tool arguments
        """
        args_text = ", ".join([f"{k}={v}" for k, v in args.items()])
        console.print(f"[dim]🔧 Executing {tool_name}({args_text})[/dim]")

    def display_tool_result(self, tool_name: str, success: bool, result: Any) -> None:
        """Display tool execution result.

        Args:
            tool_name: Name of the tool
            success: Whether tool succeeded
            result: Tool result
        """
        if success:
            console.print(f"[green]✓[/green] [dim]{tool_name} completed[/dim]")
            if result and str(result).strip():
                # Format result based on type
                if isinstance(result, dict) or isinstance(result, list):
                    console.print(Panel(
                        Syntax(str(result), "json", theme="monokai"),
                        title="[bold blue]Result[/bold blue]",
                        border_style="bright_blue"
                    ))
                else:
                    console.print(Panel(
                        str(result),
                        title="[bold blue]Result[/bold blue]",
                        border_style="bright_blue"
                    ))
        else:
            console.print(f"[red]✗[/red] [dim]{tool_name} failed[/dim]")
            if result:
                console.print(Panel(
                    str(result),
                    title="[bold red]Error[/bold red]",
                    border_style="bright_red"
                ))

    def display_thinking_indicator(self, message: str = "Thinking...") -> None:
        """Display a thinking indicator.

        Args:
            message: Status message
        """
        console.print(f"[dim]💭 {message}[/dim]")

    def display_error(self, error: str) -> None:
        """Display an error message.

        Args:
            error: Error message
        """
        console.print(Panel(
            Text(error, style="bold red"),
            title="[bold red]Error[/bold red]",
            border_style="bright_red"
        ))

    def display_warning(self, warning: str) -> None:
        """Display a warning message.

        Args:
            warning: Warning message
        """
        console.print(Panel(
            Text(warning, style="bold yellow"),
            title="[bold yellow]Warning[/bold yellow]",
            border_style="bright_yellow"
        ))

    def display_info(self, info: str) -> None:
        """Display an info message.

        Args:
            info: Info message
        """
        console.print(Panel(
            Text(info, style="bold blue"),
            title="[bold blue]Info[/bold blue]",
            border_style="bright_blue"
        ))

    def create_file_tree(self, root_path: Path, max_depth: int = 3) -> Table:
        """Create a visual file tree.

        Args:
            root_path: Root directory path
            max_depth: Maximum depth to show

        Returns:
            Rich Table with file tree
        """
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Tree", style="bright_blue", no_wrap=False)

        def add_directory_contents(path: Path, depth: int, prefix: str = ""):
            if depth > max_depth:
                return

            try:
                items = sorted(path.iterdir())
                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    next_prefix = "    " if is_last else "│   "

                    if item.is_dir():
                        table.add_row(f"{prefix}{current_prefix}📁 {item.name}/")
                        add_directory_contents(item, depth + 1, prefix + next_prefix)
                    else:
                        file_icon = self._get_file_icon(item.suffix)
                        table.add_row(f"{prefix}{current_prefix}{file_icon} {item.name}")
            except PermissionError:
                table.add_row(f"{prefix}[red]Permission denied[/red]")

        table.add_row(f"📁 {root_path.name}/")
        add_directory_contents(root_path, 0)

        return table

    def _get_file_icon(self, extension: str) -> str:
        """Get an icon for a file extension.

        Args:
            extension: File extension

        Returns:
            Icon emoji
        """
        icon_map = {
            '.py': '🐍',
            '.js': '📜',
            '.ts': '📘',
            '.html': '🌐',
            '.css': '🎨',
            '.json': '📋',
            '.md': '📝',
            '.txt': '📄',
            '.yml': '⚙️',
            '.yaml': '⚙️',
            '.xml': '📰',
            '.sql': '🗃️',
            '.sh': '🔧',
            '.bat': '🔧',
            '.exe': '⚡',
            '.jpg': '🖼️',
            '.png': '🖼️',
            '.gif': '🖼️',
            '.pdf': '📕',
            '.zip': '📦',
        }

        return icon_map.get(extension.lower(), '📄')