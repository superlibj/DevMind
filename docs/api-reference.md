# API Reference

This document provides detailed information about DevMind's internal APIs, CLI commands, and integration capabilities.

## 🖥️ CLI Commands

### Main Command

```bash
python main.py [OPTIONS]
```

#### Global Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--help` | `-h` | Show help message | |
| `--version` | `-v` | Show version information | |
| `--model MODEL` | `-m` | Start with specific model | From config |
| `--provider PROVIDER` | `-p` | Use specific LLM provider | From config |
| `--debug` | `-d` | Enable debug logging | False |
| `--verbose` | | Extra verbose output | False |
| `--list-models` | | List all available models | |
| `--show-config` | | Display current configuration | |
| `--validate-config` | | Validate configuration | |
| `--test-apis` | | Test API connections | |
| `--session SESSION` | `-s` | Load specific session | |
| `--max-iterations N` | | Maximum ReAct iterations | 10 |
| `--timeout SECONDS` | `-t` | Request timeout | 60 |

#### Examples

```bash
# Start with Claude
python main.py --model claude-3-sonnet-20240229

# Start in debug mode
python main.py --debug --verbose

# Load specific session
python main.py --session my-project

# Quick model test
python main.py --model gpt-3.5-turbo --test-apis
```

## 🎯 Interactive Commands

### Session Management

#### `/save`
```bash
/save [SESSION_NAME] [DESCRIPTION]
```
Save the current conversation session.

**Parameters:**
- `SESSION_NAME` (optional): Name for the session
- `DESCRIPTION` (optional): Description of the session

**Examples:**
```bash
/save                              # Auto-generate name
/save my-project                   # Save with name
/save my-project "React app dev"   # Save with description
```

#### `/load`
```bash
/load SESSION_NAME
```
Load a previously saved session.

**Examples:**
```bash
/load my-project                   # Load specific session
/load                             # Show session picker
```

#### `/sessions`
```bash
/sessions [FILTER]
```
List all saved sessions.

**Parameters:**
- `FILTER` (optional): Filter sessions by name or description

**Examples:**
```bash
/sessions                         # List all sessions
/sessions react                   # Filter sessions containing "react"
```

#### `/delete`
```bash
/delete SESSION_NAME
```
Delete a saved session.

#### `/export`
```bash
/export SESSION_NAME [FILE] [FORMAT]
```
Export session to file.

**Parameters:**
- `SESSION_NAME`: Session to export
- `FILE` (optional): Output filename
- `FORMAT` (optional): Export format (markdown, json, txt)

**Examples:**
```bash
/export my-project                     # Export to auto-named file
/export my-project report.md markdown  # Export as markdown
/export my-project data.json json      # Export as JSON
```

### Model Management

#### `/model`
```bash
/model [MODEL_NAME]
```
Switch to a different model or show current model.

**Examples:**
```bash
/model                                 # Show current model
/model claude-3-sonnet-20240229       # Switch to Claude
/model gpt-4                          # Switch to GPT-4
/model qwen2.5-coder:7b               # Switch to local model
```

#### `/models`
```bash
/models [PROVIDER]
```
List available models.

**Parameters:**
- `PROVIDER` (optional): Filter by provider (openai, anthropic, local, etc.)

**Examples:**
```bash
/models                               # List all models
/models anthropic                     # List Claude models only
/models local                         # List local models only
```

### Utility Commands

#### `/help`
```bash
/help [TOPIC]
```
Show help information.

**Topics:**
- `commands`: List all available commands
- `models`: Information about model switching
- `sessions`: Session management help
- `weather`: Weather feature help

#### `/clear`
```bash
/clear
```
Clear the current conversation history.

#### `/tokens`
```bash
/tokens
```
Show token usage statistics for current session.

#### `/exit`
```bash
/exit
```
Exit DevMind.

## 🌍 Weather and Location APIs

### Weather Queries

DevMind recognizes natural language weather queries:

