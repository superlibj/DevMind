#!/bin/bash
# DevMind Configuration Helper

echo "🔧 DevMind Configuration Helper"
echo "==============================="
echo ""

# Function to configure API keys
configure_api() {
    echo "Please choose your preferred LLM provider:"
    echo "1) OpenAI (GPT-4) - Paid API"
    echo "2) Anthropic (Claude) - Paid API"
    echo "3) Ollama (Local Models) - Free"
    echo "4) Check current configuration"
    echo ""
    read -p "Enter your choice (1-4): " choice

    case $choice in
        1)
            read -p "Enter your OpenAI API key (starts with sk-): " openai_key
            if [[ $openai_key == sk-* ]]; then
                sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$openai_key/" .env
                sed -i "s/DEFAULT_LLM_PROVIDER=.*/DEFAULT_LLM_PROVIDER=openai/" .env
                echo "✅ OpenAI API key configured!"
            else
                echo "❌ Invalid OpenAI API key format"
                exit 1
            fi
            ;;
        2)
            read -p "Enter your Anthropic API key (starts with sk-ant-): " anthropic_key
            if [[ $anthropic_key == sk-ant-* ]]; then
                sed -i "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$anthropic_key/" .env
                sed -i "s/DEFAULT_LLM_PROVIDER=.*/DEFAULT_LLM_PROVIDER=anthropic/" .env
                echo "✅ Anthropic API key configured!"
            else
                echo "❌ Invalid Anthropic API key format"
                exit 1
            fi
            ;;
        3)
            echo "🚀 Setting up Ollama (free local models)..."
            ./setup_ollama.sh
            ;;
        4)
            echo "📋 Current Configuration:"
            echo "========================"
            grep "DEFAULT_LLM_PROVIDER" .env
            grep "OPENAI_API_KEY" .env | sed 's/=.*/=***REDACTED***/'
            grep "ANTHROPIC_API_KEY" .env | sed 's/=.*/=***REDACTED***/'
            grep "LOCAL_MODEL" .env
            ;;
        *)
            echo "❌ Invalid choice"
            exit 1
            ;;
    esac
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    exit 1
fi

configure_api

echo ""
echo "🎉 Configuration complete!"
echo "💡 You can now run: devmind"
echo "📖 For help: devmind --help"