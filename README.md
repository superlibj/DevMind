# AI Code Development Agent

A comprehensive AI-powered development assistant that provides secure code generation, review, refactoring, and debugging capabilities.

## Features

- **Multi-Provider LLM Support**: Seamlessly switch between OpenAI, Anthropic Claude, and local models
- **Security-First Code Generation**: Automatic vulnerability scanning with Bandit, Semgrep, and Safety
- **ReAct Agent Pattern**: Production-proven reasoning and acting cycles for complex tasks
- **Tool Integration**: Standardized tool access for git, vim, and file operations
- **Real-time Web Interface**: REST API with WebSocket support for live chat
- **Docker Deployment**: Production-ready containerized deployment

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd aiagent
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Development Server**
   ```bash
   uvicorn src.api.main:app --reload
   ```

4. **Run with Docker**
   ```bash
   docker-compose up -d
   ```

## Architecture

### Core Components

- **Agent System**: ReAct pattern implementation with memory management
- **LLM Abstraction**: Universal provider interface supporting 100+ models
- **Security Layer**: Comprehensive code scanning and vulnerability detection
- **Tool Integration**: ACP-compliant tool access with safety controls
- **Web Interface**: FastAPI-based REST API with WebSocket chat

### Security Features

- Automatic SAST/SCA scanning of all generated code
- Input validation and injection prevention
- Sandboxed code execution with resource limits
- JWT authentication with role-based access control
- Rate limiting and request validation

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

Key configuration areas:
- **LLM Providers**: API keys and model selection
- **Security**: Scanning tools and validation rules
- **Database**: PostgreSQL connection settings
- **Redis**: Cache and session configuration
- **Tools**: Integration limits and allowed operations

## API Documentation

Once running, visit:
- API Documentation: `http://localhost:8000/docs`
- Interactive API: `http://localhost:8000/redoc`

## Development

### Project Structure

```
aiagent/
├── src/
│   ├── core/                 # Core agent and AI logic
│   ├── domain/              # Business logic and services
│   ├── api/                 # Web API and routes
│   └── web/                 # Web interface
├── config/                  # Configuration management
├── tests/                   # Test suite
├── scripts/                 # Setup and deployment scripts
└── monitoring/              # Observability configuration
```

### Testing

```bash
pytest tests/ -v --cov=src
```

### Code Quality

```bash
black src/
mypy src/
bandit -r src/
```

## Deployment

### Production Deployment

```bash
docker-compose -f docker-compose.yml up -d
```

### Monitoring

- Prometheus metrics: `http://localhost:9090`
- Grafana dashboards: `http://localhost:3000`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite and security checks
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions, please use the GitHub issue tracker.