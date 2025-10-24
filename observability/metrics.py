"""
Metrics collection for Code Review AI
"""
import time
from typing import Dict, Any, Optional
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest
from core.config import get_settings

settings = get_settings()

# Create custom registry
registry = CollectorRegistry()

# API Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint'],
    registry=registry
)

# LLM Metrics
llm_calls_total = Counter(
    'llm_calls_total',
    'Total LLM API calls',
    ['model', 'provider'],
    registry=registry
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'type'],
    registry=registry
)

llm_cost_total = Counter(
    'llm_cost_total',
    'Total LLM cost in USD',
    ['model', 'provider'],
    registry=registry
)

llm_call_duration = Histogram(
    'llm_call_duration_seconds',
    'LLM call duration',
    ['model', 'provider'],
    registry=registry
)

# Cache Metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result'],
    registry=registry
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate',
    registry=registry
)

# Analysis Metrics
analysis_total = Counter(
    'analysis_total',
    'Total code analyses',
    ['repository_id', 'status'],
    registry=registry
)

analysis_duration = Histogram(
    'analysis_duration_seconds',
    'Analysis duration',
    ['repository_id'],
    registry=registry
)

suggestions_generated = Counter(
    'suggestions_generated_total',
    'Total suggestions generated',
    ['type', 'severity'],
    registry=registry
)

# Feedback Metrics
feedback_total = Counter(
    'feedback_total',
    'Total feedback received',
    ['helpful', 'category'],
    registry=registry
)

learning_metrics = Gauge(
    'learning_metrics',
    'Learning system metrics',
    ['metric_type'],
    registry=registry
)

# System Metrics
active_connections = Gauge(
    'active_connections',
    'Active WebSocket connections',
    registry=registry
)

queue_size = Gauge(
    'queue_size',
    'Celery queue size',
    ['queue_name'],
    registry=registry
)

# Cost Metrics
monthly_cost = Gauge(
    'monthly_cost_usd',
    'Monthly cost in USD',
    registry=registry
)

cost_alert_threshold = Gauge(
    'cost_alert_threshold_usd',
    'Cost alert threshold in USD',
    registry=registry
)


def record_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record API request metrics"""
    api_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)


def record_llm_call(
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    duration: float
):
    """Record LLM call metrics"""
    llm_calls_total.labels(model=model, provider=provider).inc()
    llm_tokens_total.labels(model=model, type="input").inc(input_tokens)
    llm_tokens_total.labels(model=model, type="output").inc(output_tokens)
    llm_cost_total.labels(model=model, provider=provider).inc(cost)
    llm_call_duration.labels(model=model, provider=provider).observe(duration)


def record_cache_operation(operation: str, result: str):
    """Record cache operation metrics"""
    cache_operations_total.labels(operation=operation, result=result).inc()


def record_cache_hit_rate(hit_rate: float):
    """Record cache hit rate"""
    cache_hit_rate.set(hit_rate)


def record_analysis(
    repository_id: str,
    status: str,
    duration: float,
    suggestion_count: int,
    cost: float
):
    """Record analysis metrics"""
    analysis_total.labels(repository_id=repository_id, status=status).inc()
    analysis_duration.labels(repository_id=repository_id).observe(duration)
    
    # Record suggestions by type (simplified)
    suggestions_generated.labels(type="all", severity="all").inc(suggestion_count)


def record_suggestion(suggestion_type: str, severity: str):
    """Record individual suggestion"""
    suggestions_generated.labels(type=suggestion_type, severity=severity).inc()


def record_feedback(helpful: bool, category: str):
    """Record feedback metrics"""
    feedback_total.labels(helpful=str(helpful), category=category).inc()


def record_learning_metric(metric_type: str, value: float):
    """Record learning system metric"""
    learning_metrics.labels(metric_type=metric_type).set(value)


def record_connection_count(count: int):
    """Record active connection count"""
    active_connections.set(count)


def record_queue_size(queue_name: str, size: int):
    """Record queue size"""
    queue_size.labels(queue_name=queue_name).set(size)


def record_cost_metrics(monthly_cost_value: float, threshold: float):
    """Record cost metrics"""
    monthly_cost.set(monthly_cost_value)
    cost_alert_threshold.set(threshold)


def record_analysis_metrics(
    processing_time: float,
    suggestion_count: int,
    cost_estimate: float,
    cache_hit_rate: float
):
    """Record comprehensive analysis metrics"""
    # This would be called from the analysis task
    pass


def record_embedding_metrics(
    processing_time: float,
    files_processed: int,
    embeddings_generated: int,
    repository_id: str
):
    """Record embedding generation metrics"""
    # This would be called from the embedding task
    pass


def record_retrieval_metrics(
    processing_time: float,
    documents_retrieved: int,
    repository_id: str
):
    """Record retrieval metrics"""
    # This would be called from the retrieval system
    pass


def record_retraining_metrics(
    processing_time: float,
    feedback_samples: int,
    learning_improvement: float,
    pattern_updates: int
):
    """Record retraining metrics"""
    # This would be called from the retraining task
    pass


def get_metrics() -> str:
    """Get Prometheus metrics in text format"""
    return generate_latest(registry).decode('utf-8')


def get_metrics_dict() -> Dict[str, Any]:
    """Get metrics as dictionary"""
    # This would return a structured dictionary of metrics
    return {
        "api_requests": "See Prometheus metrics",
        "llm_calls": "See Prometheus metrics",
        "cache_operations": "See Prometheus metrics",
        "analysis_metrics": "See Prometheus metrics"
    }


def setup_metrics():
    """Setup metrics collection"""
    # Initialize default values
    cost_alert_threshold.set(settings.ALERT_THRESHOLD_USD)
    monthly_cost.set(0.0)
    
    # Set up any additional metric collection
    pass


def metrics_middleware(func):
    """Decorator to automatically record function metrics"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Record success metrics
            record_api_request("POST", func.__name__, 200, duration)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error metrics
            record_api_request("POST", func.__name__, 500, duration)
            raise
    
    return wrapper
