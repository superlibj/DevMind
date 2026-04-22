"""
Centralized configuration management for AI Agent system.
"""
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import Dict, Any, Optional, List
import os


class SecuritySettings(BaseSettings):
    """Security-related configuration."""
    jwt_secret_key: str = Field(default="test-secret-key-for-cli", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")

    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")

    # Security scanning
    enable_code_scanning: bool = Field(default=True, env="ENABLE_CODE_SCANNING")
    bandit_config_path: Optional[str] = Field(default=None, env="BANDIT_CONFIG_PATH")
    semgrep_rules_path: Optional[str] = Field(default=None, env="SEMGREP_RULES_PATH")

    model_config = ConfigDict(env_file=".env", extra="ignore")


class LLMSettings(BaseSettings):
    """LLM provider configuration."""
    default_provider: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")

    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")

    # DeepSeek
    deepseek_api_key: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek", env="DEEPSEEK_MODEL")

    # Local models
    local_model_endpoint: Optional[str] = Field(default=None, env="LOCAL_MODEL_ENDPOINT")
    local_model_name: str = Field(default="codellama", env="LOCAL_MODEL_NAME")

    # LLM settings
    max_tokens: int = Field(default=4096, env="LLM_MAX_TOKENS")
    temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    timeout_seconds: int = Field(default=30, env="LLM_TIMEOUT_SECONDS")

    model_config = ConfigDict(env_file=".env", extra="ignore")


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    database_url: str = Field(default="sqlite:///./test.db", env="DATABASE_URL")
    echo_sql: bool = Field(default=False, env="ECHO_SQL")
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")

    model_config = ConfigDict(env_file=".env", extra="ignore")


class RedisSettings(BaseSettings):
    """Redis configuration."""
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    cache_ttl: int = Field(default=300, env="CACHE_TTL")

    model_config = ConfigDict(env_file=".env", extra="ignore")


class ToolSettings(BaseSettings):
    """Tool integration configuration."""
    git_enabled: bool = Field(default=True, env="GIT_ENABLED")
    vim_enabled: bool = Field(default=True, env="VIM_ENABLED")
    file_operations_enabled: bool = Field(default=True, env="FILE_OPERATIONS_ENABLED")

    # Tool execution limits
    tool_timeout_seconds: int = Field(default=30, env="TOOL_TIMEOUT_SECONDS")
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    allowed_file_extensions: List[str] = Field(
        default=[".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs", ".php", ".rb"]
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Handle ALLOWED_FILE_EXTENSIONS from environment
        env_extensions = os.environ.get("ALLOWED_FILE_EXTENSIONS")
        if env_extensions:
            self.allowed_file_extensions = [ext.strip() for ext in env_extensions.split(',')]

    model_config = ConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)


class AgentSettings(BaseSettings):
    """Agent behavior configuration."""
    max_iterations: int = Field(default=100, env="AGENT_MAX_ITERATIONS")
    memory_limit_mb: int = Field(default=100, env="AGENT_MEMORY_LIMIT_MB")
    conversation_history_limit: int = Field(default=50, env="CONVERSATION_HISTORY_LIMIT")

    # ReAct settings
    react_max_steps: int = Field(default=5, env="REACT_MAX_STEPS")
    react_timeout_seconds: int = Field(default=60, env="REACT_TIMEOUT_SECONDS")

    model_config = ConfigDict(env_file=".env", extra="ignore")


class AppSettings(BaseSettings):
    """Main application configuration."""
    app_name: str = Field(default="DevMind Interactive Development Assistant", env="APP_NAME")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")

    # WebSocket settings
    websocket_path: str = Field(default="/ws", env="WEBSOCKET_PATH")

    # CORS
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Handle ALLOWED_ORIGINS from environment
        env_origins = os.environ.get("ALLOWED_ORIGINS")
        if env_origins:
            self.allowed_origins = [
                origin.strip().strip('"').strip("'")
                for origin in env_origins.split(',')
            ]

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True
    )


class Settings:
    """Consolidated settings container."""

    def __init__(self):
        self.app = AppSettings()
        self.security = SecuritySettings()
        self.llm = LLMSettings()
        self.database = DatabaseSettings()
        self.redis = RedisSettings()
        self.tools = ToolSettings()
        self.agent = AgentSettings()

    @property
    def is_development(self) -> bool:
        return self.app.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.app.environment == "production"


# Global settings instance
settings = Settings()