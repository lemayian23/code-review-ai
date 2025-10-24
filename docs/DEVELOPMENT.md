# Code Review AI - Development Guide

## Overview

This guide covers setting up a development environment, contributing to the project, and understanding the codebase architecture.

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git
- Node.js (for load testing with k6)

### Local Development Environment

```bash
# Clone repository
git clone https://github.com/lemayian23/code-review-ai.git
cd code-review-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install

# Start infrastructure services
docker-compose up -d postgres redis weaviate

# Run database migrations
alembic upgrade head

# Seed database with sample data
python scripts/seed_data.py
```

### Environment Configuration

Create `.env` file:

```bash
# Development settings
DEBUG=true
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/codereviews
REDIS_URL=redis://localhost:6379/0

# LLM APIs (get from OpenAI and Anthropic)
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Vector Database
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=

# GitHub Integration (optional for development)
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY_PATH=
GITHUB_WEBHOOK_SECRET=
```

### Running the Application

```bash
# Start API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (separate terminal)
celery -A workers.celery_app worker --loglevel=info

# Start Flower dashboard (optional)
celery -A workers.celery_app flower --port=5555
```

## Codebase Architecture

### Project Structure

```
code-review-ai/
├── api/                    # FastAPI application
│   ├── main.py            # Application entry point
│   ├── routers/           # API route handlers
│   ├── middleware/         # Custom middleware
│   └── dependencies.py    # Dependency injection
├── core/                  # Core business logic
│   ├── llm/              # LLM integration
│   ├── rag/              # RAG system
│   ├── patterns/         # Pattern matching
│   └── feedback/         # Learning system
├── workers/              # Celery workers
│   ├── celery_app.py     # Celery configuration
│   └── tasks/            # Background tasks
├── db/                   # Database layer
│   ├── models.py         # SQLAlchemy models
│   └── migrations/       # Alembic migrations
├── observability/        # Monitoring and logging
├── tests/               # Test suite
├── scripts/             # Utility scripts
└── infrastructure/      # Deployment configs
```

### Key Components

#### API Layer (`api/`)

- **FastAPI**: Modern, fast web framework
- **Routers**: Modular route organization
- **Middleware**: Authentication, rate limiting, CORS
- **Dependencies**: Database sessions, user authentication

#### Core Logic (`core/`)

- **LLM Client**: Multi-provider LLM integration
- **RAG System**: Vector embeddings and retrieval
- **Pattern Matcher**: Rule-based code analysis
- **Feedback Learner**: ML learning system

#### Workers (`workers/`)

- **Celery**: Distributed task queue
- **Tasks**: Async code analysis, embeddings, retraining
- **Scheduling**: Periodic maintenance tasks

#### Database (`db/`)

- **Models**: SQLAlchemy ORM models
- **Migrations**: Alembic database migrations
- **Relationships**: User, repository, review, feedback models

## Development Workflow

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type checking
mypy core/ api/ workers/

# Run tests
make test

# Run specific test
pytest tests/unit/test_llm_client.py -v
```

### Testing

#### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=core --cov=api --cov-report=html

# Run specific test file
pytest tests/unit/test_llm_client.py::TestLLMClient::test_analyze_code_success -v
```

#### Integration Tests

```bash
# Run integration tests
pytest tests/integration/ -v

# Run with database
pytest tests/integration/test_api_endpoints.py -v
```

#### Load Tests

```bash
# Install k6
npm install -g k6

# Run load tests
make test-load

# Run specific load test
k6 run tests/load/analyze_endpoint.js
```

#### AI Evaluations

```bash
# Run golden dataset evaluation
make evals

# Run specific evaluation
python tests/evals/run_golden_dataset.py
```

### Database Development

#### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Show migration history
alembic history
```

#### Model Development

```python
# Example: Adding new model
from sqlalchemy import Column, String, DateTime
from db.models import Base

class NewModel(Base):
    __tablename__ = "new_model"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
```

### API Development

#### Adding New Endpoints

```python
# api/routers/new_router.py
from fastapi import APIRouter, Depends
from api.dependencies import get_current_user

router = APIRouter()

