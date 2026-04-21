"""
Model configuration management for different LLM providers.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from .base_llm import LLMConfig, ModelCapability


class ProviderType(Enum):
    """Enum for LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    AZURE_OPENAI = "azure_openai"
    GOOGLE = "google"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    DEEPSEEK = "deepseek"


@dataclass
class ModelInfo:
    """Information about a specific model."""
    name: str
    provider: ProviderType
    max_tokens: int
    context_window: int
    capabilities: List[ModelCapability]
    cost_per_1k_input: Optional[float] = None
    cost_per_1k_output: Optional[float] = None
    supports_streaming: bool = True
    supports_tools: bool = False
    description: str = ""


@dataclass
class ProviderConfig:
    """Configuration for a specific provider."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    organization: Optional[str] = None
    additional_headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


class ModelConfigManager:
    """Manages model configurations and capabilities."""

    def __init__(self):
        self._models = self._initialize_models()
        self._providers: Dict[ProviderType, ProviderConfig] = {}

    def _initialize_models(self) -> Dict[str, ModelInfo]:
        """Initialize the model registry."""
        return {
            # OpenAI Models
            "gpt-4-turbo-preview": ModelInfo(
                name="gpt-4-turbo-preview",
                provider=ProviderType.OPENAI,
                max_tokens=4096,
                context_window=128000,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.TOOL_CALLING
                ],
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.03,
                supports_tools=True,
                description="GPT-4 Turbo with latest improvements"
            ),
            "gpt-4": ModelInfo(
                name="gpt-4",
                provider=ProviderType.OPENAI,
                max_tokens=8192,
                context_window=8192,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.TOOL_CALLING
                ],
                cost_per_1k_input=0.03,
                cost_per_1k_output=0.06,
                supports_tools=True,
                description="GPT-4 standard model"
            ),
            "gpt-3.5-turbo": ModelInfo(
                name="gpt-3.5-turbo",
                provider=ProviderType.OPENAI,
                max_tokens=4096,
                context_window=16385,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TOOL_CALLING
                ],
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.002,
                supports_tools=True,
                description="Fast and efficient GPT-3.5 Turbo"
            ),

            # Anthropic Models
            "claude-3-opus-20240229": ModelInfo(
                name="claude-3-opus-20240229",
                provider=ProviderType.ANTHROPIC,
                max_tokens=4096,
                context_window=200000,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.TOOL_CALLING
                ],
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.075,
                supports_tools=True,
                description="Claude 3 Opus - Most capable model"
            ),
            "claude-3-sonnet-20240229": ModelInfo(
                name="claude-3-sonnet-20240229",
                provider=ProviderType.ANTHROPIC,
                max_tokens=4096,
                context_window=200000,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.TOOL_CALLING
                ],
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                supports_tools=True,
                description="Claude 3 Sonnet - Balanced performance"
            ),
            "claude-3-haiku-20240307": ModelInfo(
                name="claude-3-haiku-20240307",
                provider=ProviderType.ANTHROPIC,
                max_tokens=4096,
                context_window=200000,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TOOL_CALLING
                ],
                cost_per_1k_input=0.00025,
                cost_per_1k_output=0.00125,
                supports_tools=True,
                description="Claude 3 Haiku - Fastest model"
            ),

            # DeepSeek Models
            "deepseek-chat": ModelInfo(
                name="deepseek-chat",
                provider=ProviderType.DEEPSEEK,
                max_tokens=8192,
                context_window=32768,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TOOL_CALLING
                ],
                cost_per_1k_input=0.0014,
                cost_per_1k_output=0.0028,
                supports_streaming=True,
                supports_tools=True,
                description="DeepSeek Chat - General purpose conversation and coding"
            ),
            "deepseek-coder": ModelInfo(
                name="deepseek-chat",  # Map to actual API model
                provider=ProviderType.DEEPSEEK,
                max_tokens=8192,
                context_window=128000,
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.CHAT
                ],
                cost_per_1k_input=0.0014,
                cost_per_1k_output=0.0028,
                supports_streaming=True,
                supports_tools=True,
                description="DeepSeek Coder - Uses deepseek-chat for code generation and review"
            ),
            "deepseek-reasoner": ModelInfo(
                name="deepseek-reasoner",
                provider=ProviderType.DEEPSEEK,
                max_tokens=8192,
                context_window=128000,
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.CHAT
                ],
                cost_per_1k_input=0.0014,
                cost_per_1k_output=0.0028,
                supports_streaming=True,
                supports_tools=True,
                description="DeepSeek Reasoner - Advanced reasoning mode (DeepSeek-V3.2)"
            ),

            # Ollama Models
            "llama3.2": ModelInfo(
                name="llama3.2",
                provider=ProviderType.OLLAMA,
                max_tokens=8192,
                context_window=128000,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.COMPLETION
                ],
                supports_tools=False,
                description="Llama 3.2 - Advanced reasoning and coding capabilities"
            ),
            "llama3.1": ModelInfo(
                name="llama3.1",
                provider=ProviderType.OLLAMA,
                max_tokens=8192,
                context_window=128000,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.COMPLETION
                ],
                supports_tools=False,
                description="Llama 3.1 - Large context model with strong performance"
            ),
            "codellama": ModelInfo(
                name="codellama",
                provider=ProviderType.OLLAMA,
                max_tokens=4096,
                context_window=16384,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.COMPLETION
                ],
                supports_tools=False,
                description="Code Llama 7B/13B/34B - Specialized for code generation"
            ),
            "codellama:13b": ModelInfo(
                name="codellama:13b",
                provider=ProviderType.OLLAMA,
                max_tokens=4096,
                context_window=16384,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW
                ],
                supports_tools=False,
                description="Code Llama 13B - Better coding performance"
            ),
            "codellama:34b": ModelInfo(
                name="codellama:34b",
                provider=ProviderType.OLLAMA,
                max_tokens=4096,
                context_window=16384,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.COMPLETION
                ],
                supports_tools=False,
                description="Code Llama 34B - Best coding performance"
            ),
            "deepseek-coder:ollama": ModelInfo(
                name="deepseek-coder:ollama",
                provider=ProviderType.OLLAMA,
                max_tokens=8192,
                context_window=16384,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW
                ],
                supports_tools=False,
                description="DeepSeek Coder - Excellent for programming tasks"
            ),
            "qwen2.5-coder": ModelInfo(
                name="qwen2.5-coder:7b",
                provider=ProviderType.OLLAMA,
                max_tokens=8192,
                context_window=32768,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.COMPLETION
                ],
                supports_tools=False,
                description="Qwen2.5 Coder - Strong multilingual coding model"
            ),
            "qwen2.5-coder:7b": ModelInfo(
                name="qwen2.5-coder:7b",
                provider=ProviderType.OLLAMA,
                max_tokens=8192,
                context_window=32768,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.COMPLETION
                ],
                supports_tools=False,
                description="Qwen2.5 Coder 7B - Strong multilingual coding model"
            ),
            "starcoder2": ModelInfo(
                name="starcoder2",
                provider=ProviderType.OLLAMA,
                max_tokens=4096,
                context_window=16384,
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.COMPLETION,
                    ModelCapability.CODE_REVIEW
                ],
                supports_tools=False,
                description="StarCoder2 - High-quality code generation"
            ),
            "mistral": ModelInfo(
                name="mistral",
                provider=ProviderType.OLLAMA,
                max_tokens=8192,
                context_window=32768,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.COMPLETION,
                    ModelCapability.CODE_GENERATION
                ],
                supports_tools=False,
                description="Mistral 7B - Fast and capable general model"
            ),
            "mixtral": ModelInfo(
                name="mixtral",
                provider=ProviderType.OLLAMA,
                max_tokens=8192,
                context_window=32768,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.COMPLETION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.COMPLETION
                ],
                supports_tools=False,
                description="Mixtral 8x7B - Mixture of experts model with excellent performance"
            ),
            "llama2": ModelInfo(
                name="llama2",
                provider=ProviderType.OLLAMA,
                max_tokens=4096,
                context_window=4096,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.COMPLETION
                ],
                supports_tools=False,
                description="Llama 2 - Reliable foundation model"
            ),
            "phi3": ModelInfo(
                name="phi3",
                provider=ProviderType.OLLAMA,
                max_tokens=4096,
                context_window=128000,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.COMPLETION
                ],
                supports_tools=False,
                description="Phi-3 - Compact but powerful model"
            ),

            # Llama.cpp Models
            "llama-cpp-local": ModelInfo(
                name="llama-cpp-local",
                provider=ProviderType.LLAMA_CPP,
                max_tokens=4096,
                context_window=8192,
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.COMPLETION,
                    ModelCapability.CODE_GENERATION
                ],
                supports_tools=False,
                description="Local model via llama.cpp server"
            ),
            "llama-cpp-codeqwen": ModelInfo(
                name="llama-cpp-codeqwen",
                provider=ProviderType.LLAMA_CPP,
                max_tokens=4096,
                context_window=32768,
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.CHAT
                ],
                supports_tools=False,
                description="CodeQwen via llama.cpp for coding tasks"
            ),
            "llama-cpp-codellama": ModelInfo(
                name="llama-cpp-codellama",
                provider=ProviderType.LLAMA_CPP,
                max_tokens=4096,
                context_window=16384,
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.COMPLETION,
                    ModelCapability.CHAT
                ],
                supports_tools=False,
                description="Code Llama via llama.cpp server"
            ),
        }

    def register_provider(self, provider: ProviderType, config: ProviderConfig):
        """Register a provider configuration.

        Args:
            provider: The provider type
            config: The provider configuration
        """
        self._providers[provider] = config

    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get information about a model.

        Args:
            model_name: The name of the model

        Returns:
            ModelInfo if found, None otherwise
        """
        return self._models.get(model_name)

    def get_provider_config(self, provider: ProviderType) -> Optional[ProviderConfig]:
        """Get configuration for a provider.

        Args:
            provider: The provider type

        Returns:
            ProviderConfig if found, None otherwise
        """
        return self._providers.get(provider)

    def list_models(
        self,
        provider: Optional[ProviderType] = None,
        capability: Optional[ModelCapability] = None
    ) -> List[ModelInfo]:
        """List available models with optional filtering.

        Args:
            provider: Filter by provider type
            capability: Filter by capability

        Returns:
            List of ModelInfo objects matching the filters
        """
        models = list(self._models.values())

        if provider:
            models = [m for m in models if m.provider == provider]

        if capability:
            models = [m for m in models if capability in m.capabilities]

        return models

    def get_best_model(
        self,
        capability: ModelCapability,
        max_cost: Optional[float] = None,
        provider: Optional[ProviderType] = None
    ) -> Optional[ModelInfo]:
        """Get the best model for a specific capability.

        Args:
            capability: Required capability
            max_cost: Maximum cost per 1k tokens (input)
            provider: Preferred provider

        Returns:
            Best matching ModelInfo or None
        """
        candidates = self.list_models(provider=provider, capability=capability)

        if max_cost:
            candidates = [
                m for m in candidates
                if m.cost_per_1k_input is None or m.cost_per_1k_input <= max_cost
            ]

        if not candidates:
            return None

        # Sort by capabilities (more is better), then by cost (lower is better)
        def score_model(model: ModelInfo) -> tuple:
            capability_score = len(model.capabilities)
            cost_score = model.cost_per_1k_input or 0
            # Prefer models with tool support for advanced capabilities
            tool_bonus = 1 if model.supports_tools else 0
            return (-capability_score, cost_score, -tool_bonus)

        return min(candidates, key=score_model)

    def create_llm_config(
        self,
        model_name: str,
        **overrides
    ) -> LLMConfig:
        """Create an LLM config for a specific model.

        Args:
            model_name: The model name
            **overrides: Configuration overrides

        Returns:
            LLMConfig object

        Raises:
            ValueError: If model is not found
        """
        model_info = self.get_model_info(model_name)
        if not model_info:
            raise ValueError(f"Model '{model_name}' not found")

        config_data = {
            "model": model_name,
            "max_tokens": model_info.max_tokens,  # Use model's actual max_tokens
            "temperature": 0.1,
            "timeout": 30,
            "stream": False,
        }
        config_data.update(overrides)

        return LLMConfig(**config_data)

    def validate_model_capability(
        self,
        model_name: str,
        required_capability: ModelCapability
    ) -> bool:
        """Validate that a model supports a required capability.

        Args:
            model_name: The model name
            required_capability: The required capability

        Returns:
            True if the model supports the capability
        """
        model_info = self.get_model_info(model_name)
        return (
            model_info is not None and
            required_capability in model_info.capabilities
        )


# Global model config manager instance
model_config_manager = ModelConfigManager()