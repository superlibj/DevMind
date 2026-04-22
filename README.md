# DevMind - Interactive AI Development Assistant

A powerful CLI-based AI development assistant that provides intelligent code generation, debugging, and development support with integrated weather and location services.

## 🚀 Features

### Core Capabilities
- **Interactive CLI Interface**: Rich terminal experience with streaming responses and syntax highlighting
- **Multi-Model LLM Support**: OpenAI, Anthropic Claude, DeepSeek, and local models via Ollama
- **Intelligent Code Assistant**: Code generation, review, debugging, and refactoring
- **Development Tools Integration**: Git operations, file management, and system commands
- **Session Management**: Persistent conversations with save/load functionality

### Enhanced Services
- **Weather Integration**: Real-time weather forecasts and conditions
- **Location Services**: IP geolocation and location-based queries
- **Streaming Real-time Responses**: Live conversation with progress indicators
- **Token Usage Tracking**: Cost monitoring and usage statistics

## 🎯 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd aiagent

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Basic Usage

```bash
# Start DevMind
python main.py

# Start with specific model
python main.py --model claude-3-sonnet-20240229

# Start with local model
python main.py --model qwen2.5-coder:7b

# Show available models
python main.py --list-models
```

## 🔧 Configuration

Create a `.env` file with your API keys:

```bash
# LLM Provider API Keys
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here

# Default Settings
DEFAULT_LLM_PROVIDER=local
LOCAL_MODEL_NAME=qwen2.5-coder:7b
LOCAL_MODEL_ENDPOINT=http://localhost:11434

# CLI Preferences
CLI_STREAM_RESPONSES=true
CLI_AUTO_SAVE=true
CLI_SYNTAX_HIGHLIGHTING=true
```

## 💻 Interactive Commands

### Session Management
```bash
/save project-name "Description"    # Save current session
/load project-name                  # Load saved session
/sessions                          # List all sessions
/clear                            # Clear current conversation
```

### Model Management
```bash
/model claude-3-sonnet-20240229    # Switch to Claude
/model qwen2.5-coder:7b           # Switch to local model
/models                           # List available models
```

### Development Tools
```bash
/tokens                           # Show token usage
/help                            # Show help information
/exit                            # Exit DevMind
```

## 🌍 Weather & Location Features

DevMind includes integrated weather and location services:

```bash
# Weather queries
what's the weather like today?
what's the forecast for tomorrow?
how's the weather in Tokyo?

# Location queries
where am I located?
what's my current location?
```

## 🤖 Supported Models

### Cloud Models
- **OpenAI**: GPT-4, GPT-3.5-turbo, GPT-4-turbo
- **Anthropic**: Claude-3 Opus, Sonnet, Haiku
- **DeepSeek**: DeepSeek-Chat, DeepSeek-Coder

### Local Models (via Ollama)
- **Code-Specialized**: qwen2.5-coder, codellama, deepseek-coder
- **General Purpose**: llama3.2, mistral, phi3

## 📁 Project Structure

```
aiagent/
├── main.py                 # CLI entry point
├── src/
│   ├── cli/               # CLI interface components
│   │   ├── repl.py       # Interactive REPL
│   │   ├── streaming_agent.py  # Streaming responses
│   │   └── session_manager.py  # Session persistence
│   ├── core/              # Core AI logic
│   │   ├── agent/        # ReAct agent implementation
│   │   ├── llm/          # Multi-LLM abstraction
│   │   ├── security/     # Input validation and safety
│   │   └── tools/        # Development tools integration
│   └── domain/           # Business logic services
├── config/               # Configuration management
├── docs/                 # Documentation
└── tests/               # Test suite
```

## 🛠 Development Tools

DevMind integrates with essential development tools:

### File Operations
- Read, write, edit files with syntax highlighting
- Glob pattern matching and content search
- Directory operations and file management

### Git Integration
- Repository operations and status checking
- Smart commit suggestions and PR creation
- Branch management and merge conflict resolution

### Code Analysis
- Syntax validation and error detection
- Code review and optimization suggestions
- Security scanning and vulnerability detection

## 🌐 Web Services Integration

### Weather Services
- Real-time weather data via Open-Meteo API
- Location-based forecasts and conditions
- Multi-day forecasts and weather alerts

### Location Services
- IP-based geolocation detection
- Geocoding and reverse geocoding
- Location-aware weather queries

## 📊 Token Usage & Cost Tracking

Monitor your LLM usage in real-time:

```bash
# Real-time display during usage
📊 Tokens: 1,245 (prompt: 850, completion: 395) | Cost: $0.002340 | Model: claude-3-sonnet

# Session summary
╭─ Session Summary ────────────────────────────────────╮
│ Duration       │ 15.3 minutes                        │
│ Total Requests │ 12                                  │
│ Total Tokens   │ 15,420                             │
│ Total Cost     │ $0.028560                          │
╰──────────────────────────────────────────────────────╯
```

## 🔒 Security Features

- **Input Validation**: Comprehensive sanitization of all inputs
- **Code Safety**: Automatic security scanning of generated code
- **Sandboxed Execution**: Safe execution environment for code operations
- **API Key Protection**: Secure credential management

## 🧪 Testing

```bash
# Run test suite
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src

# Test specific components
python -m pytest tests/cli/
python -m pytest tests/core/
```

## 🚀 Deployment Options

### Local Development
```bash
python main.py
```

### Docker (Optional)
```bash
docker-compose up -d
```

### Local Model Setup
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull qwen2.5-coder:7b
ollama pull codellama
```

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [Configuration Options](docs/configuration.md)
- [Local Models Setup](docs/local-models.md)
- [API Reference](docs/api-reference.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [LiteLLM](https://github.com/BerriAI/litellm) for multi-provider LLM support
- [Ollama](https://ollama.com/) for local model hosting
- Weather data provided by [Open-Meteo](https://open-meteo.com/)