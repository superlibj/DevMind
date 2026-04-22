# Troubleshooting Guide

This guide helps you resolve common issues when using DevMind.

## 🚨 Common Issues

### 1. Installation Problems

#### Python Version Issues
```bash
# Error: DevMind requires Python 3.8+
$ python --version
Python 3.7.3

# Solution: Install newer Python
# Using pyenv (recommended)
curl https://pyenv.run | bash
pyenv install 3.10.12
pyenv global 3.10.12

# Using system package manager
sudo apt install python3.10  # Ubuntu
brew install python@3.10     # macOS
```

#### Dependency Installation Failures
```bash
# Error: pip install fails
# Solution 1: Update pip
pip install --upgrade pip

# Solution 2: Use virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Solution 3: Clear pip cache
pip cache purge
pip install -r requirements.txt
```

#### Permission Denied Errors
```bash
# Error: Permission denied when installing
# Solution: Use virtual environment or --user flag
pip install --user -r requirements.txt

# Or create virtual environment
python -m venv devmind-env
source devmind-env/bin/activate  # Linux/macOS
devmind-env\Scripts\activate     # Windows
```

### 2. API Key and Authentication Issues

#### Invalid API Key
```bash
# Error: Invalid API key
Agent error: AuthenticationError

# Solution: Check your .env file
cat .env | grep API_KEY

# Verify key format:
OPENAI_API_KEY=sk-...           # OpenAI format
ANTHROPIC_API_KEY=sk-ant-...    # Anthropic format
DEEPSEEK_API_KEY=sk-...         # DeepSeek format
```

#### API Key Not Found
```bash
# Error: No API key configured
Agent error: No API key found for provider 'anthropic'

# Solution: Add key to .env file
echo "ANTHROPIC_API_KEY=sk-ant-your_key_here" >> .env

# Or export environment variable
export ANTHROPIC_API_KEY=sk-ant-your_key_here
```

#### Rate Limiting
```bash
# Error: Rate limit exceeded
Agent error: Rate limit exceeded

# Solution: Wait and retry, or switch models
devmind> /model gpt-3.5-turbo  # Usually has higher limits

# Or configure rate limiting
echo "RATE_LIMIT_RPM=30" >> .env
```

### 3. Local Model Issues

#### Ollama Not Running
```bash
# Error: Connection refused to localhost:11434
Agent error: Connection refused

# Solution: Start Ollama service
ollama serve

# Check if running
curl http://localhost:11434/api/version
```

#### Model Not Found
```bash
# Error: Model not found
Agent error: Model 'qwen2.5-coder:7b' not found

# Solution: Download the model
ollama pull qwen2.5-coder:7b

# Check available models
ollama list
```

#### Out of Memory
```bash
# Error: Model loading failed - insufficient memory
# Solution 1: Use smaller model
ollama pull qwen2.5-coder:3b

# Solution 2: Close other applications
# Solution 3: Increase swap space (Linux)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### Slow Local Model Responses
```bash
# Issue: Very slow responses (60+ seconds)
# Solution 1: Check CPU usage
top  # Look for ollama process

# Solution 2: Use GPU acceleration (if available)
# GPU acceleration is automatic with compatible hardware

# Solution 3: Reduce context size
# Edit Ollama modelfile to reduce num_ctx
```

### 4. Weather and Location Issues

#### Weather Service Unavailable
```bash
# Error: Weather service timeout
Agent error: Weather service timeout

# Solution 1: Check internet connection
curl https://api.open-meteo.com/v1/forecast

# Solution 2: Increase timeout
echo "WEATHER_TIMEOUT=60" >> .env

# Solution 3: Check if Open-Meteo is accessible
ping api.open-meteo.com
```

#### Location Detection Failed
```bash
# Error: Could not determine location
Agent error: Location detection failed

# Solution 1: Try alternative location services
# DevMind automatically tries multiple services

# Solution 2: Specify location manually
devmind> what's the weather in New York?

# Solution 3: Check IP-based services
curl https://ipapi.co/json/
```

### 5. Performance Issues

#### Slow Startup
```bash
# Issue: DevMind takes long time to start
# Solution 1: Check tool registration
# Comment out unused tools in src/core/tools/__init__.py

# Solution 2: Use faster model
python main.py --model claude-3-haiku-20240307

# Solution 3: Disable auto-loading
echo "CLI_AUTO_LOAD_LAST=false" >> .env
```

#### High Memory Usage
```bash
# Issue: DevMind using too much memory
# Solution 1: Clear conversation history
devmind> /clear

# Solution 2: Reduce max tokens
echo "CLI_MAX_TOKENS=2048" >> .env

# Solution 3: Monitor memory
top -p $(pgrep -f "python main.py")
```

#### Frequent Timeouts
```bash
# Issue: Requests timing out frequently
# Solution 1: Increase timeout
echo "ANTHROPIC_API_TIMEOUT=120" >> .env

# Solution 2: Check network stability
ping 8.8.8.8

# Solution 3: Switch to local model
python main.py --model qwen2.5-coder:7b
```

### 6. Session and File Issues

#### Session Loading Failed
```bash
# Error: Failed to load session
Agent error: Session 'project-name' not found

