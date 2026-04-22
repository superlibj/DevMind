# Installation Guide

This guide covers various installation methods for DevMind, from basic Python setup to advanced deployment configurations.

## 🎯 System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 4GB (8GB+ recommended for local models)
- **Storage**: 2GB free space (10GB+ for local models)
- **OS**: Windows 10+, macOS 10.15+, or Linux

### Recommended Requirements
- **Python**: 3.10 or higher
- **RAM**: 16GB (for optimal local model performance)
- **GPU**: NVIDIA RTX series (for GPU-accelerated local models)
- **Storage**: SSD with 20GB+ free space
- **Network**: Stable internet connection for cloud models

## 🚀 Quick Installation

### Method 1: Basic Python Installation

```bash
# Clone the repository
git clone <repository-url>
cd aiagent

# Create virtual environment (recommended)
python -m venv devmind-env
source devmind-env/bin/activate  # Linux/macOS
# devmind-env\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Start DevMind
python main.py
```

### Method 2: Development Installation

```bash
# Clone and setup for development
git clone <repository-url>
cd aiagent

# Install in editable mode with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pre-commit install

# Run tests to verify installation
python -m pytest tests/
```

## 📦 Package Dependencies

### Core Dependencies
```bash
# LLM providers
litellm>=1.21.0          # Multi-provider LLM support
anthropic>=0.7.0         # Claude models
openai>=1.6.0           # GPT models

# CLI interface
rich>=13.7.0            # Terminal formatting
typer>=0.9.0           # CLI framework

# HTTP and networking
aiohttp>=3.8.0         # Async HTTP client
requests>=2.28.0       # HTTP requests

# Utilities
pydantic>=2.0.0        # Data validation
python-dotenv>=1.0.0   # Environment variables
```

### Optional Dependencies
```bash
# Local model support
ollama-python>=0.1.0   # Ollama integration

# Development tools
pytest>=7.0.0          # Testing framework
black>=23.0.0          # Code formatting
mypy>=1.0.0           # Type checking
pre-commit>=3.0.0     # Git hooks
```

## 🔧 Platform-Specific Installation

### Windows Installation

#### Using Python from Microsoft Store
```powershell
# Install Python from Microsoft Store
# Then in PowerShell:
git clone <repository-url>
cd aiagent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### Using Conda
```powershell
# Install Miniconda, then:
conda create -n devmind python=3.10
conda activate devmind
pip install -r requirements.txt
```

#### Common Windows Issues
```powershell
# If you get execution policy errors:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# If pip fails with SSL errors:
pip install --trusted-host pypi.org --trusted-host pypi.python.org -r requirements.txt
```

### macOS Installation

#### Using Homebrew
```bash
# Install Python via Homebrew
brew install python@3.10

# Clone and setup
git clone <repository-url>
cd aiagent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Apple Silicon (M1/M2) Notes
```bash
# Some packages may need special handling
pip install --no-deps litellm
pip install --only-binary=all aiohttp

# For local models with GPU acceleration
# Metal is automatically used by compatible models
```

### Linux Installation

#### Ubuntu/Debian
```bash
# Install Python and pip
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# Clone and setup
git clone <repository-url>
cd aiagent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### CentOS/RHEL/Fedora
```bash
# Install Python and pip
sudo dnf install python3 python3-pip python3-venv git  # Fedora
# sudo yum install python3 python3-pip git              # CentOS/RHEL

# Setup same as Ubuntu
```

#### Arch Linux
```bash
# Install Python
sudo pacman -S python python-pip git

# Setup same as other distributions
```

## 🐳 Docker Installation

### Using Pre-built Image (Coming Soon)
```bash
# Pull and run DevMind
docker pull devmind/devmind:latest
docker run -it --rm \
  -v $(pwd):/workspace \
  -e ANTHROPIC_API_KEY=your_key_here \
  devmind/devmind:latest
```

### Building from Source
```bash
# Clone repository
git clone <repository-url>
cd aiagent

# Build Docker image
docker build -t devmind .

# Run with environment variables
docker run -it --rm \
  -v $(pwd):/workspace \
  -e ANTHROPIC_API_KEY=your_key_here \
  devmind
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'
services:
  devmind:
    build: .
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - CLI_AUTO_SAVE=true
    volumes:
      - ./sessions:/app/sessions
      - ./workspace:/workspace
    stdin_open: true
    tty: true
```

```bash
# Run with Docker Compose
docker-compose run devmind
```

## 🔑 API Keys Setup

### Getting API Keys

#### OpenAI
1. Visit [OpenAI API Platform](https://platform.openai.com/account/api-keys)
2. Create an account or sign in
3. Navigate to API keys section
4. Create a new secret key
5. Copy the key (starts with `sk-...`)

#### Anthropic Claude
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign up for an account
3. Go to API Keys section
4. Generate a new API key
5. Copy the key (starts with `sk-ant-...`)

#### DeepSeek
1. Visit [DeepSeek Platform](https://platform.deepseek.com/)
2. Create an account
3. Navigate to API keys
4. Generate a new key
5. Copy the key

### Environment Configuration
```bash
# Create .env file from template
cp .env.example .env

