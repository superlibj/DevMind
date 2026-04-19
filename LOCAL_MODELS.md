# DevMind Local Model Support

## 🎯 Feature Overview

DevMind now supports locally running open-source models through Ollama and llama.cpp integration, allowing you to run powerful AI models locally without depending on online services!

## 🚀 Supported Local Model Platforms

### **1. Ollama Integration**
- ✅ Simple and easy model management
- ✅ One-click model installation and execution
- ✅ Automatic model discovery
- ✅ Full API compatibility

### **2. llama.cpp Integration**
- ✅ High-performance GGUF model support
- ✅ OpenAI-compatible API
- ✅ Flexible model configuration
- ✅ Low memory footprint

## 📋 Pre-configured Model List

### **Ollama Models**

| Model Name | Description | Specialization |
|---------|------|------|
| `llama3.2` | Llama 3.2 | Latest general-purpose capabilities |
| `llama3.1` | Llama 3.1 | Large context window, strong performance |
| `codellama` | Code Llama 7B | Specialized for code generation |
| `codellama:13b` | Code Llama 13B | Enhanced coding capabilities |
| `codellama:34b` | Code Llama 34B | Best coding performance |
| `deepseek-coder` | DeepSeek Coder | Excellent programming assistant |
| `qwen2.5-coder` | Qwen2.5 Coder | Multilingual programming support |
| `starcoder2` | StarCoder2 | High-quality code generation |
| `mistral` | Mistral 7B | Fast general-purpose model |
| `mixtral` | Mixtral 8x7B | Mixture of experts model |
| `phi3` | Phi-3 | Compact but powerful |

### **llama.cpp Models**

| Model Name | Description | Use Cases |
|---------|------|---------|
| `llama-cpp-local` | General local model | Basic chat and programming |
| `llama-cpp-codeqwen` | CodeQwen GGUF | Professional programming tasks |
| `llama-cpp-codellama` | Code Llama GGUF | Code generation |

## ⚙️ Installation and Setup

### **Ollama Setup**

#### **1. Install Ollama**
```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Download installer from https://ollama.com/download
```

#### **2. Start Ollama Service**
```bash
ollama serve
```

#### **3. Pull Recommended Models**
```bash
# Latest general-purpose model
ollama pull llama3.2

# Programming-specific models
ollama pull codellama:13b
ollama pull deepseek-coder

# Fast lightweight model
ollama pull mistral
```

### **llama.cpp Setup**

#### **1. Build llama.cpp**
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make
```

#### **2. Download GGUF Models**
Download GGUF format models from Hugging Face:
- `CodeQwen1.5-7B-Chat.Q4_K_M.gguf`
- `CodeLlama-13B-Instruct.Q4_K_M.gguf`
- `deepseek-coder-6.7b-instruct.Q4_K_M.gguf`

#### **3. Start Server**
```bash
# Start OpenAI-compatible server
./server -m models/your-model.gguf -c 4096 --port 8080

# Or use alias for easier usage
./server --model models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --ctx-size 4096 --port 8080 --alias codellama
```

## 🔧 Using with DevMind

### **Basic Commands**

#### **Check Local Models**
```bash
devmind> /local
🏠 Local Model Servers
┏━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Server  ┃ Provider ┃ URL                  ┃ Status ┃ Models          ┃
┡━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ ollama  │ Ollama   │ http://localhost:... │ ● Ac.. │ llama3.2, co... │
│ llama..
```

#### **Ollama Help**
```bash
devmind> /ollama
🦙 Ollama Integration
✓ Ollama server found with 5 models:
  • llama3.2
  • codellama:13b
  • deepseek-coder

Quick start:
  /model llama3.2
```

#### **llama.cpp Help**
```bash
devmind> /llamacpp
🦙 llama.cpp Integration
✓ llama.cpp server found with 2 models:
  • codeqwen-7b
  • codellama-13b

Quick start:
  /model llama-cpp-local
```

### **Switching to Local Models**
```bash
# Use Ollama model
devmind> /model llama3.2
✓ Switched to llama3.2

# Use llama.cpp model
devmind> /model llama-cpp-local
✓ Switched to llama-cpp-local
```

### **Real Development Example**
```bash
devmind> /model deepseek-coder
✓ Switched to deepseek-coder
Provider: Ollama
Description: DeepSeek Coder - Excellent for programming tasks

devmind> Help me write a Python quicksort function
💭 Starting task analysis
💭 User needs Python quicksort function, I'll write an efficient implementation

def quicksort(arr):
    """
    Quicksort algorithm implementation

    Args:
        arr: Array to be sorted

    Returns:
        Sorted array
    """
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quicksort(left) + middle + quicksort(right)