#### Current Weather
```
what's the weather?
what's the current weather?
how's the weather today?
```

#### Forecasts
```
what's the weather tomorrow?
what's the weather the day after tomorrow?
what's the forecast for this week?
```

#### Location-Specific
```
what's the weather in Tokyo?
how's the weather in London today?
what's the forecast for New York tomorrow?
```

### Location Queries

#### Current Location
```
where am I?
what's my current location?
what city am I in?
```

### Weather API Configuration

#### Environment Variables
```bash
# Service endpoints
WEATHER_API_BASE=https://api.open-meteo.com/v1
LOCATION_API_PRIMARY=https://ipapi.co/json/
LOCATION_API_FALLBACK=http://ip-api.com/json/

# Timeouts
WEATHER_TIMEOUT=30
LOCATION_TIMEOUT=30

# Cache settings
WEATHER_CACHE_DURATION=15
LOCATION_CACHE_DURATION=24
```

#### Response Format

Weather responses include:
- Current conditions (temperature, humidity, wind)
- Forecast data (next 7 days)
- Weather alerts (if any)
- Location information

## 🔧 Tool Integration API

### File Operations

#### Read Tool
Reads file contents with syntax highlighting support.

**Parameters:**
- `file_path`: Path to the file
- `encoding`: File encoding (default: utf-8)
- `max_lines`: Maximum lines to read

#### Write Tool
Creates or overwrites files with content.

**Parameters:**
- `file_path`: Output file path
- `content`: File content
- `encoding`: File encoding (default: utf-8)
- `create_dirs`: Create directories if needed

#### Edit Tool
Makes targeted edits to existing files.

**Parameters:**
- `file_path`: File to edit
- `old_text`: Text to replace
- `new_text`: Replacement text
- `line_number`: Specific line to edit (optional)

### Git Operations

#### Git Tool
Provides Git repository operations.

**Available Operations:**
- `status`: Get repository status
- `diff`: Show changes
- `add`: Stage files
- `commit`: Create commits
- `push`: Push changes
- `pull`: Pull updates
- `branch`: Branch management
- `log`: View history

**Parameters vary by operation**

### System Commands

#### Bash Tool
Executes system commands safely.

**Parameters:**
- `command`: Command to execute
- `working_dir`: Working directory
- `timeout`: Execution timeout
- `capture_output`: Capture stdout/stderr

**Security Notes:**
- Commands are executed in a sandboxed environment
- Dangerous commands are blocked
- Output is captured and sanitized

## 📊 Token Tracking API

### Real-time Statistics

DevMind automatically tracks:
- Prompt tokens
- Completion tokens
- Total tokens per request
- Cost calculation (when pricing data available)
- Cumulative session statistics

### Token Display Format

```
📊 Tokens: 1,245 (prompt: 850, completion: 395) | Cost: $0.002340 | Model: claude-3-sonnet
```

### Session Summary

```
╭─ Session Summary ────────────────────────────────────────────────╮
│ Duration       │ 15.3 minutes                                    │
│ Total Requests │ 12                                              │
│ Total Tokens   │ 15,420                                         │
│ Total Cost     │ $0.028560                                      │
╰─────────────────────────────────────────────────────────────────╯
```

## 🤖 Model Configuration API

### Supported Providers

#### OpenAI
- **Models**: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- **API Base**: https://api.openai.com/v1
- **Authentication**: API key header
- **Features**: Streaming, tool calling

#### Anthropic Claude
- **Models**: claude-3-opus, claude-3-sonnet, claude-3-haiku
- **API Base**: https://api.anthropic.com
- **Authentication**: API key header
- **Features**: Streaming, large context

#### DeepSeek
- **Models**: deepseek-chat, deepseek-coder
- **API Base**: https://api.deepseek.com/v1
- **Authentication**: API key header
- **Features**: Coding specialization

