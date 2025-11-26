#!/usr/bin/env python3
# app/cache.py
# -*- coding: utf-8 -*-
"""
Redis cache wrapper with safe JSON serialization and TTL support.

This module provides a RedisCache class that handles caching with:
- Safe JSON serialization
- Non-fatal error handling (graceful degradation)
- TTL (time-to-live) support
- Decorator for caching function results

Default cache TTLs:
- Spec cache: 3600 seconds (1 hour)
- Search results: 900 seconds (15 minutes)
- Host/details: 3600 seconds (1 hour)
"""

import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis cache wrapper with safe JSON serialization and error handling.
    
    Falls back gracefully if Redis is unavailable - operations return None
    instead of raising exceptions.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL. Defaults to REDIS_URL env var
                      or redis://localhost:6379/0
        """
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )
        self._client = None
        self._available = False
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Redis client with error handling."""
        try:
            import redis
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            # Test connection
            self._client.ping()
            self._available = True
            logger.info("Redis cache initialized successfully")
        except ImportError:
            logger.warning(
                "redis-py not installed. Cache will be disabled. "
                "Install with: pip install redis"
            )
        except Exception as e:
            logger.warning(
                f"Redis connection failed: {e}. Cache will be disabled."
            )
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found, None otherwise
        """
        if not self._available or not self._client:
            return None
        
        try:
            value = self._client.get(key)
            if value is None:
                return None
            
            # Deserialize JSON
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize cached value for {key}: {e}")
            # Delete corrupted cache entry
            try:
                self._client.delete(key)
            except Exception:
                pass
            return None
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl_seconds: Time-to-live in seconds. None for no expiration.
            
        Returns:
            True if successful, False otherwise
        """
        if not self._available or not self._client:
            return False
        
        try:
            # Serialize to JSON
            serialized = json.dumps(value, default=str)
            
            if ttl_seconds:
                self._client.setex(key, ttl_seconds, serialized)
            else:
                self._client.set(key, serialized)
            
            return True
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize value for {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self._available or not self._client:
            return False
        
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False
    
    def cache_result(
        self,
        ttl_seconds: int = 3600,
        key_prefix: str = "func"
    ) -> Callable:
        """
        Decorator to cache function results.
        
        Args:
            ttl_seconds: Cache TTL in seconds
            key_prefix: Prefix for cache keys
            
        Returns:
            Decorator function
            
        Example:
            @cache.cache_result(ttl_seconds=900, key_prefix="search")
            def expensive_search(query: str) -> dict:
                # ... expensive operation
                return results
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Build cache key from function name and arguments
                import hashlib
                
                args_str = json.dumps(
                    {"args": args, "kwargs": kwargs},
                    sort_keys=True,
                    default=str
                )
                args_hash = hashlib.sha256(
                    args_str.encode()
                ).hexdigest()[:16]
                
                cache_key = f"{key_prefix}:{func.__name__}:{args_hash}"
                
                # Try to get from cache
                cached = self.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache result
                self.set(cache_key, result, ttl_seconds)
                
                return result
            
            return wrapper
        return decorator


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """
    Get or create global cache instance.
    
    Returns:
        RedisCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance
