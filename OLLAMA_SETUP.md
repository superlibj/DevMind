# Ollama Quick Setup Guide

## 🚀 Why Choose Ollama?

- ✅ **Super Simple**: One command to install, one command to run
- ✅ **Automatic Management**: Automatically downloads, updates and manages models
- ✅ **Ready to Use**: No manual building or configuration needed
- ✅ **Rich Models**: Supports the latest open-source models
- ✅ **Performance Optimized**: Automatically optimizes for different hardware

## ⚡ **Ultra-Fast Setup (Done in 3 minutes)**

### **Step 1: Install Ollama**

#### **Linux (Recommended)**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### **macOS**
```bash
# Using Homebrew
brew install ollama

# Or download installer
# Visit https://ollama.com/download
```

#### **Windows**
```bash
# Download and run installer
# Visit https://ollama.com/download/windows
```

### **Step 2: Start Ollama Service**
```bash
# Start service (runs in background)
ollama serve
```

### **Step 3: Pull Programming Models**
```bash
# Pull recommended programming models (choose one or more)

# Latest and strongest - Llama 3.2 (recommended)
ollama pull llama3.2

# Programming-specific - DeepSeek Coder
ollama pull deepseek-coder

# Code generation - Code Llama 13B
ollama pull codellama:13b

# Fast lightweight - Mistral
ollama pull mistral

# Multilingual programming - Qwen2.5 Coder
ollama pull qwen2.5-coder
```

### **Step 4: Use with DevMind**
```bash
# Start DevMind
python main.py

# Check Ollama status
devmind> /ollama

# View all local models
devmind> /local

# Switch to Ollama model
devmind> /model llama3.2

# Start programming conversation
devmind> Help me write a Python quicksort function
```

## 🎯 **Recommended Model Configurations**

### **Beginner Recommendation (Choose 1-2)**
```bash
ollama pull llama3.2      # Latest general-purpose model
ollama pull deepseek-coder # Programming-specific
```

### **Developer Recommendation (Choose 2-3)**
```bash
ollama pull llama3.2      # Latest general-purpose
ollama pull codellama:13b # Strong coding capabilities
ollama pull deepseek-coder # Programming assistant
ollama pull mistral       # Fast and lightweight
```

### **Professional Developer (Full Suite)**
```bash
ollama pull llama3.2      # Latest general-purpose
ollama pull codellama:13b # Code generation
ollama pull deepseek-coder # Programming understanding
ollama pull qwen2.5-coder # Multilingual
ollama pull starcoder2    # High-quality code
ollama pull mistral       # Fast prototyping
ollama pull phi3          # Compact model
```

## 📊 **Model Comparison Table**

| Model | Size | Memory Required | Programming Ability | General Ability | Speed |
|------|------|----------|----------|----------|------|
| `llama3.2` | 4.7GB | 8GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `deepseek-coder` | 3.8GB | 6GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| `codellama:13b` | 7.3GB | 16GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| `mistral` | 4.1GB | 8GB | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| `qwen2.5-coder` | 4.2GB | 8GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## 🔧 **Common Ollama Commands**

### **Model Management**
```bash
# View installed models
ollama list

# Pull new model
ollama pull model-name

# Delete model
ollama rm model-name

# Update model
ollama pull model-name
```

### **Direct Model Testing**
```bash
# Test directly in command line (without DevMind)
ollama run llama3.2
# Then you can chat directly

# Exit test
/bye
```

### **Service Management**
```bash
# Start service
ollama serve

# Check service status
ollama ps

# View running models
ollama ps
```

## 🚀 **Complete Setup Example**

Assuming you're a Python developer, here's the complete setup process:

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Start service
ollama serve &

# 3. Pull recommended models
ollama pull llama3.2
ollama pull deepseek-coder

# 4. Verify installation
ollama list

# 5. Start DevMind
cd ~/workspace/aiagent
python main.py

# 6. Use in DevMind
# devmind> /ollama
# devmind> /model llama3.2
# devmind> Help me write a Web API
```

## 🔍 **Troubleshooting**

### **Service Start Failed**
```bash
# Check if already running
ollama ps

# Kill existing process and restart
pkill ollama
ollama serve
```

### **Model Download Slow**
```bash
# Set mirrors for China (if in China)
export OLLAMA_MIRRORS="https://ollama.hf.space,https://ollama-models.zwc365.com"
ollama pull llama3.2
```

### **Insufficient Memory**
```bash
# Use smaller models
ollama pull phi3        # 3.8GB
ollama pull llama3.2:8b # If default is too large, try specifying size
```

### **Port Conflict**
```bash
# Change default port (default 11434)
export OLLAMA_HOST=0.0.0.0:11435
ollama serve
```

## 📱 **One-Click Startup Script**

Create a convenient startup script:

```bash
# Create Ollama startup script
cat > ~/start_ollama_dev.sh << 'EOF'
#!/bin/bash
echo "🦙 Starting Ollama development environment..."

# Check if Ollama is already running
if ! pgrep -x "ollama" > /dev/null; then
    echo "📍 Starting Ollama service..."
    ollama serve &
    sleep 3
else
    echo "✅ Ollama service already running"
fi

# Show available models
echo "📋 Available models:"
ollama list

echo ""
echo "🚀 Ollama ready!"
echo "💡 Usage examples:"
echo "   devmind> /model llama3.2"
echo "   devmind> /model deepseek-coder"
EOF

chmod +x ~/start_ollama_dev.sh

# Run
~/start_ollama_dev.sh
```

## 🎯 **DevMind Integration Testing**

After setup, test in DevMind:

```bash
# Start DevMind
python main.py

# Test Ollama integration
devmind> /ollama
🦙 Ollama Integration
✓ Ollama server found with 3 models:
  • llama3.2
  • deepseek-coder
  • mistral

# Switch model test
devmind> /model deepseek-coder
✓ Switched to deepseek-coder
Provider: Ollama
Description: DeepSeek Coder - Excellent for programming tasks

# Test programming capabilities
devmind> Help me write a basic FastAPI application structure
```

## 🏆 **Best Practices**

1. **First Use**: Pull `llama3.2` and `deepseek-coder` first
2. **Daily Development**: Mainly use `deepseek-coder` for programming
3. **Complex Reasoning**: Switch to `llama3.2` for architecture design
4. **Quick Prototyping**: Use `mistral` for fast responses
5. **Regular Updates**: `ollama pull model-name` to update models

Ollama is much simpler than llama.cpp! Try it now! 🚀