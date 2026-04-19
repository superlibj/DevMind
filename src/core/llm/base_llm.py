"""
Abstract base class for LLM providers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass
from enum import Enum


class ModelCapability(Enum):
    """Enum for model capabilities."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    TOOL_CALLING = "tool_calling"


@dataclass
class LLMMessage:
    """Represents a message in a conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMResponse:
    """Represents an LLM response."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMConfig:
    """Configuration for LLM requests."""
    model: str
    max_tokens: int = 4096
    temperature: float = 0.1
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    timeout: int = 30
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None


class BaseLLM(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, config: LLMConfig):
        """Initialize the LLM provider.

        Args:
            config: LLM configuration
        """
        self.config = config
        self._model_info: Optional[Dict[str, Any]] = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the LLM provider."""
        pass

    @property
    @abstractmethod
    def supported_capabilities(self) -> List[ModelCapability]:
        """Return the list of supported capabilities."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        config_override: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            messages: List of conversation messages
            config_override: Optional config override for this request

        Returns:
            LLM response

        Raises:
            LLMError: If the generation fails
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        config_override: Optional[LLMConfig] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM.

        Args:
            messages: List of conversation messages
            config_override: Optional config override for this request

        Yields:
            Streaming response chunks

        Raises:
            LLMError: If the generation fails
        """
        pass

    @abstractmethod
    async def count_tokens(self, messages: List[LLMMessage]) -> int:
        """Count the number of tokens in the messages.

        Args:
            messages: List of messages to count tokens for

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    async def validate_model(self) -> bool:
        """Validate that the model is available and accessible.

        Returns:
            True if model is valid and accessible
        """
        pass

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model.

        Returns:
            Model information dictionary
        """
        if self._model_info is None:
            await self._load_model_info()
        return self._model_info or {}

    @abstractmethod
    async def _load_model_info(self) -> None:
        """Load model information (to be implemented by providers)."""
        pass

    def supports_capability(self, capability: ModelCapability) -> bool:
        """Check if the provider supports a specific capability.

        Args:
            capability: The capability to check

        Returns:
            True if the capability is supported
        """
        return capability in self.supported_capabilities

    def create_config(self, **kwargs) -> LLMConfig:
        """Create a new config with overrides.

        Args:
            **kwargs: Configuration overrides

        Returns:
            New LLMConfig with overrides applied
        """
        config_dict = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            "stop": self.config.stop,
            "timeout": self.config.timeout,
            "stream": self.config.stream,
            "tools": self.config.tools,
            "tool_choice": self.config.tool_choice,
        }
        config_dict.update(kwargs)
        return LLMConfig(**config_dict)


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    def __init__(self, message: str, provider: Optional[str] = None, model: Optional[str] = None):
        super().__init__(message)
        self.provider = provider
        self.model = model


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when authentication fails."""
    pass


class LLMModelNotFoundError(LLMError):
    """Raised when the specified model is not found."""
    pass