# Edit .env file
nano .env  # or your preferred editor

# Add your API keys
OPENAI_API_KEY=sk-your_openai_key_here
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here
DEEPSEEK_API_KEY=sk-your_deepseek_key_here
```

## 🧪 Local Models Installation

### Ollama Installation

#### Linux/macOS
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve

# Download recommended model
ollama pull qwen2.5-coder:7b
```

#### Windows
1. Download Ollama from [ollama.com](https://ollama.com/download)
2. Run the installer
3. Open Command Prompt or PowerShell
4. Download models: `ollama pull qwen2.5-coder:7b`

### Configure DevMind for Local Models
```bash
# Add to .env file
DEFAULT_LLM_PROVIDER=local
LOCAL_MODEL_NAME=qwen2.5-coder:7b
LOCAL_MODEL_ENDPOINT=http://localhost:11434
```

## ✅ Installation Verification

### Basic Verification
```bash
# Test installation
python main.py --help

# Check available models
python main.py --list-models

# Validate configuration
python main.py --validate-config
```

### API Connection Tests
```bash
# Test cloud models (with API keys)
python main.py --test-apis

# Test local models
python main.py --model qwen2.5-coder:7b --test
```

### Feature Tests
```bash
# Test weather functionality
python main.py
> what's the weather like?

# Test file operations
> create a simple python hello world script

# Test session management
> /save test-session "Installation test"
> /sessions
```

## 🔧 Troubleshooting Installation

### Common Issues

#### Python Version Issues
```bash
# Check Python version
python --version

# If too old, install newer Python
# Use pyenv for version management
curl https://pyenv.run | bash
pyenv install 3.10.12
pyenv global 3.10.12
```

#### Permission Errors
```bash
# Linux/macOS: Use virtual environment
python -m venv venv
source venv/bin/activate

# Windows: Run as administrator or use --user flag
pip install --user -r requirements.txt
```

#### Network/SSL Issues
```bash
# Upgrade pip and certificates
pip install --upgrade pip
pip install --upgrade certifi

# For corporate networks
pip install --trusted-host pypi.org --trusted-host pypi.python.org -r requirements.txt
```

#### Memory Issues with Local Models
```bash
# Use smaller models
ollama pull qwen2.5-coder:3b

# Check available memory
free -h  # Linux
vm_stat  # macOS
```

#### Import Errors
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check for conflicting packages
pip check

# Use fresh virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Debug Mode
```bash
# Run in debug mode for detailed logs
python main.py --debug

# Check log files
tail -f logs/devmind.log
```

## 🚀 Post-Installation Setup

### Optional Configurations

#### Shell Integration (Bash/Zsh)
```bash
# Add alias to shell config
echo 'alias dm="python /path/to/aiagent/main.py"' >> ~/.bashrc
source ~/.bashrc

# Now you can use 'dm' command
dm --help
```

#### Desktop Shortcut (Linux)
```bash
# Create .desktop file
cat > ~/.local/share/applications/devmind.desktop << EOF
[Desktop Entry]
Name=DevMind
Comment=AI Development Assistant
Exec=/path/to/aiagent/venv/bin/python /path/to/aiagent/main.py
Icon=/path/to/aiagent/icon.png
Terminal=true
Type=Application
Categories=Development;
EOF
```

#### Windows Start Menu
```powershell
# Create shortcut in Start Menu
# Right-click on main.py -> Send to -> Desktop
# Move shortcut to Start Menu folder
```

### Performance Optimization

#### For Cloud Models
```bash
# Configure timeouts
OPENAI_API_TIMEOUT=60
ANTHROPIC_API_TIMEOUT=60

# Enable response caching
ENABLE_RESPONSE_CACHE=true
CACHE_DURATION_MINUTES=15
```

#### For Local Models
```bash
# GPU acceleration (if available)
# Will be used automatically by Ollama

# Memory optimization
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_KEEP_ALIVE=5m
```

## 📋 Installation Checklist

- [ ] Python 3.8+ installed
- [ ] Git installed and configured
- [ ] Repository cloned
- [ ] Virtual environment created and activated
- [ ] Dependencies installed successfully
- [ ] `.env` file created and configured
- [ ] API keys added (at least one)
- [ ] Installation verified with `--help`
- [ ] Model list accessible with `--list-models`
- [ ] Basic functionality tested
- [ ] Local models installed (optional)
- [ ] Session directory created
- [ ] Logs directory accessible

## 🎉 Next Steps

After successful installation:

1. **Read the [Configuration Guide](configuration.md)** for detailed setup options
2. **Check [Local Models Guide](local-models.md)** if using local models
3. **Review [CLI Reference](cli-reference.md)** for command usage
4. **Start with simple queries** to get familiar with DevMind
5. **Explore weather/location features** for enhanced functionality

You're now ready to use DevMind for AI-powered development assistance!