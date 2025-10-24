"""
LLM response caching for Code Review AI
"""
import json
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

import structlog
import redis.asyncio as redis
from core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class LLMCache:
    """Redis-based cache for LLM responses"""
    
    def __init__(self):
        self.redis_client = None
        self._connection_pool = None
        self.hit_count = 0
        self.miss_count = 0

    async def _get_redis_client(self):
        """Get Redis client with connection pooling"""
        if self.redis_client is None:
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                retry_on_timeout=True
            )
            self.redis_client = redis.Redis(connection_pool=self._connection_pool)
        return self.redis_client

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        try:
            client = await self._get_redis_client()
            cached_data = await client.get(key)
            
            if cached_data:
                self.hit_count += 1
                logger.debug("Cache hit", key=key)
                return json.loads(cached_data)
            else:
                self.miss_count += 1
                logger.debug("Cache miss", key=key)
                return None
                
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            self.miss_count += 1
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set cached value with TTL"""
        try:
            client = await self._get_redis_client()
            
            # Use default TTL if not specified
            if ttl is None:
                ttl = settings.CACHE_TTL_DAYS * 24 * 3600  # Convert days to seconds
            
            serialized_value = json.dumps(value, default=str)
            result = await client.setex(key, ttl, serialized_value)
            
            logger.debug("Cache set", key=key, ttl=ttl)
            return result
            
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        try:
            client = await self._get_redis_client()
            result = await client.delete(key)
            logger.debug("Cache delete", key=key)
            return bool(result)
            
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            client = await self._get_redis_client()
            result = await client.exists(key)
            return bool(result)
            
        except Exception as e:
            logger.warning("Cache exists check failed", key=key, error=str(e))
            return False

    async def get_ttl(self, key: str) -> int:
        """Get TTL for key"""
        try:
            client = await self._get_redis_client()
            ttl = await client.ttl(key)
            return ttl
            
        except Exception as e:
            logger.warning("Cache TTL check failed", key=key, error=str(e))
            return -1

    async def extend_ttl(self, key: str, ttl: int) -> bool:
        """Extend TTL for key"""
        try:
            client = await self._get_redis_client()
            result = await client.expire(key, ttl)
            logger.debug("Cache TTL extended", key=key, ttl=ttl)
            return result
            
        except Exception as e:
            logger.warning("Cache TTL extension failed", key=key, error=str(e))
            return False

    def get_hit_rate(self) -> float:
        """Get cache hit rate"""
        total_requests = self.hit_count + self.miss_count
        if total_requests == 0:
            return 0.0
        return self.hit_count / total_requests

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": self.get_hit_rate(),
            "total_requests": self.hit_count + self.miss_count
        }

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        try:
            client = await self._get_redis_client()
            keys = await client.keys(pattern)
            
            if keys:
                deleted_count = await client.delete(*keys)
                logger.info("Cache pattern cleared", pattern=pattern, deleted_count=deleted_count)
                return deleted_count
            return 0
            
        except Exception as e:
            logger.warning("Cache pattern clear failed", pattern=pattern, error=str(e))
            return 0

    async def cleanup_expired(self) -> int:
        """Clean up expired keys (Redis handles this automatically, but useful for monitoring)"""
        try:
            client = await self._get_redis_client()
            
            # Get all cache keys
            keys = await client.keys("llm_analysis:*")
            expired_count = 0
            
            for key in keys:
                ttl = await client.ttl(key)
                if ttl == -2:  # Key doesn't exist
                    expired_count += 1
                elif ttl == -1:  # Key exists but has no expiration
                    # Set expiration for keys without TTL
                    await client.expire(key, settings.CACHE_TTL_DAYS * 24 * 3600)
            
            logger.info("Cache cleanup completed", expired_count=expired_count)
            return expired_count
            
        except Exception as e:
            logger.warning("Cache cleanup failed", error=str(e))
            return 0

    async def get_memory_usage(self) -> Dict[str, Any]:
        """Get cache memory usage statistics"""
        try:
            client = await self._get_redis_client()
            info = await client.info("memory")
            
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "maxmemory": info.get("maxmemory", 0),
                "maxmemory_human": info.get("maxmemory_human", "0B"),
                "cache_keys": len(await client.keys("llm_analysis:*"))
            }
            
        except Exception as e:
            logger.warning("Cache memory usage check failed", error=str(e))
            return {}

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None
