#!/bin/bash

# Code Review AI Setup Script
set -e

echo "🚀 Setting up Code Review AI..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please update .env file with your API keys and configuration"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs data secrets

# Set up pre-commit hooks if available
if command -v pre-commit &> /dev/null; then
    echo "🔧 Setting up pre-commit hooks..."
    pre-commit install
fi

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 15

# Check service health
echo "🏥 Checking service health..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API service is healthy"
else
    echo "❌ API service is not responding"
    exit 1
fi

if curl -f http://localhost:5555 > /dev/null 2>&1; then
    echo "✅ Flower dashboard is healthy"
else
    echo "❌ Flower dashboard is not responding"
fi

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose exec api alembic upgrade head

# Seed database with sample data
echo "🌱 Seeding database with sample data..."
docker-compose exec api python scripts/seed_data.py

echo "✅ Setup complete!"
echo ""
echo "📊 Services running:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Flower: http://localhost:5555"
echo "  - Weaviate: http://localhost:8080"
echo ""
echo "🔧 Next steps:"
echo "  1. Update .env file with your API keys"
echo "  2. Test the API: curl http://localhost:8000/health"
echo "  3. Check the documentation: http://localhost:8000/docs"
echo ""
echo "🛠️ Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart services: docker-compose restart"
