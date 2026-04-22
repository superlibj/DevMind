# Configuration Guide

This guide covers all configuration options for DevMind, from basic setup to advanced customizations.

## 🚀 Quick Setup

### Environment Configuration

Create a `.env` file in the project root:

```bash
# Copy from template
cp .env.example .env

# Edit with your preferences
nano .env
```

### Basic Configuration
```bash
# LLM Provider Settings
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_key_here

# CLI Preferences
CLI_STREAM_RESPONSES=true
CLI_AUTO_SAVE=true
CLI_SYNTAX_HIGHLIGHTING=true
```

## 🔑 API Keys Setup

### Cloud Providers

#### OpenAI
```bash
OPENAI_API_KEY=sk-your_openai_key_here
```
Get your key from [OpenAI API Keys](https://platform.openai.com/account/api-keys)

#### Anthropic Claude
```bash
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here
```
Get your key from [Anthropic Console](https://console.anthropic.com/)

#### DeepSeek
```bash
DEEPSEEK_API_KEY=sk-your_deepseek_key_here
```
Get your key from [DeepSeek Platform](https://platform.deepseek.com/)

### Local Models

#### Ollama
```bash
DEFAULT_LLM_PROVIDER=local
LOCAL_MODEL_NAME=qwen2.5-coder:7b
LOCAL_MODEL_ENDPOINT=http://localhost:11434
```

#### llama.cpp
```bash
DEFAULT_LLM_PROVIDER=local
LOCAL_MODEL_NAME=llama-cpp
LOCAL_MODEL_ENDPOINT=http://localhost:8080/v1
```

## ⚙️ LLM Configuration

### Model Selection

#### Default Model
```bash
# Set your preferred default model
CLI_DEFAULT_MODEL=claude-3-sonnet-20240229
```

#### Model-Specific Settings
```bash
# Temperature (creativity level: 0.0-1.0)
CLI_TEMPERATURE=0.1

# Maximum tokens per response
CLI_MAX_TOKENS=4096

# Top-p sampling (0.0-1.0)
CLI_TOP_P=0.9
```

### Provider-Specific Options

#### OpenAI Configuration
```bash
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_ORGANIZATION=your_org_id  # Optional
```

#### Anthropic Configuration
```bash
ANTHROPIC_API_BASE=https://api.anthropic.com
```

#### DeepSeek Configuration
```bash
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
```

## 🖥️ CLI Interface Settings

### Display Options
```bash
# Enable/disable syntax highlighting
CLI_SYNTAX_HIGHLIGHTING=true

# Color theme (dark/light/auto)
CLI_COLOR_THEME=dark

# Enable streaming responses
CLI_STREAM_RESPONSES=true

# Show token usage information
CLI_SHOW_TOKENS=true
```

### Session Management
```bash
# Automatic session saving
CLI_AUTO_SAVE=true

# Sessions directory
CLI_SESSIONS_DIR=./sessions

# Maximum session history
CLI_MAX_HISTORY=100

# Auto-load last session
CLI_AUTO_LOAD_LAST=false
```

### Input/Output Settings
```bash
# Multi-line input timeout (seconds)
CLI_MULTILINE_TIMEOUT=30

# Page size for long outputs
CLI_PAGE_SIZE=50

# Enable input history
CLI_INPUT_HISTORY=true
```

## 🛠️ Development Tools Configuration

### File Operations
```bash
# Maximum file size for reading (MB)
MAX_FILE_SIZE_MB=10

# Default file encoding
DEFAULT_FILE_ENCODING=utf-8

# Backup files before editing
CREATE_BACKUPS=true
```

### Git Integration
```bash
# Default git remote
DEFAULT_GIT_REMOTE=origin

# Auto-commit generated files
GIT_AUTO_COMMIT=false

# Git safety checks
GIT_SAFETY_ENABLED=true
```

### Security Settings
```bash
# Enable input validation
SECURITY_INPUT_VALIDATION=true

# Sandbox code execution
SECURITY_SANDBOX_ENABLED=true

# Maximum execution time (seconds)
SECURITY_MAX_EXECUTION_TIME=30
```

## 🌍 Weather & Location Services

### Service Configuration
```bash
# Enable weather/location services
WEATHER_ENABLED=true
LOCATION_ENABLED=true

# Service timeout (seconds)
WEATHER_TIMEOUT=30
LOCATION_TIMEOUT=30
```

### API Settings
```bash
# Weather service endpoints (Open-Meteo is free)
WEATHER_API_BASE=https://api.open-meteo.com/v1

# Location service endpoints
LOCATION_API_PRIMARY=https://ipapi.co/json/
LOCATION_API_FALLBACK=http://ip-api.com/json/
```

### Cache Configuration
```bash
# Cache weather data (minutes)
WEATHER_CACHE_DURATION=15

# Cache location data (hours)
LOCATION_CACHE_DURATION=24
```

## 📊 Monitoring & Logging

### Logging Configuration
```bash
# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Log to file
LOG_TO_FILE=true
LOG_FILE_PATH=./logs/devmind.log

# Log rotation
LOG_MAX_SIZE_MB=10
LOG_BACKUP_COUNT=5
```

### Token Usage Tracking
```bash
# Enable token tracking
TOKEN_TRACKING_ENABLED=true

# Cost calculation currency
COST_CURRENCY=USD

# Show cost in real-time
SHOW_REAL_TIME_COST=true
```

### Performance Monitoring
```bash
# Monitor response times
MONITOR_RESPONSE_TIMES=true

# Alert on slow responses (seconds)
SLOW_RESPONSE_THRESHOLD=10

# Memory usage monitoring
MONITOR_MEMORY_USAGE=true
```

## 🔧 Advanced Configuration

### Model Fallbacks
```bash
# Primary model
PRIMARY_MODEL=claude-3-sonnet-20240229

# Fallback models (comma-separated)
FALLBACK_MODELS=gpt-3.5-turbo,qwen2.5-coder:7b

# Enable automatic fallback
ENABLE_MODEL_FALLBACK=true
```

### Rate Limiting
```bash
# Requests per minute
RATE_LIMIT_RPM=60

# Concurrent requests
MAX_CONCURRENT_REQUESTS=5

# Retry configuration
MAX_RETRIES=3
RETRY_DELAY=1
```

### Custom Tool Configuration
```bash
# Tool timeout (seconds)
TOOL_TIMEOUT=30

# Enable dangerous operations
ALLOW_DANGEROUS_OPERATIONS=false

# Tool execution sandbox
TOOL_SANDBOX_ENABLED=true
```

## 📁 Directory Structure Configuration

### Working Directories
```bash
# Base working directory
WORKING_DIR=./

# Sessions storage
SESSIONS_DIR=./sessions

# Logs directory
LOGS_DIR=./logs

# Cache directory
CACHE_DIR=./.cache
```

### File Patterns
```bash
# Ignore patterns (glob format)
IGNORE_PATTERNS=__pycache__,*.pyc,.git,node_modules

# Include patterns for file operations
INCLUDE_PATTERNS=*.py,*.js,*.md,*.json

# Default file extensions for code
CODE_EXTENSIONS=py,js,ts,java,cpp,c,go,rs
```

## 🎨 UI Customization

### Terminal Themes
```bash
# Available themes: dark, light, monokai, solarized
CLI_THEME=dark

# Custom color scheme
CLI_PRIMARY_COLOR=#0066cc
CLI_SUCCESS_COLOR=#00cc66
CLI_WARNING_COLOR=#cc6600
CLI_ERROR_COLOR=#cc0000
```

### Output Formatting
```bash
# Progress bar style
PROGRESS_BAR_STYLE=blue_on_white

# Spinner style for loading
SPINNER_STYLE=dots

# Table border style
TABLE_BORDER_STYLE=rounded
```

## 🔍 Environment-Specific Configurations

### Development Environment
```bash
# .env.development
DEBUG=true
LOG_LEVEL=DEBUG
CLI_AUTO_SAVE=false
SHOW_DEBUG_INFO=true
```

### Production Environment
```bash
# .env.production
DEBUG=false
LOG_LEVEL=INFO
CLI_AUTO_SAVE=true
SECURITY_SANDBOX_ENABLED=true
```

### Testing Environment
```bash
# .env.test
USE_MOCK_MODELS=true
DISABLE_API_CALLS=true
CLI_STREAM_RESPONSES=false
```

## 📋 Configuration Validation

### Checking Configuration
```bash
# Validate current configuration
python main.py --validate-config

# Show all configuration values
python main.py --show-config

# Test API connections
python main.py --test-apis
```

### Common Validation Issues

#### Missing API Keys
```bash
# Error: No API key found for provider
# Solution: Add key to .env file
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

#### Invalid Model Names
```bash
# Error: Model not found
# Solution: Check available models
python main.py --list-models
```

#### Network Issues
```bash
# Error: Connection timeout
# Solution: Check endpoints and increase timeout
WEATHER_TIMEOUT=60
ANTHROPIC_API_TIMEOUT=60
```

## 🔒 Security Best Practices

### API Key Management
- Store keys in `.env` file (not in code)
- Use different keys for development/production
- Rotate keys regularly
- Monitor usage for unexpected spikes

### File Permissions
```bash
# Secure .env file
chmod 600 .env

# Secure session files
chmod 700 sessions/
```

### Network Security
```bash
# Use HTTPS endpoints only
OPENAI_API_BASE=https://api.openai.com/v1
ANTHROPIC_API_BASE=https://api.anthropic.com

# Enable TLS verification
VERIFY_SSL=true
```

## 🚀 Performance Optimization

### Model Selection
- Use smaller models for simple tasks
- Switch to larger models for complex operations
- Enable local models for privacy and speed

### Caching
```bash
# Enable response caching
ENABLE_RESPONSE_CACHE=true
CACHE_DURATION_MINUTES=15

# Cache location
CACHE_DIRECTORY=./.cache/responses
```

### Resource Limits
```bash
# Memory limits
MAX_MEMORY_MB=2048

# Concurrent operations
MAX_CONCURRENT_TOOLS=3

# Response size limits
MAX_RESPONSE_SIZE=50000
```

## 💡 Example Configurations

### For Coding Projects
```bash
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
CLI_DEFAULT_MODEL=claude-3-sonnet-20240229
CLI_SYNTAX_HIGHLIGHTING=true
GIT_INTEGRATION=true
CLI_AUTO_SAVE=true
```

### For Local Development
```bash
DEFAULT_LLM_PROVIDER=local
LOCAL_MODEL_NAME=qwen2.5-coder:7b
LOCAL_MODEL_ENDPOINT=http://localhost:11434
CLI_STREAM_RESPONSES=true
LOG_LEVEL=DEBUG
```

### For Team Environments
```bash
CLI_SESSIONS_DIR=/shared/sessions
CLI_AUTO_SAVE=true
SECURITY_SANDBOX_ENABLED=true
RATE_LIMIT_RPM=30
MAX_CONCURRENT_REQUESTS=2
```

This configuration guide provides comprehensive coverage of all DevMind settings, from basic setup to advanced customizations for specific use cases.