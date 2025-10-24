.PHONY: setup test lint build deploy clean migrate seed benchmark

setup:
	@echo "🚀 Setting up Code Review AI..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	sleep 15
	python scripts/seed_data.py
	@echo "✅ Setup complete. API running on http://localhost:8000"
	@echo "📊 Flower dashboard: http://localhost:5555"

test:
	@echo "🧪 Running unit tests..."
	pytest tests/unit -v --cov=core --cov=api --cov-report=html
	@echo "🔗 Running integration tests..."
	pytest tests/integration -v

test-load:
	@echo "⚡ Running load tests..."
	k6 run tests/load/analyze_endpoint.js

evals:
	@echo "🤖 Running AI evaluations..."
	python tests/evals/run_golden_dataset.py

lint:
	@echo "🔍 Running linters..."
	ruff check .
	mypy core/ api/ workers/

format:
	@echo "🎨 Formatting code..."
	ruff format .

build:
	@echo "🏗️ Building Docker images..."
	docker build -t code-review-ai:api -f infrastructure/docker/Dockerfile.api .
	docker build -t code-review-ai:worker -f infrastructure/docker/Dockerfile.worker .

deploy-staging:
	@echo "🚀 Deploying to staging..."
	kubectl config use-context staging
	helm upgrade --install code-review-ai infrastructure/helm/code-review-ai/ -f values-staging.yaml

deploy-prod:
	@echo "🚀 Deploying to production..."
	kubectl config use-context prod
	helm upgrade --install code-review-ai infrastructure/helm/code-review-ai/ -f values-prod.yaml

benchmark:
	@echo "📊 Running benchmark tests..."
	python scripts/benchmark.py --prs=100 --concurrent=20

clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	rm -rf __pycache__ .pytest_cache htmlcov .coverage

migrate:
	@echo "🗄️ Running database migrations..."
	alembic upgrade head

seed:
	@echo "🌱 Seeding database..."
	python scripts/seed_data.py --samples=100

logs:
	@echo "📋 Showing logs..."
	docker-compose logs -f api worker

health:
	@echo "🏥 Checking service health..."
	curl -f http://localhost:8000/health || echo "❌ API not healthy"
	curl -f http://localhost:5555 || echo "❌ Flower not healthy"

dev:
	@echo "🛠️ Starting development environment..."
	docker-compose up -d postgres redis weaviate
	@echo "⏳ Waiting for services..."
	sleep 10
	@echo "🚀 Starting API in development mode..."
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
