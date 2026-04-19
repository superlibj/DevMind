# AI Code Development Agent - Deployment Guide

This guide provides comprehensive instructions for deploying the AI Code Development Agent in various environments.

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- Git
- At least 4GB RAM and 20GB disk space
- API keys for AI providers (OpenAI, Anthropic, etc.)

### 2. Basic Deployment

```bash
# Clone the repository
git clone <repository-url>
cd aiagent

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your configuration

# Deploy with Docker Compose
./scripts/deploy.sh
```

The application will be available at http://localhost:8000

## Deployment Options

### Development Environment

```bash
# Quick development setup
./scripts/deploy.sh -e development

# With background tasks and monitoring
./scripts/deploy.sh -e development -b -M
```

### Production Environment

```bash
# Production deployment with all services
./scripts/deploy.sh -e production -b -M

# Force recreate all containers
./scripts/deploy.sh -e production -f
```

### Staging Environment

```bash
# Staging deployment for testing
./scripts/deploy.sh -e staging -M
```

## Configuration

### Environment Variables

Key configuration variables in `.env`:

```bash
# Application
APP__ENVIRONMENT=production
APP__DEBUG=false

# Security (REQUIRED for production)
SECURITY__JWT_SECRET_KEY="your-super-secret-key"
POSTGRES_PASSWORD="secure-database-password"
REDIS_PASSWORD="secure-redis-password"

# AI Providers (at least one required)
OPENAI_API_KEY="sk-your-openai-key"
ANTHROPIC_API_KEY="your-anthropic-key"

# Monitoring (optional)
GRAFANA_PASSWORD="admin"
```

### Database Configuration

The application uses PostgreSQL for persistent storage:

- **Host**: postgres (in Docker network)
- **Database**: aiagent
- **User**: aiagent
- **Port**: 5432

Default initialization creates:
- Admin user: `admin` / `admin123`
- Test user: `testuser` / `test123`

### Security Settings

Key security configurations:
- JWT tokens with configurable expiration
- Rate limiting with token bucket algorithm
- CORS configuration for web access
- Automatic security scanning of generated code

## Service Architecture

### Core Services

1. **aiagent**: Main application (FastAPI + WebSocket)
2. **postgres**: Database for persistent storage
3. **redis**: Cache and session storage

### Optional Services

4. **nginx**: Reverse proxy and load balancer
5. **prometheus**: Metrics collection
6. **grafana**: Monitoring dashboards
7. **worker**: Background task processing

### Service URLs

- Application: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Prometheus: http://localhost:9090 (if enabled)
- Grafana: http://localhost:3000 (if enabled)

## Health Monitoring

### Health Endpoints

- `GET /health` - Basic health status
- `GET /health/detailed` - Comprehensive health info
- `GET /health/ready` - Readiness for traffic
- `GET /health/live` - Liveness check

### Monitoring Setup

Enable monitoring with the `-M` flag:

```bash
./scripts/deploy.sh -M
```

This starts Prometheus and Grafana for metrics visualization.

## Testing

### Running Tests

```bash
# All tests
./scripts/run_tests.sh

# Unit tests only
./scripts/run_tests.sh -t unit

# Integration tests with coverage
./scripts/run_tests.sh -t integration -v

# Fast tests without coverage
./scripts/run_tests.sh -f -c
```

### Test Types

- **Unit**: Component-level testing
- **Integration**: API and service testing
- **E2E**: End-to-end functionality testing
- **Security**: Security-focused testing
- **Performance**: Load and performance testing

## Security

### Security Scanning

All AI-generated code is automatically scanned using:
- **Bandit**: Python security linting
- **Semgrep**: Multi-language static analysis
- **Safety**: Dependency vulnerability scanning

### Authentication

- JWT-based authentication
- Role-based permissions (admin, premium, basic)
- Rate limiting per user type

### Network Security

- CORS configuration
- Reverse proxy support
- SSL/TLS termination at nginx

## Backup and Recovery

### Database Backup

```bash
# Manual backup
docker-compose exec postgres pg_dump -U aiagent aiagent > backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U aiagent aiagent < backup.sql
```

### Volume Backup

```bash
# Backup persistent volumes
docker run --rm -v aiagent_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
docker run --rm -v aiagent_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_backup.tar.gz -C /data .
```

## Scaling

### Horizontal Scaling

Multiple application instances can be deployed behind a load balancer:

```yaml
# docker-compose.override.yml
services:
  aiagent:
    scale: 3
  nginx:
    depends_on:
      - aiagent
```

### Resource Limits

Configure resource limits in docker-compose.yml:

```yaml
services:
  aiagent:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

## Troubleshooting

### Common Issues

1. **Application won't start**
   ```bash
   # Check logs
   docker-compose logs aiagent

   # Verify environment variables
   docker-compose config
   ```

2. **Database connection issues**
   ```bash
   # Check database status
   docker-compose ps postgres

   # Test connection
   docker-compose exec postgres psql -U aiagent -d aiagent -c "SELECT 1;"
   ```

3. **API key errors**
   ```bash
   # Verify API keys are set
   docker-compose exec aiagent env | grep API_KEY
   ```

4. **Memory issues**
   ```bash
   # Check resource usage
   docker stats

   # Monitor logs for OOM errors
   dmesg | grep -i "killed process"
   ```

### Log Analysis

```bash
# Application logs
docker-compose logs -f aiagent

# Database logs
docker-compose logs -f postgres

# All service logs
docker-compose logs -f

# Specific service logs with timestamps
docker-compose logs -f -t aiagent
```

### Performance Tuning

1. **Database optimization**
   - Adjust PostgreSQL configuration
   - Monitor slow queries
   - Optimize indexes

2. **Redis optimization**
   - Configure memory limits
   - Set appropriate TTL values
   - Monitor cache hit rates

3. **Application optimization**
   - Adjust worker count
   - Configure connection pools
   - Enable gzip compression

## Maintenance

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and redeploy
./scripts/deploy.sh -f
```

### Cleanup

```bash
# Remove stopped containers
docker-compose down

# Remove all data (WARNING: DATA LOSS)
docker-compose down -v

# Clean up Docker system
docker system prune -a
```

### Log Rotation

Configure log rotation to prevent disk space issues:

```bash
# Add to crontab
0 2 * * * docker-compose exec aiagent find /app/logs -name "*.log" -mtime +7 -delete
```

## Production Checklist

- [ ] Environment variables configured
- [ ] Strong passwords and secrets
- [ ] SSL/TLS certificates configured
- [ ] Reverse proxy configured
- [ ] Monitoring enabled
- [ ] Backup strategy implemented
- [ ] Log rotation configured
- [ ] Resource limits set
- [ ] Health checks configured
- [ ] Security scanning enabled

## Support

For additional support:
1. Check the application logs
2. Review the health check endpoints
3. Consult the API documentation at `/docs`
4. Review the monitoring dashboards

## Advanced Configuration

### Custom Docker Images

Build custom images with additional dependencies:

```dockerfile
FROM aiagent:latest
RUN pip install additional-package
COPY custom-config.yaml /app/config/
```

### External Services

Configure external services in docker-compose.override.yml:

```yaml
services:
  aiagent:
    environment:
      - EXTERNAL_API_URL=https://api.example.com
    external_links:
      - external-service
```

### Multi-Environment Setup

Use Docker Compose profiles for different environments:

```bash
# Development
docker-compose --profile development up

# Production
docker-compose --profile production up
```