"""
Structured logging configuration for Code Review AI
"""
import logging
import sys
from typing import Any, Dict

import structlog
from core.config import get_settings

settings = get_settings()


def setup_logging():
    """Configure structured logging"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


class LoggerMixin:
    """Mixin class for adding structured logging to classes"""
    
    @property
    def logger(self):
        """Get structured logger for this class"""
        return structlog.get_logger(self.__class__.__name__)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger by name"""
    return structlog.get_logger(name)


def log_function_call(func_name: str, **kwargs) -> Dict[str, Any]:
    """Log function call with parameters"""
    logger = structlog.get_logger("function_calls")
    logger.info("Function called", function=func_name, **kwargs)
    return {"function": func_name, **kwargs}


def log_performance(operation: str, duration: float, **kwargs) -> Dict[str, Any]:
    """Log performance metrics"""
    logger = structlog.get_logger("performance")
    logger.info("Performance metric", operation=operation, duration=duration, **kwargs)
    return {"operation": operation, "duration": duration, **kwargs}


def log_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Log error with context"""
    logger = structlog.get_logger("errors")
    logger.error("Error occurred", error=str(error), context=context or {})
    return {"error": str(error), "context": context or {}}


def log_user_action(user_id: str, action: str, **kwargs) -> Dict[str, Any]:
    """Log user action"""
    logger = structlog.get_logger("user_actions")
    logger.info("User action", user_id=user_id, action=action, **kwargs)
    return {"user_id": user_id, "action": action, **kwargs}


def log_api_request(method: str, path: str, status_code: int, duration: float, **kwargs) -> Dict[str, Any]:
    """Log API request"""
    logger = structlog.get_logger("api_requests")
    logger.info(
        "API request",
        method=method,
        path=path,
        status_code=status_code,
        duration=duration,
        **kwargs
    )
    return {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration": duration,
        **kwargs
    }


def log_llm_call(model: str, tokens: int, cost: float, duration: float, **kwargs) -> Dict[str, Any]:
    """Log LLM API call"""
    logger = structlog.get_logger("llm_calls")
    logger.info(
        "LLM call",
        model=model,
        tokens=tokens,
        cost=cost,
        duration=duration,
        **kwargs
    )
    return {
        "model": model,
        "tokens": tokens,
        "cost": cost,
        "duration": duration,
        **kwargs
    }


def log_cache_operation(operation: str, key: str, hit: bool = None, **kwargs) -> Dict[str, Any]:
    """Log cache operation"""
    logger = structlog.get_logger("cache_operations")
    logger.info(
        "Cache operation",
        operation=operation,
        key=key,
        hit=hit,
        **kwargs
    )
    return {
        "operation": operation,
        "key": key,
        "hit": hit,
        **kwargs
    }
