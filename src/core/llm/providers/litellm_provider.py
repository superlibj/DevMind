"""
Universal LLM provider using LiteLLM for 100+ model support.
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
import json
import time

try:
    import litellm
    from litellm import completion, acompletion, token_counter
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

from ..base_llm import (
    BaseLLM, LLMMessage, LLMResponse, LLMConfig, ModelCapability,
    LLMError, LLMTimeoutError, LLMRateLimitError, LLMAuthenticationError,
    LLMModelNotFoundError
)
from ..model_config import ModelConfigManager, ProviderType


logger = logging.getLogger(__name__)


class LiteLLMProvider(BaseLLM):
    """Universal LLM provider using LiteLLM."""

    def __init__(self, config: LLMConfig):
        """Initialize the LiteLLM provider.

        Args:
            config: LLM configuration

        Raises:
            RuntimeError: If LiteLLM is not available
        """
        if not LITELLM_AVAILABLE:
            raise RuntimeError(
                "LiteLLM is not available. Please install with: pip install litellm"
            )

        super().__init__(config)
        self._model_config_manager = ModelConfigManager()
        self._setup_litellm()

    def _setup_litellm(self):
        """Setup LiteLLM configuration."""
        # Set LiteLLM logging level
        litellm.set_verbose = logger.isEnabledFor(logging.DEBUG)

        # Configure rate limiting and retries
        litellm.num_retries = 3
        litellm.request_timeout = self.config.timeout

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "litellm"

    @property
    def supported_capabilities(self) -> List[ModelCapability]:
        """Return supported capabilities."""
        model_info = self._model_config_manager.get_model_info(self.config.model)
        if model_info:
            return model_info.capabilities
        # Default capabilities if model not in registry
        return [
            ModelCapability.CHAT,
            ModelCapability.CODE_GENERATION,
            ModelCapability.COMPLETION
        ]

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage objects to LiteLLM format."""
        converted = []
        for msg in messages:
            litellm_msg = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.name:
                litellm_msg["name"] = msg.name
            if msg.tool_calls:
                litellm_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                litellm_msg["tool_call_id"] = msg.tool_call_id
            converted.append(litellm_msg)
        return converted

    def _convert_response(self, response: Any) -> LLMResponse:
        """Convert LiteLLM response to LLMResponse."""
        choice = response.choices[0]

        # Extract tool calls if present
        tool_calls = None
        if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
            tool_calls = []
            for tool_call in choice.message.tool_calls:
                tool_calls.append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if response.usage else None,
            finish_reason=choice.finish_reason,
            tool_calls=tool_calls,
            metadata={
                "response_time": getattr(response, '_response_ms', None),
                "provider": self._get_provider_from_model(response.model)
            }
        )

    def _get_provider_from_model(self, model: str) -> str:
        """Extract provider name from model string."""
        if "/" in model:
            return model.split("/")[0]

        # Common provider prefixes
        if model.startswith("gpt-"):
            return "openai"
        elif model.startswith("claude-"):
            return "anthropic"
        elif model.startswith("gemini-"):
            return "google"
        elif model.startswith("deepseek-"):
            return "deepseek"
        else:
            return "unknown"

    def _map_model_name(self, model: str) -> str:
        """Map user-friendly model names to LiteLLM-specific names."""
        # DeepSeek models need provider prefix for LiteLLM
        if model.startswith("deepseek-") and "/" not in model:
            return f"deepseek/{model}"

        # Other models pass through unchanged
        return model

    def _build_litellm_params(self, config: LLMConfig) -> Dict[str, Any]:
        """Build parameters for LiteLLM API call."""
        params = {
            "model": self._map_model_name(config.model),
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            "timeout": config.timeout,
            "stream": config.stream,
        }

        # Add stop sequences if provided
        if config.stop:
            params["stop"] = config.stop

        # Add tools if provided
        if config.tools:
            params["tools"] = config.tools
            if config.tool_choice:
                params["tool_choice"] = config.tool_choice

        return params

    def _handle_litellm_error(self, error: Exception) -> LLMError:
        """Convert LiteLLM errors to our error types."""
        error_message = str(error)

        if "timeout" in error_message.lower():
            return LLMTimeoutError(error_message, self.provider_name, self.config.model)
        elif "rate limit" in error_message.lower() or "429" in error_message:
            return LLMRateLimitError(error_message, self.provider_name, self.config.model)
        elif "unauthorized" in error_message.lower() or "401" in error_message:
            return LLMAuthenticationError(error_message, self.provider_name, self.config.model)
        elif "not found" in error_message.lower() or "404" in error_message:
            return LLMModelNotFoundError(error_message, self.provider_name, self.config.model)
        else:
            return LLMError(error_message, self.provider_name, self.config.model)

    async def generate(
        self,
        messages: List[LLMMessage],
        config_override: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        config = config_override or self.config

        try:
            litellm_messages = self._convert_messages(messages)
            params = self._build_litellm_params(config)

            logger.debug(f"Making LiteLLM request with model: {config.model}")
            start_time = time.time()

            response = await acompletion(
                messages=litellm_messages,
                **params
            )

            response_time = (time.time() - start_time) * 1000
            response._response_ms = response_time

            logger.debug(f"LiteLLM response received in {response_time:.2f}ms")
            return self._convert_response(response)

        except Exception as e:
            logger.error(f"LiteLLM generation error: {e}")
            raise self._handle_litellm_error(e)

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        config_override: Optional[LLMConfig] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM."""
        config = config_override or self.config
        stream_config = config
        stream_config.stream = True

        try:
            litellm_messages = self._convert_messages(messages)
            params = self._build_litellm_params(stream_config)

            logger.debug(f"Making streaming LiteLLM request with model: {config.model}")

            response = await acompletion(
                messages=litellm_messages,
                **params
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"LiteLLM streaming error: {e}")
            raise self._handle_litellm_error(e)

    async def count_tokens(self, messages: List[LLMMessage]) -> int:
        """Count tokens in the messages."""
        try:
            litellm_messages = self._convert_messages(messages)
            return await asyncio.get_event_loop().run_in_executor(
                None,
                token_counter,
                self.config.model,
                litellm_messages
            )
        except Exception as e:
            logger.warning(f"Token counting failed: {e}")
            # Fallback to approximate counting
            total_chars = sum(len(msg.content) for msg in messages)
            return int(total_chars / 4)  # Rough approximation

    async def validate_model(self) -> bool:
        """Validate that the model is accessible."""
        try:
            test_messages = [
                LLMMessage(role="user", content="Hello")
            ]

            # Create a minimal config for testing
            test_config = LLMConfig(
                model=self.config.model,
                max_tokens=10,
                temperature=0,
                timeout=10
            )

            response = await self.generate(test_messages, test_config)
            return response.content is not None

        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return False

    async def _load_model_info(self) -> None:
        """Load model information."""
        model_info = self._model_config_manager.get_model_info(self.config.model)

        if model_info:
            self._model_info = {
                "name": model_info.name,
                "provider": model_info.provider.value,
                "max_tokens": model_info.max_tokens,
                "context_window": model_info.context_window,
                "capabilities": [cap.value for cap in model_info.capabilities],
                "supports_streaming": model_info.supports_streaming,
                "supports_tools": model_info.supports_tools,
                "description": model_info.description,
                "cost_per_1k_input": model_info.cost_per_1k_input,
                "cost_per_1k_output": model_info.cost_per_1k_output,
            }
        else:
            # Try to get basic info from LiteLLM
            self._model_info = {
                "name": self.config.model,
                "provider": self._get_provider_from_model(self.config.model),
                "max_tokens": self.config.max_tokens,
                "context_window": "unknown",
                "capabilities": [cap.value for cap in self.supported_capabilities],
                "supports_streaming": True,
                "supports_tools": False,
                "description": f"Model {self.config.model} via LiteLLM",
            }


# Convenience function to create a LiteLLM provider
def create_litellm_provider(
    model: str,
    api_key: Optional[str] = None,
    **config_kwargs
) -> LiteLLMProvider:
    """Create a LiteLLM provider instance.

    Args:
        model: The model name
        api_key: Optional API key (will be set as environment variable)
        **config_kwargs: Additional configuration parameters

    Returns:
        LiteLLMProvider instance
    """
    if api_key:
        import os
        # Set API key based on provider
        if model.startswith("gpt-") or "openai" in model:
            os.environ["OPENAI_API_KEY"] = api_key
        elif model.startswith("claude-") or "anthropic" in model:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        elif "gemini" in model or "google" in model:
            os.environ["GOOGLE_API_KEY"] = api_key

    config = LLMConfig(model=model, **config_kwargs)
    return LiteLLMProvider(config)