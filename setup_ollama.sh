#!/bin/bash
# Setup script to install and configure Ollama for DevMind

echo "🚀 Setting up Ollama for DevMind..."

# Install Ollama
echo "📥 Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
echo "🔧 Starting Ollama service..."
ollama serve &
sleep 5

# Pull recommended models for coding
echo "📦 Installing recommended coding models..."
echo "This will take a few minutes depending on your internet speed..."

# Install a good general-purpose coding model
ollama pull qwen2.5-coder:7b

# Install a smaller, faster model for quick tasks
ollama pull codellama:7b

# Wait for models to install
echo "⏳ Waiting for models to download..."
sleep 10

echo "✅ Ollama setup complete!"
echo "🎯 Configuring DevMind to use Ollama..."

# Update .env file to use Ollama
sed -i 's/DEFAULT_LLM_PROVIDER=openai/DEFAULT_LLM_PROVIDER=ollama/' /home/xiubli/workspace/aiagent/.env
sed -i 's/LOCAL_MODEL_ENDPOINT=http:\/\/localhost:11434/LOCAL_MODEL_ENDPOINT=http:\/\/localhost:11434/' /home/xiubli/workspace/aiagent/.env
sed -i 's/LOCAL_MODEL_NAME=codellama/LOCAL_MODEL_NAME=qwen2.5-coder:7b/' /home/xiubli/workspace/aiagent/.env

echo "🎉 DevMind is now configured to use Ollama!"
echo "💡 Available models:"
ollama list

echo ""
echo "🚀 You can now run: devmind"
echo "🔧 To change models later: ollama pull <model-name>"
echo "📖 Popular coding models: qwen2.5-coder, codellama, deepseek-coder, starcoder2"