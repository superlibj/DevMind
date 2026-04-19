#!/bin/bash
# Post-installation setup for Ollama

echo "🎉 Setting up Ollama after installation..."

# Check if ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama not found. Installation may have failed."
    exit 1
fi

echo "✅ Ollama installation detected!"

# Start Ollama service
echo "🚀 Starting Ollama service..."
sudo systemctl enable ollama
sudo systemctl start ollama

# Wait for service to start
echo "⏳ Waiting for Ollama to initialize..."
sleep 5

# Check if Ollama is running
if systemctl is-active --quiet ollama; then
    echo "✅ Ollama service is running!"
else
    echo "🔧 Starting Ollama manually..."
    ollama serve &
    sleep 5
fi

# Test Ollama connection
echo "🔍 Testing Ollama connection..."
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✅ Ollama API is responding!"
else
    echo "⚠️  Ollama API not responding yet, trying to start..."
    ollama serve &
    sleep 5
fi

echo "📦 Installing recommended coding model..."
echo "This will download about 4GB for the model..."

# Install a good coding model
ollama pull qwen2.5-coder:7b

echo "🎯 Updating DevMind configuration..."

# Update .env to use Ollama
sed -i 's/DEFAULT_LLM_PROVIDER=.*/DEFAULT_LLM_PROVIDER=ollama/' /home/xiubli/workspace/aiagent/.env
sed -i 's/LOCAL_MODEL_NAME=.*/LOCAL_MODEL_NAME=qwen2.5-coder:7b/' /home/xiubli/workspace/aiagent/.env

echo "✅ Ollama setup complete!"
echo ""
echo "🚀 You can now test DevMind:"
echo "   python main.py --model qwen2.5-coder:7b"
echo ""
echo "💡 Available models:"
ollama list
echo ""
echo "🎉 DevMind is ready with free local AI!"