# EMR Backend API - Production Deployment Guide

## Architecture Overview

The application has been refactored for production with clean architecture:

```
backend-api-python/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration from .env
│   ├── models.py           # Pydantic models
│   ├── prompts.py          # System prompts
│   ├── dependencies.py     # DI container
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py       # API endpoints
│   └── services/
│       ├── __init__.py
│       ├── session_service.py  # Session management
│       └── chat_service.py     # Chat business logic
├── main_v4.py              # Production app entry point
├── Dockerfile              # Development
├── Dockerfile.prod         # Production with workers
├── docker-compose.prod.yml # Production stack
└── requirements.txt        # Updated dependencies
```

## Key Improvements

### 1. **Clean Architecture**
- ✅ Separation of concerns (API, Services, Models, Config)
- ✅ Dependency injection for testability
- ✅ Business logic in service layer
- ✅ Configuration management from .env

### 2. **Production Features**
- ✅ Multiple worker support
- ✅ Redis session storage (optional)
- ✅ Proper logging configuration
- ✅ Health checks
- ✅ Error handling

### 3. **Scalability**
- ✅ Horizontal scaling with workers
- ✅ Session storage decoupled from app instances
- ✅ Configurable via environment variables

## Deployment Options

### Development
```bash
# Use existing setup
docker-compose up -d
```

### Production
```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d
```

## Environment Configuration

All settings are managed through your existing `.env` file:

```env
# Existing settings (no changes needed)
GROQ_API_KEY=gsk_ZzLxWO5T6JpODWmSISaQBd9D8eT
FHIR_SERVER_URL=http://10.201.205.101:8007/
FHIR_USERNAME=fhiruser
FHIR_PASSWORD=Password@123
PORT=8004
CORS_ORIGIN=http://localhost:3004
LOG_LEVEL=info
VITE_API_URL=http://localhost:8004

# Optional production settings
WORKERS=4                    # Number of worker processes
REDIS_URL=redis://redis:6379 # For session storage
```

## Production Features

### 1. **Multiple Workers**
```bash
# Configure in .env
WORKERS=4

# Or override in docker-compose
environment:
  WORKERS: 8
```

### 2. **Session Storage**
- **Development**: In-memory (current)
- **Production**: Redis (configured automatically)

### 3. **Monitoring**
```bash
# Health check
curl http://localhost:8004/health

# Container health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## Migration Steps

### Option 1: Gradual Migration (Recommended)
1. Test new version alongside old:
   ```bash
   # Build new version
   docker-compose build backend-api
   docker-compose up -d backend-api
   ```

2. Verify functionality matches old version
3. Switch production when ready

### Option 2: Production Deployment
```bash
# Deploy production stack
docker-compose -f docker-compose.prod.yml up -d

# Monitor logs
docker-compose -f docker-compose.prod.yml logs -f backend-api
```

## Key Benefits

1. **Maintainability**: Clean separation of concerns
2. **Scalability**: Multi-worker support
3. **Testability**: Dependency injection
4. **Configuration**: Environment-driven
5. **Production-Ready**: Proper logging, health checks, error handling

## API Compatibility

✅ **No breaking changes** - same endpoints:
- `POST /api/chat`
- `DELETE /api/patient/{patient_id}/session`  
- `GET /health`

The refactored version maintains 100% API compatibility while improving code structure and production readiness.