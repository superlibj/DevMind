# DevMind Interactive Development Assistant - CLI Edition

A powerful DevMind-like interactive development assistant that works as a CLI tool directly integrated with your development environment.

## 🚀 Features

- **Interactive REPL**: Terminal-based interface with Rich-powered output formatting
- **Streaming Responses**: Real-time conversation with progress indicators
- **Multi-Model Support**: OpenAI, Anthropic Claude, and **DeepSeek** models
- **Session Management**: Persistent conversations across CLI sessions
- **Direct Tool Integration**: File operations, git commands, code analysis
- **Syntax Highlighting**: Beautiful code display with multiple themes
- **Multi-line Input**: Support for complex code input with ```

## 🏗 Architecture

This CLI application transforms the existing web API service into an interactive terminal experience:

- **CLI Interface** (`/src/cli/`): Rich terminal interface with REPL
- **Streaming Agent** (`StreamingReActAgent`): Real-time ReAct pattern execution
- **Session Persistence**: JSON-based conversation storage
- **Model Abstraction**: Unified interface for multiple LLM providers

## 📦 Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd aiagent

# Install in development mode
pip install -e .

# Or install with all optional dependencies
pip install -e ".[all]"
```

### Dependencies

**Core Requirements:**
- typer>=0.9.0 - CLI framework
- rich>=13.7.0 - Terminal interface
- litellm>=1.21.0 - Multi-LLM provider support
- anthropic>=0.7.0 - Claude models
- openai>=1.6.0 - GPT models

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# LLM Provider API Keys
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here

# Default Model Settings
CLI_DEFAULT_PROVIDER=anthropic
CLI_DEFAULT_MODEL=claude-3-sonnet-20240229
CLI_TEMPERATURE=0.1
CLI_MAX_TOKENS=4096

# CLI Preferences
CLI_SESSIONS_DIR=./sessions
CLI_AUTO_SAVE=true
CLI_SYNTAX_HIGHLIGHTING=true
CLI_STREAM_RESPONSES=true
```

### CLI Configuration

The CLI behavior can be customized through environment variables or by modifying `config/cli_config.py`.

## 🎯 Usage

### Starting DevMind

```bash
# Basic start
devmind

# Start with specific model
devmind --model deepseek-chat

# Load a specific session
devmind --session my-project

# List available models
devmind --list-models

# Show help
devmind --help
```

### Interactive Commands

Once in the REPL, you can use these special commands:

#### Session Management
```bash
/save project-name "Optional description"    # Save current conversation
/load project-name                           # Load saved session
/sessions                                   # List all sessions
/delete session-name                        # Delete a session
/export project-name ./output.md markdown   # Export session
```

#### Model Management
```bash
/model deepseek-chat              # Switch to DeepSeek Chat
/model claude-3-sonnet-20240229   # Switch to Claude Sonnet
/model gpt-4-turbo-preview        # Switch to GPT-4 Turbo
/models                           # List all available models
/models deepseek                  # List DeepSeek models only
```

#### Conversation
```bash
/clear      # Clear current conversation
/status     # Show conversation status
/help       # Show detailed help
/exit       # Exit DevMind
```

### Multi-line Input

Use triple backticks for multi-line code input:

```
claude> ```
... def fibonacci(n):
...     if n <= 1:
...         return n
...     return fibonacci(n-1) + fibonacci(n-2)
... ```
```

## 🤖 Supported Models

### OpenAI Models
- `gpt-4-turbo-preview` - Latest GPT-4 with extended context
- `gpt-4` - Standard GPT-4 model
- `gpt-3.5-turbo` - Fast and efficient model

### Anthropic Claude Models
- `claude-3-opus-20240229` - Most capable Claude model
- `claude-3-sonnet-20240229` - Balanced performance and cost
- `claude-3-haiku-20240307` - Fastest Claude model

### DeepSeek Models ⭐
- `deepseek-chat` - General conversation and coding
- `deepseek-coder` - Specialized for code generation
- `deepseek-coder-v2` - Advanced coding with extended context

### Local Models (via Ollama)
- `codellama` - Code Llama for programming
- `llama2` - Llama 2 base model

## 💡 Example Usage

### Starting a New Project

```bash
$ devmind
Welcome to DevMind! 🚀

