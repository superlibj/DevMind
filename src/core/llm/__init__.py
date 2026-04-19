"""
LLM abstraction layer for AI Code Development Agent.

This module provides a universal interface for interacting with multiple
LLM providers including OpenAI, Anthropic, and local models.
"""

from .base_llm import (
    BaseLLM,
    LLMMessage,
    LLMResponse,
    LLMConfig,
    ModelCapability,
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMModelNotFoundError
)

from .model_config import (
    ModelInfo,
    ProviderType,
    ProviderConfig,
    ModelConfigManager,
    model_config_manager
)

from .llm_factory import LLMFactory, llm_factory

from .providers.litellm_provider import LiteLLMProvider, create_litellm_provider

# Convenience imports
create_llm = llm_factory.create_llm
get_available_models = llm_factory.get_available_models
validate_model = llm_factory.validate_model
get_recommended_model = llm_factory.get_recommended_model

__all__ = [
    # Core classes
    "BaseLLM",
    "LLMMessage",
    "LLMResponse",
    "LLMConfig",
    "ModelCapability",

    # Exceptions
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMModelNotFoundError",

    # Configuration
    "ModelInfo",
    "ProviderType",
    "ProviderConfig",
    "ModelConfigManager",
    "model_config_manager",

    # Factory
    "LLMFactory",
    "llm_factory",

    # Providers
    "LiteLLMProvider",
    "create_litellm_provider",

    # Convenience functions
    "create_llm",
    "get_available_models",
    "validate_model",
    "get_recommended_model",
]