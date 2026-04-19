"""
Real-time token usage tracking for DevMind CLI.

Provides real-time monitoring and display of token consumption
during LLM requests with cost estimation and usage statistics.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from threading import Lock

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text
from rich.layout import Layout

from ..core.llm.model_config import ModelConfigManager

console = Console()


@dataclass
class TokenUsage:
    """Represents token usage for a single request."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_input: float = 0.0
    cost_output: float = 0.0
    total_cost: float = 0.0
    timestamp: float = field(default_factory=time.time)
    model: str = ""


@dataclass
class SessionStats:
    """Aggregated token statistics for the entire session."""
    total_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    start_time: float = field(default_factory=time.time)
    models_used: Dict[str, int] = field(default_factory=dict)
    request_history: List[TokenUsage] = field(default_factory=list)


class TokenCounter:
    """Real-time token usage counter and display manager."""

    def __init__(self):
        """Initialize the token counter."""
        self.model_config = ModelConfigManager()
        self.session_stats = SessionStats()
        self.current_request: Optional[TokenUsage] = None
        self.lock = Lock()

        # Display state
        self.live_display: Optional[Live] = None
        self.show_details = True

    def start_request(self, model: str) -> None:
        """Start tracking a new LLM request.

        Args:
            model: The model being used for this request
        """
        with self.lock:
            self.current_request = TokenUsage(model=model)
            self.session_stats.total_requests += 1

            # Update model usage count
            if model in self.session_stats.models_used:
                self.session_stats.models_used[model] += 1
            else:
                self.session_stats.models_used[model] = 1

    def update_token_usage(self,
                          prompt_tokens: int = 0,
                          completion_tokens: int = 0,
                          total_tokens: int = None) -> None:
        """Update token usage for the current request.

        Args:
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens generated
            total_tokens: Total tokens (if not provided, calculated as sum)
        """
        if not self.current_request:
            return

        with self.lock:
            self.current_request.prompt_tokens = prompt_tokens
            self.current_request.completion_tokens = completion_tokens
            self.current_request.total_tokens = total_tokens or (prompt_tokens + completion_tokens)

            # Calculate costs
            self._calculate_costs()

    def _calculate_costs(self) -> None:
        """Calculate costs based on model pricing."""
        if not self.current_request:
            return

        model_info = self.model_config.get_model_info(self.current_request.model)
        if not model_info:
            return

        # Calculate costs (pricing is per 1K tokens)
        if model_info.cost_per_1k_input:
            self.current_request.cost_input = (
                self.current_request.prompt_tokens / 1000.0 * model_info.cost_per_1k_input
            )

        if model_info.cost_per_1k_output:
            self.current_request.cost_output = (
                self.current_request.completion_tokens / 1000.0 * model_info.cost_per_1k_output
            )

        self.current_request.total_cost = (
            self.current_request.cost_input + self.current_request.cost_output
        )

    def finish_request(self) -> TokenUsage:
        """Finish the current request and update session stats.

        Returns:
            The completed TokenUsage object
        """
        if not self.current_request:
            return TokenUsage()

        with self.lock:
            # Update session totals
            self.session_stats.total_prompt_tokens += self.current_request.prompt_tokens
            self.session_stats.total_completion_tokens += self.current_request.completion_tokens
            self.session_stats.total_tokens += self.current_request.total_tokens
            self.session_stats.total_cost += self.current_request.total_cost

            # Add to history
            self.session_stats.request_history.append(self.current_request)

            completed_request = self.current_request
            self.current_request = None

            return completed_request

    def get_current_usage_display(self) -> Panel:
        """Get a Rich panel showing current token usage.

        Returns:
            Rich Panel with current usage information
        """
        if not self.current_request:
            return Panel("No active request", title="Token Usage")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Current Request", style="green")
        table.add_column("Session Total", style="yellow")

        # Current request data
        current = self.current_request
        session = self.session_stats

        table.add_row(
            "Prompt Tokens",
            f"{current.prompt_tokens:,}",
            f"{session.total_prompt_tokens:,}"
        )
        table.add_row(
            "Completion Tokens",
            f"{current.completion_tokens:,}",
            f"{session.total_completion_tokens:,}"
        )
        table.add_row(
            "Total Tokens",
            f"{current.total_tokens:,}",
            f"{session.total_tokens:,}"
        )
        table.add_row(
            "Cost (USD)",
            f"${current.total_cost:.6f}",
            f"${session.total_cost:.6f}"
        )

        return Panel(
            table,
            title=f"Token Usage - {current.model}",
            title_align="left"
        )

    def get_session_summary(self) -> Panel:
        """Get a summary panel of the entire session.

        Returns:
            Rich Panel with session statistics
        """
        session = self.session_stats
        duration = time.time() - session.start_time

        # Create summary table
        summary_table = Table(show_header=False)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Duration", f"{duration/60:.1f} minutes")
        summary_table.add_row("Total Requests", f"{session.total_requests}")
        summary_table.add_row("Total Tokens", f"{session.total_tokens:,}")
        summary_table.add_row("Total Cost", f"${session.total_cost:.6f}")

        if session.total_tokens > 0:
            avg_cost_per_token = session.total_cost / session.total_tokens * 1000
            summary_table.add_row("Cost per 1K tokens", f"${avg_cost_per_token:.6f}")

        # Models used
        models_text = Text()
        for model, count in session.models_used.items():
            models_text.append(f"{model}: {count} requests\n", style="green")

        if len(session.models_used) > 1:
            content = Table.grid()
            content.add_column()
            content.add_column()
            content.add_row(summary_table, models_text)
        else:
            content = summary_table

        return Panel(
            content,
            title="Session Summary",
            title_align="left"
        )

    def show_token_stats(self) -> None:
        """Display current token statistics."""
        if self.current_request:
            console.print(self.get_current_usage_display())
        else:
            console.print(self.get_session_summary())

    def start_live_display(self) -> None:
        """Start live updating token display."""
        if self.live_display:
            return

        layout = Layout()
        layout.split_column(
            Layout(name="usage", ratio=3),
            Layout(name="summary", ratio=2)
        )

        def update_layout():
            if self.current_request:
                layout["usage"].update(self.get_current_usage_display())
                layout["summary"].update(self.get_session_summary())
            else:
                layout["usage"].update(Panel("No active request"))
                layout["summary"].update(self.get_session_summary())

        update_layout()
        self.live_display = Live(layout, refresh_per_second=2, console=console)
        self.live_display.start()

    def stop_live_display(self) -> None:
        """Stop live updating token display."""
        if self.live_display:
            self.live_display.stop()
            self.live_display = None

    def update_live_display(self) -> None:
        """Update the live display if it's running."""
        if not self.live_display:
            return

        layout = self.live_display.renderable
        if self.current_request:
            layout["usage"].update(self.get_current_usage_display())
        layout["summary"].update(self.get_session_summary())

    def get_recent_requests(self, limit: int = 5) -> List[TokenUsage]:
        """Get the most recent token usage records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent TokenUsage objects
        """
        with self.lock:
            return self.session_stats.request_history[-limit:]

    def export_usage_report(self) -> str:
        """Export detailed usage report as text.

        Returns:
            Formatted text report of token usage
        """
        session = self.session_stats
        duration = time.time() - session.start_time

        report = []
        report.append("=" * 60)
        report.append("DevMind Token Usage Report")
        report.append("=" * 60)
        report.append(f"Session Duration: {duration/60:.1f} minutes")
        report.append(f"Total Requests: {session.total_requests}")
        report.append(f"Total Tokens: {session.total_tokens:,}")
        report.append(f"  - Prompt Tokens: {session.total_prompt_tokens:,}")
        report.append(f"  - Completion Tokens: {session.total_completion_tokens:,}")
        report.append(f"Total Cost: ${session.total_cost:.6f}")
        report.append("")

        # Model breakdown
        report.append("Models Used:")
        for model, count in session.models_used.items():
            report.append(f"  - {model}: {count} requests")

        report.append("")

        # Recent requests
        report.append("Recent Requests:")
        for i, usage in enumerate(self.get_recent_requests(10)):
            timestamp = time.strftime('%H:%M:%S', time.localtime(usage.timestamp))
            report.append(
                f"  {i+1}. [{timestamp}] {usage.model} - "
                f"{usage.total_tokens:,} tokens (${usage.total_cost:.6f})"
            )

        return "\n".join(report)


# Global token counter instance
token_counter = TokenCounter()