claude> I'm starting a new Python web API project. Can you help me set up FastAPI with authentication?

💭 I'll help you create a FastAPI project with authentication. Let me start by creating the project structure and core files.

🔧 Executing file_create(filename="main.py", content="...")
✓ file_create completed

🔧 Executing file_create(filename="auth.py", content="...")
✓ file_create completed

[Displays created files with syntax highlighting...]

claude> /save fastapi-auth-project "FastAPI project with JWT authentication"
✓ Session saved as 'fastapi-auth-project'
```

### Working with DeepSeek

```bash
claude> /model deepseek-coder-v2
✓ Switched to deepseek-coder-v2
Provider: deepseek
Description: DeepSeek Coder V2 - Advanced coding with extended context and tool calling

claude> Can you review this React component for performance issues?

```
function UserList({ users }) {
  return (
    <div>
      {users.map(user => (
        <div key={user.id}>
          <UserCard user={user} />
        </div>
      ))}
    </div>
  );
}
```

💭 Analyzing the React component for potential performance issues...

[DeepSeek provides detailed performance analysis...]
```

### Session Management

```bash
claude> /sessions
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                   ┃ Messages ┃ Model          ┃ Last Accessed    ┃ Description             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ fastapi-auth-project   │ 12       │ claude-3-sonnet│ 2024-04-18 14:30│ FastAPI with JWT auth   │
│ react-performance      │ 8        │ deepseek-coder │ 2024-04-18 10:15│ React optimization tips │
│ python-algorithms      │ 15       │ gpt-4-turbo    │ 2024-04-17 16:45│ Algorithm implementations│
└────────────────────────┴──────────┴────────────────┴──────────────────┴─────────────────────────┘

claude> /load react-performance
✓ Session 'react-performance' loaded
```

## 🛠 Development

### Running from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Run directly
python main.py

# Run with specific model
python main.py --model deepseek-chat
```

### Testing

```bash
# Run tests
pytest tests/

# Test CLI components specifically
pytest tests/cli/

# Test with coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/
```

## 🔧 Troubleshooting

### Common Issues

**1. Model not found error:**
```bash
devmind --list-models  # Check available models
```

**2. API key issues:**
```bash
# Check your .env file has the correct API keys
# Verify API key permissions and quotas
```

**3. Session loading failures:**
```bash
claude> /sessions  # Check if session exists
# Sessions are stored in ./sessions/ directory
```

**4. Import errors:**
```bash
# Make sure you've installed the package
pip install -e .
# Or install missing dependencies
pip install -r requirements.txt
```

### Debug Mode

Run with debug logging:

```bash
devmind --debug
```

## 📋 Architecture Details

### File Structure
```
aiagent/ (devmind-cli)
├── main.py           # CLI entry point
├── src/
│   ├── cli/                      # CLI-specific components
│   │   ├── repl.py              # Interactive REPL interface
│   │   ├── streaming_agent.py   # Streaming ReAct wrapper
│   │   ├── command_parser.py    # Command parsing
│   │   ├── output_formatter.py  # Terminal output formatting
│   │   └── session_manager.py   # Session persistence
│   ├── core/                     # Core agent logic (reused)
│   │   ├── agent/               # ReAct agent implementation
│   │   ├── llm/                 # Multi-LLM abstraction
│   │   └── tools/               # Tool execution system
│   └── domain/                   # Business logic services
├── config/                       # Configuration management
├── sessions/                     # Saved conversation sessions
└── setup.py                      # Installation package
```

### Key Components

1. **StreamingReActAgent**: Wraps the existing ReAct agent with streaming capabilities
2. **CLIAgentInterface**: High-level interface for CLI interaction with Rich display
3. **SessionManager**: Handles conversation persistence and export
4. **OutputFormatter**: Rich terminal formatting with syntax highlighting
5. **CommandParser**: Special command handling (/help, /save, /model, etc.)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [Typer](https://typer.tiangolo.com/) for the CLI framework
- [LiteLLM](https://github.com/BerriAI/litellm) for multi-provider LLM support
- [DeepSeek](https://deepseek.com/) for advanced coding models
- Inspired by [DevMind](https://claude.com/devmind) by Anthropic