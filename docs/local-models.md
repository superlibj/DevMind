# Local Models Setup Guide

DevMind supports running powerful AI models locally through Ollama and llama.cpp, allowing you to use AI assistance without depending on cloud services.

## 🎯 Overview

### Benefits of Local Models
- **Privacy**: Your code and conversations stay on your machine
- **Cost-effective**: No API usage costs
- **Offline capability**: Work without internet connection
- **Customization**: Fine-tune models for specific needs

### Supported Platforms
- **Ollama**: Easy model management with automatic downloads
- **llama.cpp**: High-performance GGUF model support

## 🚀 Ollama Setup

### Installation

#### Linux/macOS
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### Windows
Download from [ollama.com](https://ollama.com/download) and install.

### Verify Installation
```bash
ollama --version
```

### Download Models
```bash
# Code-specialized models (recommended)
ollama pull qwen2.5-coder:7b      # 7B multilingual code model
ollama pull codellama:13b          # 13B code generation
ollama pull deepseek-coder         # Programming specialist

# General purpose models
ollama pull llama3.2:8b           # Latest Llama model
ollama pull mistral:7b            # Fast general model
ollama pull phi3:mini             # Compact model
```

### Configuration for DevMind

Update your `.env` file:
```bash
DEFAULT_LLM_PROVIDER=local
LOCAL_MODEL_NAME=qwen2.5-coder:7b
LOCAL_MODEL_ENDPOINT=http://localhost:11434
```

## ⚙️ llama.cpp Setup

### Installation

#### Build from Source
```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build && cd build
cmake .. -DLLAMA_CUBLAS=ON  # For NVIDIA GPU support
make -j
```

#### Download Pre-built
Download binaries from the [releases page](https://github.com/ggerganov/llama.cpp/releases).

### Download GGUF Models

Popular GGUF models for coding:
```bash
# Create models directory
mkdir -p models

# Download CodeQwen model (example)
wget https://huggingface.co/Qwen/CodeQwen1.5-7B-Chat-GGUF/resolve/main/codeqwen-1_5-7b-chat-q4_0.gguf -O models/codeqwen.gguf
```

### Start llama.cpp Server
```bash
./server -m models/codeqwen.gguf \
         --host 0.0.0.0 \
         --port 8080 \
         --ctx-size 4096 \
         --alias codeqwen
```

### Configuration for DevMind
```bash
DEFAULT_LLM_PROVIDER=local
LOCAL_MODEL_NAME=llama-cpp
LOCAL_MODEL_ENDPOINT=http://localhost:8080/v1
```

## 📋 Recommended Models

### For Code Development

| Model | Size | Strengths | Use Case |
|-------|------|-----------|----------|
| `qwen2.5-coder:7b` | 4.3GB | Multilingual, fast | General coding |
| `codellama:13b` | 7.4GB | Code completion | Large projects |
| `deepseek-coder` | 3.8GB | Algorithm focused | Problem solving |
| `starcoder2:7b` | 4.0GB | Code quality | Code review |

### For General Chat

| Model | Size | Strengths | Use Case |
|-------|------|-----------|----------|
| `llama3.2:8b` | 4.7GB | Latest, balanced | General assistance |
| `mistral:7b` | 4.1GB | Fast responses | Quick queries |
| `phi3:mini` | 2.3GB | Compact, efficient | Resource-limited |

### For Specialized Tasks

| Model | Size | Specialization | Best For |
|-------|------|----------------|----------|
| `llama3.1:70b` | 40GB | Reasoning | Complex problems |
| `mixtral:8x7b` | 26GB | Mixture of experts | Diverse tasks |
| `llama3.2:3b` | 2.0GB | Lightweight | Fast responses |

## 🔧 Usage in DevMind

### Starting with Local Model
```bash
# Start with specific local model
python main.py --model qwen2.5-coder:7b

# List available models
python main.py --list-models
```

### Switching Models in Session
```bash
devmind> /model qwen2.5-coder:7b
✓ Switched to qwen2.5-coder:7b
Provider: ollama
Description: Qwen2.5 Coder 7B - Strong multilingual coding model

devmind> /model codellama:13b
✓ Switched to codellama:13b
Provider: ollama
Description: Code Llama 13B - Enhanced coding capabilities
```

## 🏎️ Performance Optimization

### Hardware Requirements

#### Minimum Requirements
- **RAM**: 8GB (for 7B models)
- **Storage**: 10GB free space
- **CPU**: Modern multi-core processor

#### Recommended Hardware
- **RAM**: 16GB+ (for 13B models)
- **GPU**: NVIDIA RTX series (for GPU acceleration)
- **Storage**: SSD for faster model loading

### GPU Acceleration

#### NVIDIA CUDA (Ollama)
```bash
# Ollama automatically uses CUDA if available
ollama pull qwen2.5-coder:7b
```

#### NVIDIA CUDA (llama.cpp)
```bash
# Build with CUDA support
cmake .. -DLLAMA_CUBLAS=ON
make -j

# Run with GPU layers
./server -m model.gguf -ngl 35  # Use GPU for 35 layers
```

#### Apple Metal (macOS)
```bash
# llama.cpp automatically uses Metal on Apple Silicon
./server -m model.gguf -ngl 35
```

### Memory Management

#### Reduce Context Size
```bash
# For Ollama (via modelfile)
ollama create mymodel -f Modelfile
# Add: PARAMETER num_ctx 2048

# For llama.cpp
./server -m model.gguf --ctx-size 2048
```

#### Use Smaller Models
- Start with 3B-7B models for development
- Use 13B+ models only for complex tasks
- Consider quantized models (Q4_0, Q5_0) for lower memory usage

## 🔍 Troubleshooting

### Common Issues

#### Model Not Loading
```bash
# Check Ollama service
ollama list
ollama ps

# Restart Ollama service
ollama serve
```

#### Out of Memory
```bash
# Use smaller model
ollama pull qwen2.5-coder:3b

# Reduce context size
# Edit model parameters in Ollama
```

#### Slow Responses
```bash
# Check GPU usage
nvidia-smi  # For NVIDIA

# Increase GPU layers (llama.cpp)
./server -m model.gguf -ngl 40

# Use quantized model
ollama pull qwen2.5-coder:7b-q4_0
```

#### Connection Issues
```bash
# Check service is running
curl http://localhost:11434/api/version  # Ollama
curl http://localhost:8080/v1/models    # llama.cpp

# Restart services
ollama serve
./server -m model.gguf
```

### Model Quality Issues

#### Poor Code Generation
- Try different models: `codellama`, `deepseek-coder`, `starcoder2`
- Increase model size: upgrade from 7B to 13B
- Adjust temperature settings in DevMind

#### Inconsistent Responses
- Use newer models: `llama3.2` vs `llama2`
- Check model quantization: prefer Q4_0 or higher
- Ensure sufficient RAM for model size

## 📊 Model Comparison

### Performance Benchmarks (Approximate)

| Model | Code Quality | Speed | Memory | Best For |
|-------|-------------|-------|--------|----------|
| `qwen2.5-coder:7b` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 5GB | Balanced coding |
| `codellama:13b` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 8GB | Complex code |
| `deepseek-coder` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 4GB | Algorithms |
| `llama3.2:8b` | ⭐⭐⭐ | ⭐⭐⭐⭐ | 5GB | General chat |
| `phi3:mini` | ⭐⭐ | ⭐⭐⭐⭐⭐ | 2GB | Fast responses |

### Language Support

| Model | Python | JavaScript | Java | C++ | Go | Rust |
|-------|--------|------------|------|-----|-----|------|
| `qwen2.5-coder` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `codellama` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| `deepseek-coder` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| `starcoder2` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

## 🎯 Getting Started

### Quick Setup (Recommended)
```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Download recommended model
ollama pull qwen2.5-coder:7b

# 3. Configure DevMind
echo "DEFAULT_LLM_PROVIDER=local" >> .env
echo "LOCAL_MODEL_NAME=qwen2.5-coder:7b" >> .env

# 4. Start DevMind
python main.py --model qwen2.5-coder:7b
```

### Advanced Setup (GPU Acceleration)
```bash
# 1. Install CUDA drivers (NVIDIA)
# 2. Install Ollama with GPU support
# 3. Pull larger model
ollama pull codellama:13b

# 4. Test GPU usage
ollama run codellama:13b "Write a Python function"
```

## 💡 Best Practices

### Model Selection
- **Start small**: Begin with 7B models, upgrade as needed
- **Task-specific**: Use code models for programming, general models for chat
- **Test locally**: Try models with `ollama run` before configuring DevMind

### Resource Management
- **Monitor RAM**: Check `htop` or `nvidia-smi` during usage
- **Close unused models**: Use `ollama stop <model>` to free memory
- **Batch operations**: Group similar tasks to avoid model switching overhead

### Development Workflow
- **Code review**: Use larger models (13B+) for complex code analysis
- **Quick coding**: Use 7B models for rapid prototyping
- **Documentation**: General models work well for writing docs

This setup provides a complete local AI development environment that rivals cloud-based solutions while maintaining privacy and control.