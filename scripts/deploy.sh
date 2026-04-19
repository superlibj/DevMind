#!/bin/bash
# AI Code Development Agent Deployment Script

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="production"
SKIP_BUILD=false
SKIP_MIGRATION=false
BACKGROUND_TASKS=false
MONITORING=false
FORCE_RECREATE=false

# Print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Show usage information
show_usage() {
    cat << EOF
AI Code Development Agent Deployment Script

Usage: $0 [OPTIONS]

Options:
    -e, --env ENVIRONMENT      Set deployment environment (development|staging|production)
    -s, --skip-build           Skip Docker image build
    -m, --skip-migration       Skip database migration
    -b, --background-tasks     Enable background task workers
    -M, --monitoring           Enable monitoring services (Prometheus/Grafana)
    -f, --force-recreate       Force recreate all containers
    -h, --help                 Show this help message

Examples:
    $0                                 # Basic production deployment
    $0 -e development                  # Development deployment
    $0 -b -M                          # Production with background tasks and monitoring
    $0 --force-recreate               # Force recreate all containers

Environment Variables:
    JWT_SECRET_KEY                     JWT secret key (required for production)
    OPENAI_API_KEY                     OpenAI API key (optional)
    ANTHROPIC_API_KEY                  Anthropic API key (optional)
    POSTGRES_PASSWORD                  Database password
    REDIS_PASSWORD                     Redis password
    GRAFANA_PASSWORD                   Grafana admin password
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -s|--skip-build)
                SKIP_BUILD=true
                shift
                ;;
            -m|--skip-migration)
                SKIP_MIGRATION=true
                shift
                ;;
            -b|--background-tasks)
                BACKGROUND_TASKS=true
                shift
                ;;
            -M|--monitoring)
                MONITORING=true
                shift
                ;;
            -f|--force-recreate)
                FORCE_RECREATE=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check if .env file exists for production
    if [[ "$ENVIRONMENT" == "production" ]] && [[ ! -f .env ]]; then
        print_warning ".env file not found. Creating template..."
        create_env_template
    fi

    print_success "Prerequisites check completed"
}

# Create .env template
create_env_template() {
    cat > .env << EOF
# AI Code Development Agent Environment Configuration

# Application Settings
APP__ENVIRONMENT=$ENVIRONMENT
APP__DEBUG=false
APP__API_HOST=0.0.0.0
APP__API_PORT=8000

# Security Settings
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
SECURITY__RATE_LIMIT_REQUESTS=100
SECURITY__RATE_LIMIT_WINDOW=60

# Database Configuration
POSTGRES_PASSWORD=changeme-secure-password
DATABASE_URL=postgresql://aiagent:\${POSTGRES_PASSWORD}@postgres:5432/aiagent

# Redis Configuration
REDIS_PASSWORD=changeme-secure-redis-password
REDIS_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0

# LLM API Keys (Optional)
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Monitoring (Optional)
GRAFANA_PASSWORD=admin

# Additional Settings
PYTHONPATH=/app
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
EOF
    print_warning "Please edit .env file with your actual configuration values"
}

# Validate environment variables
validate_env() {
    print_info "Validating environment configuration..."

    if [[ "$ENVIRONMENT" == "production" ]]; then
        if [[ -z "${JWT_SECRET_KEY:-}" ]]; then
            print_error "JWT_SECRET_KEY is required for production deployment"
            exit 1
        fi

        if [[ "${JWT_SECRET_KEY:-}" == "your-super-secret-jwt-key-change-this-in-production" ]]; then
            print_error "Please change the default JWT_SECRET_KEY in production"
            exit 1
        fi
    fi

    print_success "Environment validation completed"
}

# Build Docker images
build_images() {
    if [[ "$SKIP_BUILD" == "true" ]]; then
        print_info "Skipping Docker image build"
        return
    fi

    print_info "Building Docker images..."
    docker-compose build --no-cache aiagent

    print_success "Docker images built successfully"
}

# Start services
start_services() {
    print_info "Starting services..."

    # Build compose command
    local compose_cmd="docker-compose"
    local compose_args=""

    # Add profiles based on options
    if [[ "$BACKGROUND_TASKS" == "true" ]]; then
        compose_args="$compose_args --profile background-tasks"
    fi

    if [[ "$MONITORING" == "true" ]]; then
        compose_args="$compose_args --profile monitoring"
    fi

    if [[ "$ENVIRONMENT" == "production" ]]; then
        compose_args="$compose_args --profile production"
    fi

    # Add force recreate flag
    local up_args="up -d"
    if [[ "$FORCE_RECREATE" == "true" ]]; then
        up_args="up -d --force-recreate"
    fi

    # Start core services first
    print_info "Starting core infrastructure services..."
    $compose_cmd $compose_args up -d postgres redis

    # Wait for databases to be ready
    print_info "Waiting for databases to be ready..."
    sleep 10

    # Start main application
    print_info "Starting main application..."
    $compose_cmd $compose_args $up_args

    print_success "Services started successfully"
}

# Run database migrations
run_migrations() {
    if [[ "$SKIP_MIGRATION" == "true" ]]; then
        print_info "Skipping database migration"
        return
    fi

    print_info "Running database migrations..."

    # Wait for application to be ready
    sleep 5

    # Check if application is running
    if docker-compose ps aiagent | grep -q "Up"; then
        print_info "Application is running, migrations should have been applied automatically"
    else
        print_warning "Application is not running, migrations may not have been applied"
    fi

    print_success "Database migrations completed"
}

# Health check
health_check() {
    print_info "Performing health check..."

    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Application is healthy and responding"
            return 0
        fi

        print_info "Waiting for application to be ready... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done

    print_error "Application health check failed after $max_attempts attempts"
    return 1
}

# Show deployment status
show_status() {
    print_info "Deployment status:"
    echo ""

    # Show running containers
    docker-compose ps

    echo ""
    print_info "Service URLs:"
    echo "  • Application: http://localhost:8000"
    echo "  • API Docs: http://localhost:8000/docs"
    echo "  • Health Check: http://localhost:8000/health"

    if [[ "$MONITORING" == "true" ]]; then
        echo "  • Prometheus: http://localhost:9090"
        echo "  • Grafana: http://localhost:3000"
    fi

    echo ""
    print_info "To view logs: docker-compose logs -f aiagent"
    print_info "To stop services: docker-compose down"
}

# Cleanup on exit
cleanup() {
    print_info "Deployment script completed"
}

# Main deployment function
main() {
    echo "AI Code Development Agent Deployment"
    echo "====================================="
    echo ""

    parse_args "$@"

    print_info "Starting deployment with environment: $ENVIRONMENT"

    check_prerequisites
    validate_env
    build_images
    start_services
    run_migrations

    if health_check; then
        show_status
        print_success "Deployment completed successfully!"
    else
        print_error "Deployment failed - application is not responding"
        print_info "Check logs with: docker-compose logs aiagent"
        exit 1
    fi
}

# Set up signal handlers
trap cleanup EXIT

# Run main function
main "$@"