# Solution 1: Check session exists
ls sessions/

# Solution 2: List available sessions
devmind> /sessions

# Solution 3: Check file permissions
chmod 755 sessions/
chmod 644 sessions/*.json
```

#### File Operation Errors
```bash
# Error: Permission denied when reading file
Agent error: Permission denied

# Solution 1: Check file permissions
ls -la filename.py

# Solution 2: Run with appropriate permissions
# Don't run as root unless necessary

# Solution 3: Check file exists and path is correct
```

### 7. Display and Terminal Issues

#### Garbled Output
```bash
# Issue: Text display is corrupted
# Solution 1: Check terminal encoding
echo $LANG

# Solution 2: Disable color output
echo "CLI_COLOR_THEME=none" >> .env

# Solution 3: Update terminal
# Use modern terminal like Windows Terminal, iTerm2, etc.
```

#### Syntax Highlighting Not Working
```bash
# Issue: No syntax highlighting
# Solution 1: Check if enabled
echo "CLI_SYNTAX_HIGHLIGHTING=true" >> .env

# Solution 2: Install required packages
pip install rich[syntax]

# Solution 3: Check terminal support
# Use terminal that supports 256 colors
```

## 🔧 Debug Mode

### Enable Debug Logging
```bash
# Start with debug mode
python main.py --debug

# Or set in environment
echo "LOG_LEVEL=DEBUG" >> .env
echo "DEBUG=true" >> .env
```

### Check Log Files
```bash
# View recent logs
tail -f logs/devmind.log

# Search for specific errors
grep "ERROR" logs/devmind.log

# View full log
less logs/devmind.log
```

### Verbose Mode
```bash
# Extra verbose output
python main.py --verbose

# Show configuration
python main.py --show-config

# Validate setup
python main.py --validate-config
```

## 🧪 Testing Your Installation

### Basic Functionality Test
```bash
# Test 1: CLI starts
python main.py --help

# Test 2: Model list loads
python main.py --list-models

# Test 3: Configuration valid
python main.py --validate-config

# Test 4: Simple query
python main.py
devmind> hello
```

### API Connection Tests
```bash
# Test cloud APIs
python main.py --test-apis

# Test specific model
echo "Testing Claude..." | python main.py --model claude-3-haiku-20240307
```

### Feature Tests
```bash
# Test file operations
devmind> create a simple test.py file with hello world

# Test weather (if enabled)
devmind> what's the weather?

# Test session management
devmind> /save test-session "Test session"
devmind> /sessions
```

## 📊 System Information

### Collect System Info
```bash
# Python information
python --version
pip list | grep -E "(anthropic|openai|litellm|rich)"

# System resources
free -h          # Memory (Linux)
df -h            # Disk space
ps aux | grep python  # Running processes
```

### DevMind Information
```bash
# Show configuration
python main.py --show-config

# Show available models
python main.py --list-models

# Check API status
python main.py --test-apis
```

## 🆘 Getting Help

### Self-Help Resources
```bash
# Built-in help
devmind> /help

# Command-line help
python main.py --help

# Model-specific help
python main.py --model claude-3-sonnet-20240229 --help
```

### Log Analysis
```bash
# Check for specific errors
grep -A 5 -B 5 "ERROR" logs/devmind.log

# Look for network issues
grep -i "timeout\|connection\|network" logs/devmind.log

# Find API errors
grep -i "api\|authentication\|rate.limit" logs/devmind.log
```

### Issue Reporting

When reporting issues, please include:

1. **DevMind Version**: `python main.py --version`
2. **Python Version**: `python --version`
3. **Operating System**: `uname -a` (Linux/macOS) or `ver` (Windows)
4. **Error Message**: Full error output
5. **Configuration**: Relevant parts of `.env` (without API keys)
6. **Steps to Reproduce**: What you did before the error
7. **Log Files**: Recent entries from `logs/devmind.log`

### Template for Bug Reports
```markdown
## Environment
- DevMind Version: [output of --version]
- Python Version: [python --version]
- OS: [your operating system]
- Model: [which model you were using]

## Issue Description
[Describe what went wrong]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [etc.]

## Expected Behavior
[What should have happened]

## Actual Behavior
[What actually happened]

## Error Output
```
[paste error message here]
```

## Logs
```
[relevant log entries]
```

## Additional Context
[any other relevant information]
```

## 🔄 Recovery Procedures

### Reset Configuration
```bash
# Backup current config
cp .env .env.backup

# Reset to defaults
cp .env.example .env
# Edit with your API keys

# Clear cache
rm -rf .cache/
```

### Clean Installation
```bash
# Remove virtual environment
rm -rf venv/

# Fresh installation
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Reset Sessions
```bash
# Backup sessions
cp -r sessions/ sessions_backup/

# Clear all sessions
rm -rf sessions/*.json

# Restart with clean state
python main.py
```

This troubleshooting guide covers the most common issues. If you encounter a problem not listed here, try enabling debug mode and checking the logs for more detailed error information.