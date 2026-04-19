# llama.cpp Complete Setup Guide

## 🎯 Complete Setup Process

### **Step 1: Download and Build llama.cpp**

```bash
# 1. Clone llama.cpp repository
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# 2. Build the project (choose method suitable for your system)

# Linux/macOS (CPU version)
make

# Or, if you have NVIDIA GPU
make LLAMA_CUDA=1

# Or, if you have AMD GPU
make LLAMA_HIPBLAS=1

# Or, use CMake build
mkdir build
cd build
cmake ..
make -j 8
cd ..
```

### **Step 2: Download Model Files**

You need to download GGUF format model files. Here are some recommended programming-related models:

#### **Method 1: Download using Hugging Face Hub**
```bash
# Install huggingface_hub
pip install huggingface_hub

# Download models to models directory
mkdir -p models

# Download CodeQwen model (recommended)
huggingface-cli download Qwen/CodeQwen1.5-7B-Chat-GGUF CodeQwen1.5-7B-Chat.Q4_K_M.gguf --local-dir models

# Download Code Llama model
huggingface-cli download TheBloke/CodeLlama-7B-Instruct-GGUF CodeLlama-7B-Instruct.Q4_K_M.gguf --local-dir models

# Download DeepSeek Coder model
huggingface-cli download TheBloke/deepseek-coder-6.7b-instruct-GGUF deepseek-coder-6.7b-instruct.Q4_K_M.gguf --local-dir models
```

#### **Method 2: Manual Download**
Visit the following links for manual download:
- [CodeQwen Models](https://huggingface.co/Qwen/CodeQwen1.5-7B-Chat-GGUF/tree/main)
- [Code Llama Models](https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/tree/main)
- [DeepSeek Coder Models](https://huggingface.co/TheBloke/deepseek-coder-6.7b-instruct-GGUF/tree/main)

Download `.gguf` files to the `llama.cpp/models/` directory.

### **Step 3: Start Server**

```bash
# Run in the llama.cpp directory
cd llama.cpp

# Start server - use your downloaded model file
./server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 4096

# Or use Code Llama
./server -m models/CodeLlama-7B-Instruct.Q4_K_M.gguf --port 8080 --ctx-size 4096

# Or use DeepSeek Coder
./server -m models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf --port 8080 --ctx-size 4096
```

### **Step 4: Test Server**

```bash
# Test in another terminal
curl http://localhost:8080/v1/models

# Should return JSON like this:
# {"object":"list","data":[{"id":"model","object":"model"}]}
```

### **Step 5: Use with DevMind**

```bash
# Start DevMind
python main.py

# Check local models
devmind> /local

# Switch to llama.cpp model
devmind> /model llama-cpp-local

# Start conversation
devmind> Hello, can you help me write code?
```

## 📂 **Directory Structure Example**

After setup is complete, your directory should look like this:

```
/home/your-username/
├── llama.cpp/                    # llama.cpp main directory
│   ├── server                    # Built server executable
│   ├── models/                   # Model files directory
│   │   ├── CodeQwen1.5-7B-Chat.Q4_K_M.gguf
│   │   ├── CodeLlama-7B-Instruct.Q4_K_M.gguf
│   │   └── deepseek-coder-6.7b-instruct.Q4_K_M.gguf
│   └── ...
└── aiagent/                      # DevMind directory
    ├── main.py
    └── ...
```

## ⚡ **Quick Startup Script**

Create a startup script for convenience:

```bash
# Create startup script
cat > start_llamacpp.sh << 'EOF'
#!/bin/bash
cd /path/to/llama.cpp
echo "Starting llama.cpp server..."
echo "Model: CodeQwen1.5-7B-Chat"
echo "Port: 8080"
echo "Press Ctrl+C to stop server"
echo ""
./server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 4096
EOF

# Set execute permissions
chmod +x start_llamacpp.sh

# Run
./start_llamacpp.sh
```

## 🔧 **Recommended Configurations**

### **Lightweight Configuration (8GB RAM)**
```bash
./server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 2048 --threads 4
```

### **Standard Configuration (16GB RAM)**
```bash
./server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 4096 --threads 8
```

### **High-Performance Configuration (32GB+ RAM, GPU)**
```bash
./server -m models/CodeLlama-13B-Instruct.Q4_K_M.gguf --port 8080 --ctx-size 8192 --n-gpu-layers 32
```

## 🔍 **Troubleshooting**

### **Build Failed**
```bash
# Update system dependencies
# Ubuntu/Debian
sudo apt update && sudo apt install build-essential cmake

# macOS
brew install cmake

# Clean and rebuild
make clean
make
```

### **Model File Not Found**
```bash
# Check file path
ls -la models/

# Ensure file exists and has correct permissions
chmod 644 models/*.gguf
```

### **Server Start Failed**
```bash
# Check if port is occupied
netstat -an | grep 8080

# Try different port
./server -m models/your-model.gguf --port 8081
```

### **Insufficient Memory**
```bash
# Use smaller model
# Download Q4_K_S (smaller) instead of Q4_K_M (medium) version
# Or reduce context size
./server -m models/your-model.gguf --port 8080 --ctx-size 1024
```

## 💡 **Tips**

1. **Model Selection**:
   - Q4_K_M: Balance of quality and speed
   - Q4_K_S: Faster but slightly lower quality
   - Q8_0: Highest quality but slowest

2. **Performance Optimization**:
   - Use `--threads` to set CPU thread count
   - Use `--n-gpu-layers` parameter when GPU available
   - Adjust `--ctx-size` to balance memory and functionality

3. **Background Running**:
   ```bash
   nohup ./server -m models/your-model.gguf --port 8080 > server.log 2>&1 &
   ```

Now you can follow these steps to set up llama.cpp and use local models in DevMind!