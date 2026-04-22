# DevMind Documentation

Welcome to the comprehensive documentation for DevMind, an interactive AI development assistant.

## 📚 Documentation Index

### Getting Started
- **[Installation Guide](installation.md)** - Complete installation instructions for all platforms
- **[Configuration Guide](configuration.md)** - Detailed configuration options and setup
- **[Local Models Setup](local-models.md)** - Guide for setting up local AI models with Ollama

### User Guides
- **[CLI Reference](cli-reference.md)** - Complete command-line interface documentation
- **[API Reference](api-reference.md)** - Detailed API documentation and integration guide
- **[Token Tracking](token-tracking.md)** - Understanding usage monitoring and cost tracking

### Support
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

## 🚀 Quick Navigation

### For New Users
1. Start with the [Installation Guide](installation.md)
2. Follow the [Configuration Guide](configuration.md) to set up API keys
3. Try the basic examples in the main [README](../README.md)

### For Local Model Users
1. Read the [Local Models Setup](local-models.md) guide
2. Install Ollama and download recommended models
3. Configure DevMind for local usage

### For Developers
1. Check the [API Reference](api-reference.md) for integration details
2. Review the [CLI Reference](cli-reference.md) for command usage
3. Study the project structure in the main [README](../README.md)

### For Troubleshooting
1. Consult the [Troubleshooting Guide](troubleshooting.md)
2. Enable debug mode: `python main.py --debug`
3. Check log files in the `logs/` directory

## 📋 Documentation Features

### Comprehensive Coverage
- **Installation**: Multiple platforms and installation methods
- **Configuration**: All environment variables and settings
- **Usage**: CLI commands, interactive features, and APIs
- **Models**: Cloud and local model setup and usage
- **Troubleshooting**: Common issues and solutions

### Practical Examples
- Real command-line examples with expected output
- Configuration snippets for different use cases
- Step-by-step procedures for complex setups

### Platform Support
- **Windows**: PowerShell and Command Prompt instructions
- **macOS**: Terminal and Homebrew setup
- **Linux**: Various distributions (Ubuntu, CentOS, Arch)
- **Docker**: Container-based deployment options

## 🔗 External Resources

### API Documentation
- [OpenAI API](https://platform.openai.com/docs)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [DeepSeek API](https://platform.deepseek.com/docs)

### Local Model Resources
- [Ollama Documentation](https://ollama.com/docs)
- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [Hugging Face Model Hub](https://huggingface.co/models)

### Development Tools
- [Rich Documentation](https://rich.readthedocs.io/) - Terminal formatting
- [LiteLLM](https://docs.litellm.ai/) - Multi-provider LLM support
- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html)

## 📝 Documentation Maintenance

This documentation is actively maintained and updated with:
- New feature additions
- Configuration changes
- Bug fixes and workarounds
- Community feedback and suggestions

### Contributing to Documentation
If you find errors or want to improve the documentation:
1. Check the issue tracker for existing documentation issues
2. Submit corrections or improvements via pull requests
3. Suggest new topics or clarifications

### Version Information
- **Last Updated**: Current version reflects DevMind v1.x
- **Compatibility**: Documentation covers all supported platforms
- **Update Frequency**: Updated with each major release

## 🎯 Quick Reference Cards

### Essential Commands
```bash
# Start DevMind
python main.py

# Show available models
python main.py --list-models

# Start with specific model
python main.py --model claude-3-sonnet-20240229

# Load session
python main.py --session project-name
```

### Interactive Commands
```bash
/help                    # Show help
/save project-name       # Save session
/load project-name       # Load session
/model claude-3-sonnet   # Switch model
/tokens                  # Show usage
/clear                   # Clear conversation
/exit                    # Exit DevMind
```

### Configuration Essentials
```bash
# .env file basics
ANTHROPIC_API_KEY=sk-ant-your_key
DEFAULT_LLM_PROVIDER=anthropic
CLI_STREAM_RESPONSES=true
CLI_AUTO_SAVE=true
```

This documentation provides everything you need to effectively use DevMind for AI-powered development assistance.