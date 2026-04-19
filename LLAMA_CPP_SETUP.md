# llama.cpp Complete Setup Guide

## 🎯 Complete Setup Process

### **Step 1: Install Dependencies**

llama.cpp now uses **CMake** as the primary build system. Install required dependencies first:

```bash
# Fedora/RHEL
sudo dnf install cmake gcc-c++ make pkgconfig -y

# Ubuntu/Debian
sudo apt update && sudo apt install cmake build-essential pkg-config -y

# macOS
brew install cmake

# Arch Linux
sudo pacman -S cmake base-devel pkg-config --noconfirm
```

### **Step 2: Download and Build llama.cpp**

```bash
# 1. Clone llama.cpp repository
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# 2. Build using CMake (RECOMMENDED - Modern Build System)
mkdir build
cd build

# Basic CPU build
cmake ..
make -j$(nproc)
cd ..

# 3. GPU Acceleration Options (if you have compatible hardware)

# For NVIDIA GPU (CUDA)
cmake .. -DGGML_CUDA=ON
make -j$(nproc)

# For AMD GPU (ROCm/HIP)
cmake .. -DGGML_HIPBLAS=ON
make -j$(nproc)

# For Apple Silicon (Metal)
cmake .. -DGGML_METAL=ON
make -j$(nproc)

# For Intel GPU (SYCL)
cmake .. -DGGML_SYCL=ON
make -j$(nproc)
```

### **Legacy Make Build (Deprecated but still works)**

```bash
# Only use if CMake is not available
# Basic CPU build
make

# With GPU support
make LLAMA_CUDA=1      # NVIDIA
make LLAMA_HIPBLAS=1   # AMD
make LLAMA_METAL=1     # Apple Silicon
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

# For CMake builds (recommended)
./build/bin/llama-server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 4096

# For legacy Make builds
./server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 4096

# Alternative models:
# Code Llama
./build/bin/llama-server -m models/CodeLlama-7B-Instruct.Q4_K_M.gguf --port 8080 --ctx-size 4096

# DeepSeek Coder
./build/bin/llama-server -m models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf --port 8080 --ctx-size 4096
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
│   ├── build/                    # CMake build directory
│   │   └── bin/
│   │       ├── llama-server      # CMake built server executable
│   │       ├── llama-cli         # Command line interface
│   │       └── ...               # Other tools
│   ├── server                    # Legacy Make built executable (if used)
│   ├── models/                   # Model files directory
│   │   ├── CodeQwen1.5-7B-Chat.Q4_K_M.gguf
│   │   ├── CodeLlama-7B-Instruct.Q4_K_M.gguf
│   │   └── deepseek-coder-6.7b-instruct.Q4_K_M.gguf
│   ├── CMakeLists.txt           # CMake configuration
│   ├── Makefile                 # Legacy Makefile (redirects to CMake)
│   └── ...
└── aiagent/                      # DevMind directory
    ├── main.py
    └── ...
```

## ⚡ **Quick Startup Script**

Create a startup script for convenience:

```bash
# Create smart startup script that detects build type
cat > start_llamacpp.sh << 'EOF'
#!/bin/bash
cd /path/to/llama.cpp
echo "Starting llama.cpp server..."
echo "Model: CodeQwen1.5-7B-Chat"
echo "Port: 8080"
echo "Press Ctrl+C to stop server"
echo ""

# Use CMake build if available, fallback to Make build
if [ -f "./build/bin/llama-server" ]; then
    echo "Using CMake build..."
    ./build/bin/llama-server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 4096
elif [ -f "./server" ]; then
    echo "Using Make build..."
    ./server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 4096
else
    echo "Error: No llama.cpp server executable found!"
    echo "Please build llama.cpp first using CMake or Make"
    exit 1
fi
EOF

# Set execute permissions
chmod +x start_llamacpp.sh

# Run
./start_llamacpp.sh
```

## 🔧 **Recommended Configurations**

### **Lightweight Configuration (8GB RAM)**
```bash
# CMake build
./build/bin/llama-server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 2048 --threads 4

# Legacy Make build
./server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 2048 --threads 4
```

### **Standard Configuration (16GB RAM)**
```bash
# CMake build
./build/bin/llama-server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 4096 --threads 8

# Legacy Make build
./server -m models/CodeQwen1.5-7B-Chat.Q4_K_M.gguf --port 8080 --ctx-size 4096 --threads 8
```

### **High-Performance Configuration (32GB+ RAM, GPU)**
```bash
# CMake build with GPU
./build/bin/llama-server -m models/CodeLlama-13B-Instruct.Q4_K_M.gguf --port 8080 --ctx-size 8192 --n-gpu-layers 32

# Legacy Make build with GPU
./server -m models/CodeLlama-13B-Instruct.Q4_K_M.gguf --port 8080 --ctx-size 8192 --n-gpu-layers 32
```

## 🔍 **Troubleshooting**

### **CMake Not Found**
```bash
# Install CMake first
# Fedora/RHEL
sudo dnf install cmake gcc-c++ make -y

# Ubuntu/Debian
sudo apt update && sudo apt install cmake build-essential -y

# macOS
brew install cmake

# Arch Linux
sudo pacman -S cmake base-devel --noconfirm
```

### **Build Failed**
```bash
# For CMake builds
cd llama.cpp
rm -rf build  # Clean previous build
mkdir build && cd build
cmake ..
make -j$(nproc)

# For legacy Make builds
make clean
make

# If CMake configuration fails, try:
cmake .. -DCMAKE_BUILD_TYPE=Release
```

### **"Build system changed" Error**
```bash
# This happens when using old Makefile directly
# The project now uses CMake primarily

# Solution: Use CMake instead
mkdir build && cd build
cmake ..
make -j$(nproc)

# Or if you must use Make:
make clean
make  # Will redirect to CMake automatically
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