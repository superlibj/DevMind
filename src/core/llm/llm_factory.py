"""
LLM Factory for creating and managing LLM provider instances.
"""
import logging
from typing import Optional, Dict, Any, Type
from config.settings import settings
from .base_llm import BaseLLM, LLMConfig, LLMError
from .model_config import ModelConfigManager, ProviderType, ProviderConfig
from .providers.litellm_provider import LiteLLMProvider

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM provider instances."""

    def __init__(self):
        self._model_config_manager = ModelConfigManager()
        self._provider_cache: Dict[str, BaseLLM] = {}
        self._setup_providers()

    def _setup_providers(self):
        """Setup provider configurations from settings."""
        # OpenAI configuration
        if settings.llm.openai_api_key:
            openai_config = ProviderConfig(
                api_key=settings.llm.openai_api_key,
                timeout=settings.llm.timeout_seconds,
                max_retries=3
            )
            self._model_config_manager.register_provider(
                ProviderType.OPENAI, openai_config
            )

        # Anthropic configuration
        if settings.llm.anthropic_api_key:
            anthropic_config = ProviderConfig(
                api_key=settings.llm.anthropic_api_key,
                timeout=settings.llm.timeout_seconds,
                max_retries=3
            )
            self._model_config_manager.register_provider(
                ProviderType.ANTHROPIC, anthropic_config
            )

        # Local model configuration
        if settings.llm.local_model_endpoint:
            local_config = ProviderConfig(
                base_url=settings.llm.local_model_endpoint,
                timeout=settings.llm.timeout_seconds,
                max_retries=2
            )
            self._model_config_manager.register_provider(
                ProviderType.LOCAL, local_config
            )

    def create_llm(
        self,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        use_cache: bool = True,
        **config_kwargs
    ) -> BaseLLM:
        """Create an LLM provider instance.

        Args:
            model: Specific model name (defaults to configured default)
            provider_type: Force specific provider type
            use_cache: Whether to use cached instances
            **config_kwargs: Additional configuration parameters

        Returns:
            BaseLLM instance

        Raises:
            LLMError: If model or provider is not available
        """
        # Determine model to use
        if not model:
            model = self._get_default_model()

        # Create cache key
        cache_key = f"{model}:{provider_type}:{hash(frozenset(config_kwargs.items()))}"

        # Return cached instance if available
        if use_cache and cache_key in self._provider_cache:
            logger.debug(f"Using cached LLM instance for {model}")
            return self._provider_cache[cache_key]

        # Get model information
        model_info = self._model_config_manager.get_model_info(model)
        if not model_info:
            logger.warning(f"Model {model} not in registry, using LiteLLM with defaults")

        # Create LLM configuration
        try:
            llm_config = self._model_config_manager.create_llm_config(
                model, **config_kwargs
            )
        except ValueError:
            # Model not in registry, create basic config
            llm_config = LLMConfig(
                model=model,
                max_tokens=config_kwargs.get("max_tokens", settings.llm.max_tokens),
                temperature=config_kwargs.get("temperature", settings.llm.temperature),
                timeout=config_kwargs.get("timeout", settings.llm.timeout_seconds)
            )

        # Create provider instance
        provider = self._create_provider(llm_config, provider_type)

        # Cache the instance
        if use_cache:
            self._provider_cache[cache_key] = provider

        logger.info(f"Created LLM provider for model: {model}")
        return provider

    def _get_default_model(self) -> str:
        """Get the default model based on configuration."""
        default_provider = settings.llm.default_provider

        # Check for available API keys and prefer providers that have keys
        if settings.llm.anthropic_api_key and default_provider == "anthropic":
            return settings.llm.anthropic_model
        elif settings.llm.openai_api_key and default_provider == "openai":
            return settings.llm.openai_model
        elif settings.llm.deepseek_api_key and default_provider == "deepseek":
            return settings.llm.deepseek_model
        elif settings.llm.local_model_endpoint and default_provider == "local":
            return settings.llm.local_model_name
        elif settings.llm.anthropic_api_key:
            return settings.llm.anthropic_model
        elif settings.llm.openai_api_key:
            return settings.llm.openai_model
        elif settings.llm.deepseek_api_key:
            return settings.llm.deepseek_model
        else:
            # No API keys configured, raise helpful error
            raise LLMError(
                "No LLM provider API keys configured. Please set one of:\n"
                "- OPENAI_API_KEY for OpenAI models\n"
                "- ANTHROPIC_API_KEY for Anthropic models\n"
                "- DEEPSEEK_API_KEY for DeepSeek models\n"
                "- LOCAL_MODEL_ENDPOINT for local models\n"
                "Or run with --model <model_name> to specify a model explicitly."
            )

    def _create_provider(
        self,
        config: LLMConfig,
        provider_type: Optional[str] = None
    ) -> BaseLLM:
        """Create a specific provider instance.

        Args:
            config: LLM configuration
            provider_type: Optional provider type override

        Returns:
            BaseLLM instance

        Raises:
            LLMError: If provider creation fails
        """
        # For now, we use LiteLLM as the universal provider
        # In the future, we could add provider-specific implementations
        try:
            return LiteLLMProvider(config)
        except Exception as e:
            raise LLMError(f"Failed to create LLM provider: {e}")

    def get_available_models(self) -> Dict[str, Any]:
        """Get list of available models and their capabilities.

        Returns:
            Dictionary of model information
        """
        models = {}
        for model_info in self._model_config_manager.list_models():
            models[model_info.name] = {
                "provider": model_info.provider.value,
                "capabilities": [cap.value for cap in model_info.capabilities],
                "max_tokens": model_info.max_tokens,
                "context_window": model_info.context_window,
                "supports_streaming": model_info.supports_streaming,
                "supports_tools": model_info.supports_tools,
                "description": model_info.description,
                "cost_per_1k_input": model_info.cost_per_1k_input,
                "cost_per_1k_output": model_info.cost_per_1k_output,
            }
        return models

    def validate_model(self, model: str) -> bool:
        """Validate that a model is available and accessible.

        Args:
            model: Model name to validate

        Returns:
            True if model is valid and accessible
        """
        try:
            llm = self.create_llm(model, use_cache=False)
            # Run validation in a background task to avoid blocking
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(llm.validate_model())
                return result
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Model validation failed for {model}: {e}")
            return False

    def clear_cache(self):
        """Clear the provider cache."""
        self._provider_cache.clear()
        logger.info("LLM provider cache cleared")

    def get_recommended_model(
        self,
        task_type: str = "general",
        max_cost: Optional[float] = None
    ) -> str:
        """Get recommended model for a specific task type.

        Args:
            task_type: Type of task ("code", "general", "analysis", "fast")
            max_cost: Maximum cost constraint

        Returns:
            Recommended model name
        """
        if task_type == "code":
            # Prioritize code-capable models
            candidates = [
                "gpt-4-turbo-preview",
                "claude-3-sonnet-20240229",
                "gpt-4",
                "deepseek-coder",
                "codellama"
            ]
        elif task_type == "fast":
            # Prioritize fast, cheaper models
            candidates = [
                "gpt-3.5-turbo",
                "claude-3-haiku-20240307",
                "llama2"
            ]
        elif task_type == "analysis":
            # Prioritize capable reasoning models
            candidates = [
                "gpt-4-turbo-preview",
                "claude-3-opus-20240229",
                "gpt-4",
                "claude-3-sonnet-20240229"
            ]
        else:
            # General purpose
            candidates = [
                "gpt-4-turbo-preview",
                "claude-3-sonnet-20240229",
                "gpt-3.5-turbo"
            ]

        # Filter by cost if specified
        if max_cost:
            filtered_candidates = []
            for model in candidates:
                model_info = self._model_config_manager.get_model_info(model)
                if model_info and (
                    model_info.cost_per_1k_input is None or
                    model_info.cost_per_1k_input <= max_cost
                ):
                    filtered_candidates.append(model)
            candidates = filtered_candidates

        # Return first available candidate
        for model in candidates:
            if self._model_config_manager.get_model_info(model):
                return model

        # Fallback to default
        return self._get_default_model()


# Global LLM factory instance
llm_factory = LLMFactory()