# Usage example
if __name__ == "__main__":
    data = [64, 34, 25, 12, 22, 11, 90]
    sorted_data = quicksort(data)
    print(f"Original array: {data}")
    print(f"Sorted array: {sorted_data}")
```

## 🎯 Recommended Configurations

### **Developer Recommended Configurations**

#### **Lightweight Development Environment (8GB RAM)**
```bash
ollama pull mistral      # Fast general-purpose
ollama pull deepseek-coder # Programming-specific
```

#### **Standard Development Environment (16GB RAM)**
```bash
ollama pull llama3.2      # Latest capabilities
ollama pull codellama:13b # Strong coding abilities
ollama pull deepseek-coder # Programming assistant
```

#### **Professional Development Environment (32GB+ RAM)**
```bash
ollama pull llama3.1      # Large context
ollama pull codellama:34b # Strongest programming
ollama pull mixtral       # Mixture of experts
ollama pull qwen2.5-coder # Multilingual support
```

### **Model Selection Guide**

| Task Type | Recommended Models | Description |
|---------|---------|------|
| Code Generation | `codellama:13b`, `deepseek-coder` | Professional programming capabilities |
| Code Review | `qwen2.5-coder`, `codellama:34b` | Deep code understanding |
| Quick Prototyping | `mistral`, `phi3` | Lightweight and fast |
| Complex Reasoning | `llama3.2`, `mixtral` | Strong logical capabilities |
| Large Projects | `llama3.1`, `codellama:34b` | Large context support |

## 🔍 Troubleshooting

### **Common Issues**

#### **Ollama Connection Failed**
```bash
# Check service status
ollama ps

# Restart service
ollama serve

# Check port
netstat -an | grep 11434
```

#### **llama.cpp Connection Failed**
```bash
# Check server process
ps aux | grep server

# Check port
netstat -an | grep 8080

# Ensure correct endpoint when starting
./server -m models/your-model.gguf --port 8080

# Test if server is running properly
curl http://localhost:8080/v1/models
```

#### **LiteLLM Provider Error**
If encountering "LLM Provider NOT provided" error:
- ✅ Ensure llama.cpp server is running on `http://localhost:8080`
- ✅ Use `/local` command to check server status
- ✅ llama.cpp models are automatically mapped to `openai/model-name` format

#### **Slow Model Loading**
- Ensure sufficient RAM
- Use smaller model versions (Q4_K_M vs Q8_0)
- Check disk space and I/O performance

#### **Poor Response Quality**
- Try larger model versions
- Adjust temperature parameters: `/model mistral --temperature 0.3`
- Ensure model suits the task type

## 🚀 Performance Optimization

### **Ollama Optimization**
```bash
# Set GPU acceleration (if NVIDIA GPU available)
ollama pull llama3.2 --gpu

# Adjust concurrent connections
OLLAMA_NUM_PARALLEL=2 ollama serve
```

### **llama.cpp Optimization**
```bash
# GPU acceleration
./server -m model.gguf -ngl 32

# Adjust thread count
./server -m model.gguf -t 8

# Memory mapping optimization
./server -m model.gguf --mlock
```

## 🔧 Advanced Configuration

### **Custom Endpoints**
DevMind supports custom Ollama and llama.cpp endpoint configuration.

### **Environment Variables**
```bash
# Ollama endpoint
export OLLAMA_HOST=http://localhost:11434

# llama.cpp endpoint
export LLAMACPP_HOST=http://localhost:8080
```

### **Multi-Server Support**
Multiple Ollama and llama.cpp instances can run simultaneously, and DevMind will automatically discover and manage them.

## 📊 Performance Comparison

| Model | Size | RAM Required | Inference Speed | Code Quality |
|------|------|---------|----------|----------|
| `mistral` | 7B | 8GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| `codellama:13b` | 13B | 16GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| `deepseek-coder` | 7B | 8GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| `mixtral` | 8x7B | 24GB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 🎯 Best Practices

### **Development Workflow**
1. **Quick Prototyping**: Use `mistral` or `phi3`
2. **Code Development**: Switch to `deepseek-coder` or `codellama:13b`
3. **Code Review**: Use `qwen2.5-coder` for deep analysis
4. **Complex Architecture**: Use `llama3.2` or `mixtral`

### **Resource Management**
- Choose appropriately sized models based on available memory
- Use `/local` command to monitor server status
- Regularly clean up unused models

### **Quality Assurance**
- Compare output quality across multiple models
- Choose specialized models for specific tasks
- Save best configurations as sessions

---

DevMind's local model support gives you complete privacy control and unlimited usage! 🚀