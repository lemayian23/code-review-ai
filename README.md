# Code Review AI

An intelligent code review assistant that learns from team feedback to automatically catch domain-specific bugs and enforce evolving architectural patterns across microservices.

## 🚀 Features

- **Intelligent Analysis**: Uses LLMs to understand code context and provide meaningful suggestions
- **Pattern Learning**: Learns from team feedback to improve suggestions over time
- **RAG System**: Retrieves relevant context from codebase history and documentation
- **Real-time Streaming**: WebSocket support for live analysis updates
- **Cost Optimization**: Smart caching and tiered LLM usage to minimize costs
- **Production Ready**: Comprehensive observability, monitoring, and security features

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI API   │    │  Celery Workers  │    │   Vector DB     │
│                 │    │                 │    │   (Weaviate)    │
│  - REST Endpoints│    │  - Code Analysis│    │                 │
│  - WebSocket    │    │  - Embeddings   │    │  - Code Context │
│  - Auth         │    │  - Retraining   │    │  - Patterns     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │                 │
                    │  - Reviews      │
                    │  - Feedback     │
                    │  - Metrics      │
                    └─────────────────┘
```

## 🛠️ Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- OpenAI API key
- Anthropic API key

### Setup

1. **Clone the repository**

   ```bash
   git
   cd code-review-ai
   ```

2. **Configure environment**

   ```bash
   cp env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start services**

   ```bash
   make setup
   ```

4. **Verify installation**
   ```bash
   curl http://localhost:8000/health
   ```

### Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Flower Dashboard**: http://localhost:5555
- **Weaviate**: http://localhost:8080

## 📚 Documentation

- **[API Documentation](docs/API.md)** - Complete API reference with examples
- **[Architecture Guide](ARCHITECTURE.md)** - System design and components
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment instructions
- **[Development Guide](docs/DEVELOPMENT.md)** - Local development setup

## 🚀 Usage

### Analyze Code

```bash
curl -X POST http://localhost:8000/api/v1/analyze/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "repository_url": "https://github.com/example/repo",
    "pull_request_id": 123,
    "diff_content": "diff --git a/src/main.py b/src/main.py...",
    "base_commit": "abc123",
    "head_commit": "def456"
  }'
```

### Provide Feedback

```bash
curl -X POST http://localhost:8000/api/v1/feedback/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "review_id": "uuid",
    "suggestion_id": "suggestion_1",
    "helpful": true,
    "correction": "Great catch on the security issue"
  }'
```

### Stream Analysis

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/api/v1/analyze/{review_id}/stream"
);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Analysis update:", data);
};
```

## 🔧 Development

### Local Development

```bash
# Start dependencies
docker-compose up -d postgres redis weaviate

# Install dependencies
pip install -e .

# Run API
uvicorn api.main:app --reload

# Run worker
celery -A workers.celery_app worker --loglevel=info
```

### Testing

```bash
# Run tests
make test

# Run load tests
make test-load

# Run evaluations
make evals
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type checking
mypy core/ api/ workers/
```

## 📊 Monitoring

### Metrics

- **Prometheus**: http://localhost:8000/metrics
- **Grafana**: Configure with Prometheus data source
- **Flower**: http://localhost:5555 (Celery monitoring)

### Logging

Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "api.analyze",
  "message": "Code analysis completed",
  "review_id": "uuid",
  "processing_time": 2.5,
  "suggestion_count": 3
}
```

## 🚀 Deployment

### Docker

```bash
# Build images
make build

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes

```bash
# Deploy to staging
make deploy-staging

# Deploy to production
make deploy-prod
```

### Environment Variables

| Variable            | Description           | Default  |
| ------------------- | --------------------- | -------- |
| `OPENAI_API_KEY`    | OpenAI API key        | Required |
| `ANTHROPIC_API_KEY` | Anthropic API key     | Required |
| `DATABASE_URL`      | PostgreSQL connection | Required |
| `REDIS_URL`         | Redis connection      | Required |
| `WEAVIATE_URL`      | Weaviate connection   | Required |

## 📈 Performance

### Target Metrics

- **Analysis Latency**: < 20s p95
- **API Response**: < 200ms p95
- **Cache Hit Rate**: > 70%
- **Uptime**: 99.5%

### Cost Optimization

- **Embedding Cache**: 90-day TTL
- **Tiered LLM Usage**: GPT-4o-mini for triage, Claude for deep analysis
- **Smart Caching**: Reduces API costs by 80%

## 🔒 Security

- **Authentication**: JWT tokens with OAuth 2.0
- **Authorization**: RBAC for team-level permissions
- **Data Protection**: Code never leaves VPC
- **Audit Logging**: SOC 2 compliant

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Documentation**:
  - [API Reference](docs/API.md)
  - [Architecture Guide](ARCHITECTURE.md)
  - [Deployment Guide](docs/DEPLOYMENT.md)
  - [Development Guide](docs/DEVELOPMENT.md)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## 🎯 Roadmap

- [ ] GitHub App integration
- [ ] Slack notifications
- [ ] Custom rule editor
- [ ] Team-specific models
- [ ] Advanced analytics dashboard
