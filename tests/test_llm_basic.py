"""
Basic tests for LLM abstraction layer.
"""
import pytest
from unittest.mock import Mock, patch
from src.core.llm import (
    LLMMessage, LLMResponse, LLMConfig, ModelCapability,
    create_llm, get_available_models, model_config_manager
)


def test_llm_message_creation():
    """Test LLMMessage creation."""
    message = LLMMessage(role="user", content="Hello, world!")
    assert message.role == "user"
    assert message.content == "Hello, world!"
    assert message.name is None
    assert message.tool_calls is None


def test_llm_config_creation():
    """Test LLMConfig creation."""
    config = LLMConfig(
        model="gpt-3.5-turbo",
        max_tokens=2048,
        temperature=0.5
    )
    assert config.model == "gpt-3.5-turbo"
    assert config.max_tokens == 2048
    assert config.temperature == 0.5
    assert config.timeout == 30  # default


def test_model_config_manager():
    """Test model configuration manager."""
    # Test getting model info
    gpt4_info = model_config_manager.get_model_info("gpt-4-turbo-preview")
    assert gpt4_info is not None
    assert gpt4_info.name == "gpt-4-turbo-preview"
    assert ModelCapability.CODE_GENERATION in gpt4_info.capabilities

    # Test listing models
    all_models = model_config_manager.list_models()
    assert len(all_models) > 0

    # Test filtering by capability
    code_models = model_config_manager.list_models(
        capability=ModelCapability.CODE_GENERATION
    )
    assert len(code_models) > 0
    for model in code_models:
        assert ModelCapability.CODE_GENERATION in model.capabilities


def test_get_available_models():
    """Test getting available models."""
    models = get_available_models()
    assert isinstance(models, dict)
    assert len(models) > 0

    # Check that each model has required fields
    for model_name, info in models.items():
        assert "provider" in info
        assert "capabilities" in info
        assert "max_tokens" in info


@pytest.mark.skipif(
    True,  # Skip by default since it requires API keys
    reason="Requires API keys and network access"
)
def test_create_llm_integration():
    """Integration test for LLM creation (requires API keys)."""
    # This would test actual LLM creation
    llm = create_llm("gpt-3.5-turbo")
    assert llm is not None
    assert llm.config.model == "gpt-3.5-turbo"


def test_create_llm_config_from_manager():
    """Test creating LLM config from model manager."""
    config = model_config_manager.create_llm_config(
        "gpt-3.5-turbo",
        temperature=0.8,
        max_tokens=1024
    )
    assert config.model == "gpt-3.5-turbo"
    assert config.temperature == 0.8
    assert config.max_tokens == 1024


def test_model_capability_validation():
    """Test model capability validation."""
    # Test valid model with code generation
    assert model_config_manager.validate_model_capability(
        "gpt-4-turbo-preview",
        ModelCapability.CODE_GENERATION
    )

    # Test model without specific capability
    assert not model_config_manager.validate_model_capability(
        "claude-3-haiku-20240307",
        ModelCapability.CODE_REVIEW  # Haiku doesn't have code review in our config
    )

    # Test non-existent model
    assert not model_config_manager.validate_model_capability(
        "non-existent-model",
        ModelCapability.CHAT
    )