"""
Distributed tracing for Code Review AI
"""
import time
from typing import Dict, Any, Optional
from functools import wraps

import structlog
from core.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)


class TraceContext:
    """Trace context for distributed tracing"""
    
    def __init__(self, trace_id: str, span_id: str, parent_span_id: Optional[str] = None):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.tags = {}
        self.logs = []

    def add_tag(self, key: str, value: Any):
        """Add tag to span"""
        self.tags[key] = value

    def add_log(self, message: str, **kwargs):
        """Add log to span"""
        self.logs.append({
            "timestamp": time.time(),
            "message": message,
            **kwargs
        })

    def finish(self) -> Dict[str, Any]:
        """Finish span and return trace data"""
        duration = time.time() - self.start_time
        
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "duration": duration,
            "tags": self.tags,
            "logs": self.logs
        }


class Tracer:
    """Distributed tracer for Code Review AI"""
    
    def __init__(self):
        self.active_spans = {}
        self.trace_data = []

    def start_span(
        self, 
        operation_name: str, 
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ) -> TraceContext:
        """Start a new span"""
        import uuid
        
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        span_id = str(uuid.uuid4())
        
        context = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
        
        self.active_spans[span_id] = context
        
        logger.debug(
            "Span started",
            operation=operation_name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
        
        return context

    def finish_span(self, span_id: str) -> Optional[Dict[str, Any]]:
        """Finish a span"""
        if span_id not in self.active_spans:
            logger.warning("Span not found", span_id=span_id)
            return None
        
        context = self.active_spans.pop(span_id)
        trace_data = context.finish()
        
        # Store trace data
        self.trace_data.append(trace_data)
        
        logger.debug(
            "Span finished",
            trace_id=context.trace_id,
            span_id=span_id,
            duration=trace_data["duration"]
        )
        
        return trace_data

    def get_trace(self, trace_id: str) -> list:
        """Get all spans for a trace"""
        return [span for span in self.trace_data if span["trace_id"] == trace_id]

    def get_active_spans(self) -> Dict[str, TraceContext]:
        """Get all active spans"""
        return self.active_spans.copy()

    def clear_traces(self):
        """Clear all trace data"""
        self.trace_data.clear()
        self.active_spans.clear()


# Global tracer instance
tracer = Tracer()


def trace_operation(operation_name: str):
    """Decorator to trace function execution"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Start span
            context = tracer.start_span(operation_name)
            
            try:
                # Add function parameters as tags
                context.add_tag("function", func.__name__)
                context.add_tag("args_count", len(args))
                context.add_tag("kwargs_count", len(kwargs))
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Add result metadata
                context.add_tag("success", True)
                if hasattr(result, '__len__'):
                    context.add_tag("result_size", len(result))
                
                return result
                
            except Exception as e:
                # Add error information
                context.add_tag("success", False)
                context.add_tag("error", str(e))
                context.add_log("Function failed", error=str(e))
                
                logger.error(
                    "Traced operation failed",
                    operation=operation_name,
                    error=str(e),
                    trace_id=context.trace_id,
                    span_id=context.span_id
                )
                
                raise
                
            finally:
                # Finish span
                tracer.finish_span(context.span_id)
        
        return wrapper
    return decorator


def trace_llm_call(model: str, provider: str):
    """Trace LLM API call"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            operation_name = f"llm_call_{model}_{provider}"
            context = tracer.start_span(operation_name)
            
            try:
                context.add_tag("model", model)
                context.add_tag("provider", provider)
                context.add_tag("operation", "llm_call")
                
                result = await func(*args, **kwargs)
                
                # Add LLM-specific tags
                if hasattr(result, 'usage'):
                    context.add_tag("input_tokens", result.usage.get("input_tokens", 0))
                    context.add_tag("output_tokens", result.usage.get("output_tokens", 0))
                    context.add_tag("total_tokens", result.usage.get("total_tokens", 0))
                
                if hasattr(result, 'cost'):
                    context.add_tag("cost", result.cost)
                
                return result
                
            except Exception as e:
                context.add_tag("error", str(e))
                context.add_log("LLM call failed", error=str(e))
                raise
                
            finally:
                tracer.finish_span(context.span_id)
        
        return wrapper
    return decorator


def trace_database_operation(operation: str):
    """Trace database operation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            context = tracer.start_span(f"db_{operation}")
            
            try:
                context.add_tag("operation", operation)
                context.add_tag("type", "database")
                
                result = await func(*args, **kwargs)
                
                # Add result metadata
                if isinstance(result, list):
                    context.add_tag("result_count", len(result))
                elif isinstance(result, dict):
                    context.add_tag("result_keys", list(result.keys()))
                
                return result
                
            except Exception as e:
                context.add_tag("error", str(e))
                context.add_log("Database operation failed", error=str(e))
                raise
                
            finally:
                tracer.finish_span(context.span_id)
        
        return wrapper
    return decorator


def trace_cache_operation(operation: str):
    """Trace cache operation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            context = tracer.start_span(f"cache_{operation}")
            
            try:
                context.add_tag("operation", operation)
                context.add_tag("type", "cache")
                
                result = await func(*args, **kwargs)
                
                # Add cache-specific tags
                if isinstance(result, bool):
                    context.add_tag("cache_hit", result)
                elif hasattr(result, '__len__'):
                    context.add_tag("result_size", len(result))
                
                return result
                
            except Exception as e:
                context.add_tag("error", str(e))
                context.add_log("Cache operation failed", error=str(e))
                raise
                
            finally:
                tracer.finish_span(context.span_id)
        
        return wrapper
    return decorator


def setup_tracing():
    """Setup distributed tracing"""
    logger.info("Distributed tracing initialized")
    
    # Initialize any external tracing systems (Jaeger, Zipkin, etc.)
    if settings.DATADOG_API_KEY:
        try:
            import ddtrace
            ddtrace.patch_all()
            logger.info("Datadog tracing enabled")
        except ImportError:
            logger.warning("Datadog tracing not available")


def get_trace_summary() -> Dict[str, Any]:
    """Get summary of all traces"""
    active_spans = tracer.get_active_spans()
    
    return {
        "active_spans": len(active_spans),
        "total_traces": len(tracer.trace_data),
        "active_operations": list(active_spans.keys())
    }


def export_traces() -> list:
    """Export all trace data"""
    return tracer.trace_data.copy()
