"""
Rate limiting middleware for Code Review AI
"""
import time
from typing import Dict, Tuple

import structlog
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class RateLimitMiddleware:
    """Token bucket rate limiting middleware"""
    
    def __init__(self, app):
        self.app = app
        self.buckets: Dict[str, Tuple[float, int]] = {}  # {key: (last_refill, tokens)}
        self.requests_per_minute = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.burst_capacity = settings.RATE_LIMIT_BURST

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Skip rate limiting for health checks
            if request.url.path in ["/health", "/metrics"]:
                await self.app(scope, receive, send)
                return
            
            # Get client identifier
            client_id = self._get_client_id(request)
            
            # Check rate limit
            if not self._check_rate_limit(client_id):
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {self.requests_per_minute} requests per minute",
                        "retry_after": 60
                    }
                )
                await response(scope, receive, send)
                return
        
        await self.app(scope, receive, send)

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"
        
        # Fallback to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if request is within rate limit using token bucket algorithm"""
        current_time = time.time()
        
        if client_id not in self.buckets:
            # Initialize bucket
            self.buckets[client_id] = (current_time, self.burst_capacity)
            return True
        
        last_refill, tokens = self.buckets[client_id]
        
        # Calculate time elapsed and refill tokens
        time_elapsed = current_time - last_refill
        tokens_to_add = time_elapsed * (self.requests_per_minute / 60.0)
        new_tokens = min(tokens + tokens_to_add, self.burst_capacity)
        
        # Check if we have tokens available
        if new_tokens >= 1:
            # Consume one token
            self.buckets[client_id] = (current_time, new_tokens - 1)
            return True
        
        # Update bucket state
        self.buckets[client_id] = (current_time, new_tokens)
        return False

    def _cleanup_old_buckets(self):
        """Clean up old rate limit buckets to prevent memory leaks"""
        current_time = time.time()
        cleanup_threshold = 300  # 5 minutes
        
        to_remove = []
        for client_id, (last_refill, _) in self.buckets.items():
            if current_time - last_refill > cleanup_threshold:
                to_remove.append(client_id)
        
        for client_id in to_remove:
            del self.buckets[client_id]
        
        if to_remove:
            logger.info("Cleaned up old rate limit buckets", count=len(to_remove))