#### Local (Ollama)
- **Models**: qwen2.5-coder, codellama, llama3.2, mistral
- **API Base**: http://localhost:11434
- **Authentication**: None
- **Features**: Privacy, offline usage

### Model Selection API

#### Automatic Model Selection
DevMind can automatically select appropriate models based on:
- Task complexity
- Context length requirements
- User preferences
- Model availability

#### Model Switching
```python
# Internal API for model switching
agent.switch_model(
    provider="anthropic",
    model="claude-3-sonnet-20240229",
    config={
        "temperature": 0.1,
        "max_tokens": 4096
    }
)
```

## 🔒 Security API

### Input Validation

All user inputs undergo:
- Content sanitization
- Command injection prevention
- Path traversal protection
- Size limits enforcement

### Code Execution Safety

- Sandboxed execution environment
- Resource limits (CPU, memory, time)
- Restricted system access
- Output sanitization

### API Key Management

- Environment variable storage
- No key logging or display
- Secure transmission (HTTPS only)
- Key rotation support

## 📁 Session Format API

### Session File Structure

```json
{
  "metadata": {
    "name": "session-name",
    "description": "Session description",
    "created_at": "2024-01-15T10:30:00Z",
    "last_modified": "2024-01-15T11:45:00Z",
    "model": "claude-3-sonnet-20240229",
    "token_usage": {
      "total_requests": 12,
      "total_tokens": 15420,
      "total_cost": 0.028560
    }
  },
  "messages": [
    {
      "role": "user",
      "content": "Hello, can you help me with Python?",
      "timestamp": "2024-01-15T10:30:15Z"
    },
    {
      "role": "assistant",
      "content": "Of course! I'd be happy to help...",
      "timestamp": "2024-01-15T10:30:18Z",
      "metadata": {
        "model": "claude-3-sonnet-20240229",
        "tokens": {
          "prompt": 850,
          "completion": 395,
          "total": 1245
        },
        "cost": 0.002340
      }
    }
  ]
}
```

### Session Operations

#### Creating Sessions
```python
session = SessionManager.create_session(
    name="project-name",
    description="Development session",
    auto_save=True
)
```

#### Loading Sessions
```python
session = SessionManager.load_session("project-name")
messages = session.get_messages()
metadata = session.get_metadata()
```

## 🛠️ Extension API

### Custom Tool Development

#### Tool Interface
```python
from src.core.tools.acp_integration import ACPTool, ACPToolSpec

class CustomTool(ACPTool):
    def __init__(self):
        spec = ACPToolSpec(
            name="custom_tool",
            description="Custom tool description",
            parameters={
                "required": ["param1"],
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Parameter description"
                    }
                }
            }
        )
        super().__init__(spec)

    async def _execute_impl(self, message, context):
        # Tool implementation
        return ACPToolResult(
            status=ACPStatus.COMPLETED,
            result="Tool output"
        )
```

#### Tool Registration
```python
from src.core.tools import register_acp_tool

tool = CustomTool()
register_acp_tool(tool)
```

### Custom Model Providers

#### Provider Interface
```python
from src.core.llm.base_llm import BaseLLM, LLMConfig

class CustomProvider(BaseLLM):
    def __init__(self, config: LLMConfig):
        super().__init__(config)

    async def generate(self, messages, **kwargs):
        # Model implementation
        return LLMResponse(
            content="Response content",
            usage=TokenUsage(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            )
        )
```

## 📡 API Error Handling

### Common Error Types

#### Authentication Errors
```python
AuthenticationError: Invalid API key
```

#### Rate Limit Errors
```python
RateLimitError: Rate limit exceeded
```

#### Model Not Found
```python
ModelNotFoundError: Model 'xyz' not available
```

#### Network Errors
```python
NetworkError: Connection timeout
```

### Error Recovery

DevMind implements automatic error recovery:
- Retry with exponential backoff
- Fallback to alternative models
- Graceful degradation of features
- User-friendly error messages

This API reference provides comprehensive information for using and extending DevMind's functionality.