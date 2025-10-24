# Code Review AI - Deployment Guide

## Overview

This guide covers deploying Code Review AI in different environments, from local development to production Kubernetes clusters.

## Prerequisites

- Docker and Docker Compose
- Kubernetes cluster (for production)
- kubectl configured
- Helm 3.x
- Terraform (for infrastructure)

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/lemayian23/code-review-ai.git
cd code-review-ai

# Setup environment
cp env.example .env
# Edit .env with your API keys

# Start services
make setup

# Verify deployment
curl http://localhost:8000/health
```

### Manual Setup

```bash
# Start infrastructure services
docker-compose up -d postgres redis weaviate

# Install Python dependencies
pip install -e .

# Run database migrations
alembic upgrade head

# Start API server
uvicorn api.main:app --reload

# Start Celery worker (separate terminal)
celery -A workers.celery_app worker --loglevel=info
```

## Docker Deployment

### Build Images

```bash
# Build API image
docker build -t code-review-ai:api -f infrastructure/docker/Dockerfile.api .

# Build worker image
docker build -t code-review-ai:worker -f infrastructure/docker/Dockerfile.worker .
```

### Docker Compose

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables

Create `.env` file with required variables:

```bash
# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/codereviews
REDIS_URL=redis://redis:6379/0

# LLM APIs
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Vector Database
WEAVIATE_URL=http://weaviate:8080
WEAVIATE_API_KEY=your-weaviate-key

# GitHub Integration
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=/secrets/github.pem
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# Observability
DATADOG_API_KEY=your-datadog-key
SENTRY_DSN=your-sentry-dsn
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.20+)
- Helm 3.x
- kubectl configured
- Ingress controller (nginx, traefik, etc.)

### Using Helm

```bash
# Add Helm repository (if using external charts)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Deploy to staging
make deploy-staging

# Deploy to production
make deploy-prod
```

### Manual Helm Deployment

```bash
# Create namespace
kubectl create namespace code-review-ai

# Install dependencies
helm install postgresql bitnami/postgresql \
  --namespace code-review-ai \
  --set auth.postgresPassword=password \
  --set auth.database=codereviews

helm install redis bitnami/redis \
  --namespace code-review-ai \
  --set auth.password=password

# Deploy application
helm install code-review-ai infrastructure/helm/code-review-ai/ \
  --namespace code-review-ai \
  --values values-production.yaml
```

### Helm Values

Create `values-production.yaml`:

```yaml
# API Configuration
api:
  replicaCount: 3
  image:
    repository: code-review-ai
    tag: api
    pullPolicy: IfNotPresent

  service:
    type: ClusterIP
    port: 8000

  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "500m"

  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70

# Worker Configuration
worker:
  replicaCount: 2
  image:
    repository: code-review-ai
    tag: worker

  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"

# Database Configuration
database:
  host: postgresql
  port: 5432
  name: codereviews
  username: postgres
  password: password

# Redis Configuration
redis:
  host: redis
  port: 6379
  password: password

# Weaviate Configuration
weaviate:
  host: weaviate
  port: 8080

# Ingress Configuration
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: code-review-ai.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: code-review-ai-tls
      hosts:
        - code-review-ai.example.com
```

## Infrastructure as Code

### Terraform Setup

```bash
# Initialize Terraform
cd infrastructure/terraform
terraform init

# Plan deployment
terraform plan -var-file=production.tfvars

# Apply infrastructure
terraform apply -var-file=production.tfvars
```

### Terraform Variables

Create `production.tfvars`:

```hcl
# AWS Configuration
aws_region = "us-west-2"
aws_profile = "production"

# EKS Configuration
cluster_name = "code-review-ai"
cluster_version = "1.24"
node_group_instance_types = ["t3.medium", "t3.large"]
node_group_desired_size = 3
node_group_max_size = 10
node_group_min_size = 2

# RDS Configuration
db_instance_class = "db.t3.medium"
db_allocated_storage = 100
db_backup_retention_period = 7

# ElastiCache Configuration
cache_node_type = "cache.t3.micro"
cache_num_cache_nodes = 1

# VPC Configuration
vpc_cidr = "10.0.0.0/16"
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnet_cidrs = ["10.0.10.0/24", "10.0.20.0/24"]
```

