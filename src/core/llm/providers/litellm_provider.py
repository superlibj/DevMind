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

        # Drop unsupported parameters for different providers
        litellm.drop_params = True

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
        if "deepseek" in model.lower() and "/" not in model:
            # Handle various Deepseek model name formats
            if model.startswith("deepseek-"):
                return f"deepseek/{model}"
            else:
                # Handle cases like "deepseek-chat" or just "deepseek"
                return f"deepseek/{model}"

        # Check model provider type from config
        model_info = self._model_config_manager.get_model_info(model)
        if model_info:
            if model_info.provider.value == "ollama":
                # Ollama models need provider prefix for LiteLLM
                return f"ollama/{model}"
            elif model_info.provider.value == "llama_cpp":
                # llama.cpp uses OpenAI-compatible API, use openai/ prefix
                # Use generic model name for llama.cpp (user loads whatever model they want)
                return "openai/local"

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

        # Add local endpoint configuration for Ollama and llama.cpp
        model_info = self._model_config_manager.get_model_info(config.model)
        if model_info:
            if model_info.provider.value == "ollama":
                # Default Ollama endpoint
                params["api_base"] = "http://localhost:11434"
            elif model_info.provider.value == "llama_cpp":
                # Default llama.cpp endpoint - OpenAI compatible
                params["api_base"] = "http://localhost:8080/v1"
                params["api_key"] = "sk-dummy"  # llama.cpp requires dummy API key for OpenAI compatibility

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

        # Handle server infrastructure errors (504 Gateway Timeout, CloudFront errors)
        if any(indicator in error_message.lower() for indicator in ["504 gateway timeout", "cloudfront", "<!doctype html"]):
            logger.warning(f"Server infrastructure error for {self.config.model}: {error_message[:200]}...")

            if "deepseek" in self.config.model.lower():
                friendly_error = """🚨 Deepseek API Infrastructure Issue

The Deepseek API servers are currently experiencing problems:
• 504 Gateway Timeout - Their servers are overloaded or down
• This is a temporary infrastructure issue on Deepseek's side
• Not related to your code or configuration

🔄 Immediate Solutions:
1. Switch models: `/model gpt-3.5-turbo` or `/model claude-3-sonnet-20240229`
2. Try again in 15-30 minutes when their servers recover
3. Check Deepseek status: https://platform.deepseek.com

The issue should resolve automatically when Deepseek fixes their infrastructure."""

            else:
                friendly_error = f"Server infrastructure error for {self.config.model}. The API service is temporarily unavailable. Try switching to a different model or retry later."

            return LLMError(friendly_error, self.provider_name, self.config.model)

        # Handle Deepseek-specific JSON parsing errors
        if "deepseekexception" in error_message.lower() and "unable to get json response" in error_message.lower():
            logger.warning(f"Deepseek JSON parsing error for model {self.config.model}: {error_message}")

            # Extract more details from the error
            if "Original Response:" in error_message:
                response_part = error_message.split("Original Response:")[-1].strip()
                if not response_part or response_part == "":
                    error_details = "Deepseek API returned empty response. This may be due to rate limiting, API quota exceeded, or temporary service issues."
                else:
                    error_details = f"Deepseek API returned non-JSON response: {response_part[:100]}..."
            else:
                error_details = "Deepseek API response could not be parsed as JSON."

            return LLMError(
                f"{error_details} Try switching to a different model or check your Deepseek API status.",
                self.provider_name,
                self.config.model
            )

        # Handle network and connection errors
        if any(indicator in error_message.lower() for indicator in ["connection error", "network", "dns", "502 bad gateway", "503 service unavailable"]):
            return LLMError(
                f"Network/connection error with {self.config.model} API. Check your internet connection and try again, or switch to a different model.",
                self.provider_name,
                self.config.model
            )

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

        # Special handling for Deepseek models
        is_deepseek = "deepseek" in config.model.lower()
        max_retries = 3 if is_deepseek else 1

        for attempt in range(max_retries):
            try:
                litellm_messages = self._convert_messages(messages)
                params = self._build_litellm_params(config)

                # Add Deepseek-specific parameters
                if is_deepseek:
                    # Ensure proper model mapping for Deepseek
                    if not params["model"].startswith("deepseek/"):
                        params["model"] = f"deepseek/{config.model}"

                    # Use user's timeout for Deepseek (minimum 60s for stability)
                    user_timeout = params.get("timeout", 60)
                    params["timeout"] = max(user_timeout, 60) if user_timeout < 600 else user_timeout

                logger.debug(f"Making LiteLLM request with model: {params['model']} (attempt {attempt + 1}/{max_retries})")
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
                error_message = str(e).lower()

                # Check if this is a Deepseek JSON parsing error that we might retry
                is_retryable_deepseek_error = (
                    is_deepseek and
                    "unable to get json response" in error_message and
                    attempt < max_retries - 1
                )

                if is_retryable_deepseek_error:
                    logger.warning(f"Deepseek JSON parsing error on attempt {attempt + 1}, retrying in {attempt + 1} seconds...")
                    await asyncio.sleep(attempt + 1)  # Progressive backoff
                    continue
                else:
                    logger.error(f"LiteLLM generation error: {e}")
                    raise self._handle_litellm_error(e)

        # This should never be reached due to the exception handling above
        raise LLMError("Maximum retries exceeded", self.provider_name, config.model)

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

    def diagnose_deepseek_issues(self) -> Dict[str, Any]:
        """Diagnose common Deepseek API issues and provide troubleshooting info."""
        import os

        diagnosis = {
            "model": self.config.model,
            "mapped_model": self._map_model_name(self.config.model),
            "issues": [],
            "suggestions": []
        }

        # Check API key
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        if not deepseek_key:
            diagnosis["issues"].append("No DEEPSEEK_API_KEY environment variable found")
            diagnosis["suggestions"].append("Set your Deepseek API key: export DEEPSEEK_API_KEY=your_key_here")

        # Check model name format
        if "deepseek" in self.config.model.lower() and "/" not in self.config.model:
            if not self._map_model_name(self.config.model).startswith("deepseek/"):
                diagnosis["issues"].append("Model name may not be properly formatted for LiteLLM")
                diagnosis["suggestions"].append(f"Try using model name: deepseek/{self.config.model}")

        # Check common issues
        diagnosis["common_solutions"] = [
            "Verify your Deepseek API key is valid and has quota remaining",
            "Check if the Deepseek service is currently available",
            "Try switching to a different model temporarily: gpt-3.5-turbo or claude-3-sonnet-20240229",
            "Ensure your internet connection is stable",
            "Check Deepseek API status at https://platform.deepseek.com"
        ]

        return diagnosis


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
        elif "deepseek" in model.lower():
            os.environ["DEEPSEEK_API_KEY"] = api_key

    config = LLMConfig(model=model, **config_kwargs)
    return LiteLLMProvider(config)