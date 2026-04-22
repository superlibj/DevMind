# CLI Reference Guide

Complete command-line interface documentation for DevMind.

## 🚀 Starting DevMind

### Basic Usage
```bash
# Start with default configuration
python main.py

# Show help
python main.py --help
```

### Command-Line Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--help` | `-h` | Show help message | `python main.py -h` |
| `--version` | `-v` | Show version | `python main.py -v` |
| `--model MODEL` | `-m` | Start with specific model | `python main.py -m claude-3-sonnet` |
| `--provider PROVIDER` | `-p` | Use specific provider | `python main.py -p anthropic` |
| `--session NAME` | `-s` | Load session | `python main.py -s my-project` |
| `--debug` | `-d` | Enable debug logging | `python main.py -d` |
| `--verbose` | | Extra verbose output | `python main.py --verbose` |
| `--list-models` | | Show available models | `python main.py --list-models` |
| `--show-config` | | Display configuration | `python main.py --show-config` |
| `--validate-config` | | Validate setup | `python main.py --validate-config` |
| `--test-apis` | | Test API connections | `python main.py --test-apis` |
| `--timeout SECONDS` | `-t` | Set request timeout | `python main.py -t 120` |
| `--max-iterations N` | | Max ReAct iterations | `python main.py --max-iterations 15` |

### Examples
```bash
# Start with Claude and load project
python main.py --model claude-3-sonnet-20240229 --session my-project

# Debug mode with local model
python main.py --debug --model qwen2.5-coder:7b

# Test configuration
python main.py --validate-config --test-apis

# Quick model test
echo "Hello" | python main.py --model gpt-3.5-turbo
```

## 🎯 Interactive Commands

### Session Management

#### `/save` - Save Session
```bash
/save [session_name] ["description"]
```

**Examples:**
```bash
/save                               # Auto-generate name
/save my-project                    # Save with name
/save web-dev "React application"   # Save with description
```

**Features:**
- Auto-generates timestamp-based names
- Preserves conversation history
- Stores model and configuration info
- Supports custom descriptions

#### `/load` - Load Session
```bash
/load session_name
```

**Examples:**
```bash
/load my-project                    # Load specific session
```

**Features:**
- Restores complete conversation history
- Maintains model context
- Shows loading progress
- Validates session integrity

#### `/sessions` - List Sessions
```bash
/sessions [filter_term]
```

**Examples:**
```bash
/sessions                           # List all sessions
/sessions react                     # Filter by keyword
```

**Output Format:**
```
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                 ┃ Messages ┃ Model          ┃ Last Accessed    ┃ Description          ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ web-dev              │ 15       │ claude-3-sonnet│ 2024-04-22 14:30│ React application    │
│ python-script        │ 8        │ qwen2.5-coder  │ 2024-04-22 10:15│ Data processing      │
└──────────────────────┴──────────┴────────────────┴──────────────────┴──────────────────────┘
```

#### `/delete` - Delete Session
```bash
/delete session_name
```

**Examples:**
```bash
/delete old-project                 # Delete specific session
```

**Features:**
- Confirmation prompt before deletion
- Permanent removal from storage
- Cannot be undone

#### `/export` - Export Session
```bash
/export session_name [filename] [format]
```

**Formats:**
- `markdown` - Formatted markdown (default)
- `json` - Raw JSON data
- `txt` - Plain text

**Examples:**
```bash
/export my-project                      # Export to auto-named .md file
/export my-project report.md markdown   # Export as markdown
/export my-project data.json json       # Export as JSON
```

### Model Management

#### `/model` - Switch Model
```bash
/model [model_name]
```

**Examples:**
```bash
/model                                  # Show current model
/model claude-3-sonnet-20240229        # Switch to Claude
/model gpt-4                           # Switch to GPT-4
/model qwen2.5-coder:7b                # Switch to local model
```

**Features:**
- Preserves conversation context
- Shows model capabilities
- Displays switching confirmation
- Validates model availability

#### `/models` - List Models
```bash
/models [provider_filter]
```

**Providers:**
- `openai` - OpenAI models
- `anthropic` - Claude models
- `deepseek` - DeepSeek models
- `local` - Local Ollama models

**Examples:**
```bash
/models                                 # List all models
/models anthropic                       # List only Claude models
/models local                          # List local models
```

**Output Format:**
```
Available Models:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Model                        ┃ Provider  ┃ Description                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ claude-3-sonnet-20240229     │ anthropic │ Balanced performance and cost     │
│ gpt-4                        │ openai    │ Most capable OpenAI model         │
│ qwen2.5-coder:7b            │ local     │ Local coding model                │
└──────────────────────────────┴───────────┴───────────────────────────────────┘
```

### Information Commands

#### `/help` - Show Help
```bash
/help [topic]
```

**Topics:**
- `commands` - All interactive commands
- `models` - Model management
- `sessions` - Session management
- `weather` - Weather features
- `tools` - Development tools

**Examples:**
```bash
/help                                   # General help
/help commands                          # Command reference
/help weather                          # Weather feature help
```

#### `/tokens` - Token Usage
```bash
/tokens
```

