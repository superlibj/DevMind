"""
CLI-specific configuration for DevMind Interactive Development Assistant.

This configuration file contains settings specifically for the CLI interface,
separate from the web API configuration.
"""
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class CLISettings(BaseSettings):
    """CLI-specific configuration."""

    # Session management
    sessions_dir: str = Field(default="./sessions", env="CLI_SESSIONS_DIR")
    auto_save_sessions: bool = Field(default=True, env="CLI_AUTO_SAVE")
    session_history_limit: int = Field(default=100, env="CLI_SESSION_HISTORY_LIMIT")

    # Display preferences
    syntax_highlighting: bool = Field(default=True, env="CLI_SYNTAX_HIGHLIGHTING")
    show_line_numbers: bool = Field(default=True, env="CLI_SHOW_LINE_NUMBERS")
    theme: str = Field(default="monokai", env="CLI_THEME")

    # REPL behavior
    multiline_support: bool = Field(default=True, env="CLI_MULTILINE_SUPPORT")
    command_history_size: int = Field(default=1000, env="CLI_COMMAND_HISTORY_SIZE")
    auto_complete: bool = Field(default=True, env="CLI_AUTO_COMPLETE")

    # Streaming and progress
    show_thinking_indicators: bool = Field(default=True, env="CLI_SHOW_THINKING")
    show_tool_progress: bool = Field(default=True, env="CLI_SHOW_TOOL_PROGRESS")
    stream_responses: bool = Field(default=True, env="CLI_STREAM_RESPONSES")

    # Output formatting
    max_output_width: int = Field(default=120, env="CLI_MAX_OUTPUT_WIDTH")
    wrap_text: bool = Field(default=True, env="CLI_WRAP_TEXT")
    show_timestamps: bool = Field(default=False, env="CLI_SHOW_TIMESTAMPS")

    model_config = ConfigDict(env_file=".env", extra="ignore")


class CLILLMSettings(BaseSettings):
    """CLI-specific LLM configuration."""

    # Default model selection
    default_provider: str = Field(default="anthropic", env="CLI_DEFAULT_PROVIDER")
    default_model: str = Field(default="claude-3-sonnet-20240229", env="CLI_DEFAULT_MODEL")

    # Streaming preferences
    prefer_streaming: bool = Field(default=True, env="CLI_PREFER_STREAMING")
    streaming_chunk_size: int = Field(default=1024, env="CLI_STREAMING_CHUNK_SIZE")

    # Response behavior
    temperature: float = Field(default=0.1, env="CLI_TEMPERATURE")
    max_tokens: int = Field(default=4096, env="CLI_MAX_TOKENS")
    timeout_seconds: int = Field(default=30, env="CLI_TIMEOUT")

    # Model switching
    remember_last_model: bool = Field(default=True, env="CLI_REMEMBER_MODEL")

    model_config = ConfigDict(env_file=".env", extra="ignore")


class CLIToolsSettings(BaseSettings):
    """CLI-specific tools configuration."""

    # Tool execution
    tool_timeout: int = Field(default=60, env="CLI_TOOL_TIMEOUT")
    show_tool_output: bool = Field(default=True, env="CLI_SHOW_TOOL_OUTPUT")
    interactive_confirmations: bool = Field(default=True, env="CLI_INTERACTIVE_CONFIRMATIONS")

    # File operations
    max_file_size_mb: int = Field(default=10, env="CLI_MAX_FILE_SIZE_MB")
    allowed_extensions: List[str] = Field(
        default=[
            ".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs",
            ".php", ".rb", ".swift", ".kt", ".scala", ".clj", ".hs",
            ".html", ".css", ".scss", ".less", ".json", ".xml", ".yaml",
            ".yml", ".toml", ".ini", ".cfg", ".conf", ".md", ".txt",
            ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd"
        ],
        env="CLI_ALLOWED_EXTENSIONS"
    )

    # Git integration
    git_auto_status: bool = Field(default=True, env="CLI_GIT_AUTO_STATUS")
    git_show_diffs: bool = Field(default=True, env="CLI_GIT_SHOW_DIFFS")

    model_config = ConfigDict(env_file=".env", extra="ignore")


class CLISecuritySettings(BaseSettings):
    """CLI-specific security configuration."""

    # Code scanning
    enable_code_scanning: bool = Field(default=False, env="CLI_ENABLE_CODE_SCANNING")
    scan_generated_code: bool = Field(default=False, env="CLI_SCAN_GENERATED_CODE")

    # File access
    restrict_file_access: bool = Field(default=False, env="CLI_RESTRICT_FILE_ACCESS")
    allowed_directories: List[str] = Field(default_factory=list)

    # Command execution
    allow_shell_commands: bool = Field(default=True, env="CLI_ALLOW_SHELL_COMMANDS")
    shell_command_whitelist: List[str] = Field(default=[], env="CLI_SHELL_WHITELIST")

    model_config = ConfigDict(env_file=".env", extra="ignore")


class CLIAgentSettings(BaseSettings):
    """CLI-specific agent configuration."""

    # ReAct behavior
    max_iterations: int = Field(default=100, env="CLI_AGENT_MAX_ITERATIONS")
    react_max_steps: int = Field(default=50, env="CLI_REACT_MAX_STEPS")

    # Memory management
    conversation_memory_limit: int = Field(default=50, env="CLI_CONVERSATION_MEMORY_LIMIT")
    working_memory_limit: int = Field(default=20, env="CLI_WORKING_MEMORY_LIMIT")

    # Streaming behavior
    stream_thoughts: bool = Field(default=True, env="CLI_STREAM_THOUGHTS")
    stream_actions: bool = Field(default=True, env="CLI_STREAM_ACTIONS")
    stream_observations: bool = Field(default=True, env="CLI_STREAM_OBSERVATIONS")

    # Progress indicators
    show_iteration_progress: bool = Field(default=True, env="CLI_SHOW_ITERATION_PROGRESS")
    show_tool_execution_details: bool = Field(default=True, env="CLI_SHOW_TOOL_DETAILS")

    model_config = ConfigDict(env_file=".env", extra="ignore")


class CLIConfig:
    """Consolidated CLI configuration container."""

    def __init__(self):
        self.cli = CLISettings()
        self.llm = CLILLMSettings()
        self.tools = CLIToolsSettings()
        self.security = CLISecuritySettings()
        self.agent = CLIAgentSettings()

    def get_sessions_directory(self) -> str:
        """Get the sessions directory path."""
        import os
        from pathlib import Path

        sessions_dir = Path(self.cli.sessions_dir)
        if not sessions_dir.is_absolute():
            # Make relative to project root
            project_root = Path(__file__).parent.parent
            sessions_dir = project_root / sessions_dir

        # Create directory if it doesn't exist
        sessions_dir.mkdir(parents=True, exist_ok=True)

        return str(sessions_dir)

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return os.getenv("ENVIRONMENT", "development") == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return os.getenv("ENVIRONMENT", "development") == "production"


# Global CLI config instance
cli_config = CLIConfig()