## Environment-Specific Configurations

### Development

```yaml
# docker-compose.yml
version: "3.8"
services:
  api:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./:/app
    command: uvicorn api.main:app --reload
```

### Staging

```yaml
# values-staging.yaml
api:
  replicaCount: 2
  resources:
    requests:
      memory: "256Mi"
      cpu: "125m"
    limits:
      memory: "512Mi"
      cpu: "250m"

worker:
  replicaCount: 1
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "500m"
```

### Production

```yaml
# values-production.yaml
api:
  replicaCount: 5
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"

  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 60

worker:
  replicaCount: 3
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"
```

## Monitoring and Observability

### Prometheus Setup

```bash
# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Configure service monitors
kubectl apply -f monitoring/service-monitor.yaml
```

### Grafana Dashboards

```bash
# Import dashboards
kubectl apply -f monitoring/grafana-dashboards/
```

### Logging

```bash
# Install ELK stack
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace

helm install kibana elastic/kibana \
  --namespace logging

helm install logstash elastic/logstash \
  --namespace logging
```

## Security Configuration

### Secrets Management

```bash
# Create secrets
kubectl create secret generic code-review-ai-secrets \
  --from-literal=openai-api-key=sk-... \
  --from-literal=anthropic-api-key=sk-ant-... \
  --from-literal=database-password=password \
  --from-literal=redis-password=password

# Create TLS secret
kubectl create secret tls code-review-ai-tls \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem
```

### Network Policies

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: code-review-ai-network-policy
spec:
  podSelector:
    matchLabels:
      app: code-review-ai
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: default
```

### RBAC Configuration

```yaml
# rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: code-review-ai
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: code-review-ai
rules:
  - apiGroups: [""]
    resources: ["secrets", "configmaps"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: code-review-ai
subjects:
  - kind: ServiceAccount
    name: code-review-ai
roleRef:
  kind: Role
  name: code-review-ai
  apiGroup: rbac.authorization.k8s.io
```

## Backup and Recovery

### Database Backup

```bash
# Create backup job
kubectl apply -f backup/postgres-backup-cronjob.yaml
```

### Application Backup

```bash
# Backup configuration
kubectl get configmap code-review-ai-config -o yaml > backup/config-backup.yaml

# Backup secrets (encrypted)
kubectl get secret code-review-ai-secrets -o yaml > backup/secrets-backup.yaml
```

## Troubleshooting

### Common Issues

1. **Pod not starting**

   ```bash
   kubectl describe pod <pod-name>
   kubectl logs <pod-name>
   ```

2. **Database connection issues**

   ```bash
   kubectl exec -it <postgres-pod> -- psql -U postgres -d codereviews
   ```

3. **Redis connection issues**
   ```bash
   kubectl exec -it <redis-pod> -- redis-cli ping
   ```

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check worker health
kubectl exec -it <worker-pod> -- celery -A workers.celery_app inspect ping

# Check database
kubectl exec -it <postgres-pod> -- pg_isready
```

### Performance Tuning

1. **Resource limits**: Adjust CPU/memory based on usage
2. **Replica counts**: Scale based on load
3. **Database tuning**: Optimize PostgreSQL settings
4. **Cache configuration**: Tune Redis settings

## Rollback Procedures

### Application Rollback

```bash
# Rollback to previous version
helm rollback code-review-ai 1

# Rollback database migration
kubectl exec -it <api-pod> -- alembic downgrade -1
```

### Infrastructure Rollback

```bash
# Rollback Terraform changes
terraform plan -var-file=production.tfvars
terraform apply -var-file=production.tfvars
```

## Maintenance

### Regular Tasks

1. **Security updates**: Update base images monthly
2. **Dependency updates**: Update Python packages quarterly
3. **Database maintenance**: Vacuum and analyze weekly
4. **Log rotation**: Configure log retention policies

### Monitoring

1. **Resource usage**: Monitor CPU, memory, disk
2. **Application metrics**: Track API response times
3. **Error rates**: Monitor 4xx/5xx responses
4. **Cost tracking**: Monitor cloud resource costs