**Output:**
```
╭─ Session Token Usage ─────────────────────────────────────────────╮
│ Current Session                                                   │
│ Duration           │ 25.3 minutes                                │
│ Total Requests     │ 18                                          │
│ Total Tokens       │ 24,150                                      │
│ Total Cost         │ $0.045670                                   │
│ Average per Request│ 1,342 tokens                               │
│                                                                   │
│ Last Request                                                      │
│ Model              │ claude-3-sonnet-20240229                    │
│ Tokens             │ 1,245 (prompt: 850, completion: 395)       │
│ Cost               │ $0.002340                                   │
╰───────────────────────────────────────────────────────────────────╯
```

#### `/status` - System Status
```bash
/status
```

**Shows:**
- Current model and provider
- Session information
- Memory usage
- Configuration status

#### `/clear` - Clear Conversation
```bash
/clear
```

**Features:**
- Clears conversation history
- Keeps session metadata
- Confirms before clearing
- Cannot be undone

#### `/exit` - Exit DevMind
```bash
/exit
```

**Features:**
- Graceful shutdown
- Auto-saves current session (if enabled)
- Shows session summary
- Cleanup of resources

## 🌍 Weather and Location Features

### Natural Language Queries

DevMind understands natural weather and location queries:

#### Weather Queries
```bash
what's the weather?
what's the weather like today?
what's the forecast for tomorrow?
what's the weather the day after tomorrow?
how's the weather in Tokyo?
what's the weather forecast for this week?
```

#### Location Queries
```bash
where am I?
what's my current location?
what city am I in?
what country am I located in?
```

### Weather Response Format
```
╭──────────────────────────────────── Weather Response ─────────────────────────────────────╮
│ 🌤️ Weather for Wuxi, China                                                                 │
│                                                                                            │
│ Current Conditions:                                                                        │
│ Temperature: 15.5°C (feels like 15.8°C)                                                  │
│ Condition: Overcast                                                                       │
│ Humidity: 96%                                                                             │
│ Wind: 8.4 km/h                                                                           │
│                                                                                            │
│ Forecast:                                                                                  │
│ Today: 14 to 16°C, Moderate rain (100% chance)                                           │
│ Tomorrow: 12 to 15°C, Slight rain (35% chance)                                           │
│ Day after tomorrow: 11 to 21°C, Mainly clear                                             │
╰────────────────────────────────────────────────────────────────────────────────────────╯
```

## 🛠️ Development Tools Integration

### File Operations

DevMind can perform various file operations through natural language:

#### Examples
```bash
# Read files
read the contents of main.py
show me the package.json file
what's in the README.md?

# Write files
create a simple Python hello world script
write a basic HTML page with a form
generate a package.json for a React project

# Edit files
fix the syntax error in line 15 of script.py
add error handling to the main function
update the version number in package.json
```

### Git Operations

#### Examples
```bash
# Repository status
what's the git status?
show me the recent commits
what files have been modified?

# Staging and commits
stage all the Python files
commit these changes with message "Fix bug in auth"
create a commit for the new feature

# Branch management
create a new branch called feature/auth
switch to the main branch
show me all branches
```

### Code Analysis

#### Examples
```bash
# Code review
review this Python function for bugs
check this JavaScript code for performance issues
analyze the security of this authentication code

# Documentation
add docstrings to this Python class
generate comments for this complex function
create a README for this project
```

## 🎨 Output Formatting

### Syntax Highlighting

DevMind automatically detects and highlights code in various languages:

- Python
- JavaScript/TypeScript
- Java
- C/C++
- Go
- Rust
- HTML/CSS
- JSON/YAML
- Shell scripts

### Rich Terminal Features

#### Progress Indicators
```bash
💭 Analyzing code structure...
🔧 Executing file operations...
📊 Calculating token usage...
✅ Operation completed successfully
```

#### Interactive Tables
Session lists, model information, and statistics are displayed in formatted tables with:
- Sortable columns
- Color coding
- Alignment optimization
- Responsive sizing

#### Status Bars
For long operations, DevMind shows progress bars:
```
Processing large file... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
```

## 📋 Input Modes

### Single-Line Input
Standard command input for quick queries and commands.

### Multi-Line Input
Use triple backticks for complex code or long text:

```bash
devmind> ```
... def fibonacci(n):
...     if n <= 1:
...         return n
...     return fibonacci(n-1) + fibonacci(n-2)
... ```
```

### Command History
- Use ↑/↓ arrows to navigate command history
- History persists between sessions
- Search history with Ctrl+R (on supported terminals)

### Auto-completion
- Tab completion for commands starting with `/`
- File path completion for file operations
- Model name completion for `/model` command

## 🔧 Configuration Commands

### Environment Validation
```bash
# Check current configuration
python main.py --show-config

# Validate API keys and settings
python main.py --validate-config

# Test all configured APIs
python main.py --test-apis
```

### Debug and Logging
```bash
# Enable debug mode
python main.py --debug

# Verbose output
python main.py --verbose

# Check log files
tail -f logs/devmind.log
```

### Model Testing
```bash
# Quick model test
echo "Hello, test message" | python main.py --model claude-3-haiku

# Interactive model testing
python main.py --model gpt-3.5-turbo
devmind> /tokens  # Check usage after test
```

This CLI reference provides comprehensive coverage of all DevMind command-line and interactive features.