@router.post("/new-endpoint")
async def new_endpoint(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    # Implementation
    return {"status": "success"}
```

#### Adding Middleware

```python
# api/middleware/new_middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class NewMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Pre-processing
        response = await call_next(request)
        # Post-processing
        return response
```

### Worker Development

#### Adding New Tasks

```python
# workers/tasks/new_task.py
from workers.celery_app import celery_app

@celery_app.task(bind=True, name="workers.tasks.new_task.new_task")
def new_task(self, param1: str, param2: int):
    """New background task"""
    try:
        # Task implementation
        return {"status": "completed", "result": "success"}
    except Exception as e:
        self.retry(countdown=60, max_retries=3)
```

### Core Logic Development

#### Adding New LLM Provider

```python
# core/llm/new_provider.py
class NewLLMProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_response(self, prompt: str) -> str:
        # Implementation
        pass
```

#### Adding New Pattern Rules

```python
# core/patterns/new_rules.py
def add_custom_rule(
    name: str,
    pattern: str,
    message: str,
    severity: str,
    suggestion: str
):
    # Implementation
    pass
```

## Debugging

### API Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debugger
python -m pdb -m uvicorn api.main:app --reload
```

### Worker Debugging

```bash
# Run worker with debug logging
celery -A workers.celery_app worker --loglevel=debug

# Inspect worker
celery -A workers.celery_app inspect active
celery -A workers.celery_app inspect stats
```

### Database Debugging

```bash
# Connect to database
docker-compose exec postgres psql -U user -d codereviews

# Check migrations
alembic current
alembic history
```

### Logging

```python
# Add structured logging
import structlog
logger = structlog.get_logger(__name__)

logger.info("Processing request", user_id=user_id, request_id=request_id)
logger.error("Request failed", error=str(e), context={"user_id": user_id})
```

## Performance Optimization

### Profiling

```python
# Add profiling to functions
import cProfile
import pstats

def profile_function(func):
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()

        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats()

        return result
    return wrapper
```

### Caching

```python
# Add caching to expensive operations
from core.llm.cache import LLMCache

cache = LLMCache()

@cache.cached(ttl=3600)
async def expensive_operation(param: str):
    # Implementation
    pass
```

### Database Optimization

```python
# Use database indexes
class User(Base):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
```

## Contributing

### Code Style

- **Formatting**: Use `ruff format`
- **Linting**: Use `ruff check`
- **Type Hints**: Use `mypy` for type checking
- **Docstrings**: Use Google style docstrings

### Commit Messages

Use conventional commits:

```
feat: add new feature
fix: fix bug
docs: update documentation
style: formatting changes
refactor: code refactoring
test: add tests
chore: maintenance tasks
```

### Pull Request Process

1. **Fork** the repository
2. **Create** feature branch
3. **Make** changes with tests
4. **Run** quality checks
5. **Submit** pull request
6. **Address** review feedback

### Testing Requirements

- **Unit Tests**: 85%+ coverage
- **Integration Tests**: Critical paths
- **Load Tests**: Performance validation
- **AI Evaluations**: Model quality

## Troubleshooting

### Common Issues

1. **Database Connection**

   ```bash
   # Check database status
   docker-compose ps postgres

   # Check logs
   docker-compose logs postgres
   ```

2. **Redis Connection**

   ```bash
   # Check Redis status
   docker-compose ps redis

   # Test connection
   docker-compose exec redis redis-cli ping
   ```

3. **Weaviate Connection**

   ```bash
   # Check Weaviate status
   docker-compose ps weaviate

   # Test connection
   curl http://localhost:8080/v1/meta
   ```

4. **Worker Issues**

   ```bash
   # Check worker status
   celery -A workers.celery_app inspect active

   # Check worker logs
   docker-compose logs worker
   ```

### Performance Issues

1. **Slow API Responses**

   - Check database queries
   - Monitor LLM API calls
   - Review caching strategy

2. **High Memory Usage**

   - Check for memory leaks
   - Optimize data structures
   - Review worker memory limits

3. **Database Performance**
   - Check query execution plans
   - Add database indexes
   - Optimize connection pooling

### Debug Tools

```bash
# Database query analysis
docker-compose exec postgres psql -U user -d codereviews -c "EXPLAIN ANALYZE SELECT * FROM users;"

# Redis memory usage
docker-compose exec redis redis-cli info memory

# Worker task monitoring
celery -A workers.celery_app events
```

## Documentation

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Code Documentation

```python
def analyze_code(
    diff_content: str,
    context_docs: List[Dict[str, Any]],
    file_paths: List[str],
    repository_url: str
) -> List[Dict[str, Any]]:
    """
    Analyze code changes using LLM and pattern matching.

    Args:
        diff_content: Git diff content to analyze
        context_docs: Retrieved context documents
        file_paths: List of changed file paths
        repository_url: Repository URL for context

    Returns:
        List of analysis suggestions with confidence scores

    Raises:
        LLMError: If LLM API call fails
        ValidationError: If input validation fails
    """
    # Implementation
    pass
```

### Architecture Documentation

- **System Design**: See `ARCHITECTURE.md`
- **API Reference**: See `docs/API.md`
- **Deployment Guide**: See `docs/DEPLOYMENT.md`
