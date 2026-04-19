#!/usr/bin/env python3
"""
Basic test script for DevMind CLI implementation.

This script tests that the main components can be imported and initialized
without errors. Run this to verify the CLI setup is working.
"""
import sys
import traceback
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_imports():
    """Test that all main modules can be imported."""
    print("🧪 Testing imports...")

    try:
        # Test CLI module imports
        from src.cli.session_manager import SessionManager
        print("✅ SessionManager imported successfully")

        from src.cli.output_formatter import OutputFormatter
        print("✅ OutputFormatter imported successfully")

        from src.cli.command_parser import CommandParser
        print("✅ CommandParser imported successfully")

        from src.cli.streaming_agent import StreamingReActAgent, CLIAgentInterface
        print("✅ StreamingReActAgent imported successfully")

        from src.cli.repl import DevMindREPL
        print("✅ DevMindREPL imported successfully")

        # Test core module imports
        from src.core.llm.model_config import model_config_manager, ProviderType
        print("✅ Model config imported successfully")

        from src.core.agent.react_agent import ReActAgent
        print("✅ ReActAgent imported successfully")

        # Test config imports
        from config.cli_config import cli_config
        print("✅ CLI config imported successfully")

        print("🎉 All imports successful!")
        return True

    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False


def test_model_config():
    """Test model configuration and DeepSeek support."""
    print("\n🧪 Testing model configuration...")

    try:
        from src.core.llm.model_config import model_config_manager, ProviderType

        # Test that DeepSeek provider exists
        assert ProviderType.DEEPSEEK in ProviderType
        print("✅ DeepSeek provider type exists")

        # Test DeepSeek models
        deepseek_models = model_config_manager.list_models(provider=ProviderType.DEEPSEEK)
        assert len(deepseek_models) > 0
        print(f"✅ Found {len(deepseek_models)} DeepSeek models")

        for model in deepseek_models:
            print(f"   - {model.name}: {model.description}")

        # Test getting specific model
        deepseek_chat = model_config_manager.get_model_info("deepseek-chat")
        assert deepseek_chat is not None
        assert deepseek_chat.provider == ProviderType.DEEPSEEK
        print("✅ DeepSeek chat model configuration loaded")

        # Test all provider types
        all_models = list(model_config_manager._models.keys())
        print(f"✅ Total models available: {len(all_models)}")

        print("🎉 Model configuration test passed!")
        return True

    except Exception as e:
        print(f"❌ Model config error: {e}")
        traceback.print_exc()
        return False


def test_cli_components():
    """Test CLI component initialization."""
    print("\n🧪 Testing CLI component initialization...")

    try:
        from src.cli.session_manager import SessionManager
        from src.cli.output_formatter import OutputFormatter

        # Test SessionManager
        session_manager = SessionManager()
        print("✅ SessionManager initialized")

        # Test OutputFormatter
        formatter = OutputFormatter()
        print("✅ OutputFormatter initialized")

        # Test that sessions directory exists or can be created
        sessions_dir = session_manager.sessions_dir
        assert sessions_dir.exists() or sessions_dir.parent.exists()
        print(f"✅ Sessions directory: {sessions_dir}")

        print("🎉 CLI components test passed!")
        return True

    except Exception as e:
        print(f"❌ CLI components error: {e}")
        traceback.print_exc()
        return False


def test_main_entry_point():
    """Test that the main entry point loads without errors."""
    print("\n🧪 Testing main entry point...")

    try:
        import main
        print("✅ Main entry point module loaded")

        # Check that the typer app exists
        assert hasattr(main, 'app')
        print("✅ Typer app found")

        print("🎉 Main entry point test passed!")
        return True

    except Exception as e:
        print(f"❌ Main entry point error: {e}")
        traceback.print_exc()
        return False


def test_basic_functionality():
    """Test basic functionality without requiring API keys."""
    print("\n🧪 Testing basic functionality...")

    try:
        from src.cli.session_manager import SessionManager
        from src.cli.output_formatter import OutputFormatter
        from src.core.llm.model_config import model_config_manager, ProviderType

        # Test session manager basic operations
        session_manager = SessionManager()
        sessions = session_manager.list_sessions()
        print(f"✅ Found {len(sessions)} existing sessions")

        # Test output formatter with sample text
        formatter = OutputFormatter()
        print("✅ Output formatter ready")

        # Test model listing
        all_models = model_config_manager.list_models()
        openai_models = model_config_manager.list_models(provider=ProviderType.OPENAI)
        anthropic_models = model_config_manager.list_models(provider=ProviderType.ANTHROPIC)
        deepseek_models = model_config_manager.list_models(provider=ProviderType.DEEPSEEK)

        print(f"✅ Model counts - Total: {len(all_models)}, OpenAI: {len(openai_models)}, Anthropic: {len(anthropic_models)}, DeepSeek: {len(deepseek_models)}")

        print("🎉 Basic functionality test passed!")
        return True

    except Exception as e:
        print(f"❌ Basic functionality error: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🚀 Starting DevMind CLI Tests")
    print("=" * 50)

    tests = [
        test_imports,
        test_model_config,
        test_cli_components,
        test_main_entry_point,
        test_basic_functionality,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! DevMind CLI is ready to use.")
        print("\n🚀 To start DevMind:")
        print("   python main.py")
        print("   # or after installation:")
        print("   devmind")
    else:
        print("❌ Some tests failed. Please check the errors above.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)