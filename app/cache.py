#!/usr/bin/env python3
# app/cache.py
# -*- coding: utf-8 -*-
"""
Redis caching wrapper for OSINT operations.
"""

import json
import logging
import os
from collections.abc import Callable
from functools import wraps
from typing import Any

import redis

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis cache wrapper with safe error handling.

    Provides caching functionality with automatic JSON serialization,
    TTL support, and non-fatal error handling.
    """

    def __init__(self, redis_url: str | None = None):
        """
        Initialize Redis cache connection.

        Args:
            redis_url: Redis connection URL. Defaults to REDIS_URL env var
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client: redis.Redis | None = None
        self._connect()

    def _connect(self) -> None:
        """Attempt to connect to Redis. Log errors but don't fail."""
        try:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            self._client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self._client = None

    def get(self, key: str) -> Any | None:
        """
        Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or error occurs
        """
        if not self._client:
            return None

        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Store value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds (default: 3600)

        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            return False

        try:
            serialized = json.dumps(value, default=str)
            self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            return False

        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    def cache_result(self, ttl: int = 3600, key_func: Callable | None = None):
        """
        Decorator to cache function results.

        Args:
            ttl: Time-to-live in seconds
            key_func: Optional function to generate cache key from arguments

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default: use function name and string repr of args
                    args_str = "_".join(str(arg) for arg in args)
                    kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = f"{func.__name__}:{args_str}:{kwargs_str}"

                # Try to get from cache
                cached = self.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached

                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result

            return wrapper

        return decorator


# Global cache instance
_cache_instance: RedisCache | None = None


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


# Async version for compatibility
async def get_cache_async() -> RedisCache:
    """
    Get or create global cache instance (async version for compatibility).

    Returns:
        RedisCache instance
    """
    return get_cache()

    # Async method aliases for compatibility
    async def get_async(self, key: str):
        """Async wrapper for get."""


class AsyncRedisCache:
    """
    Async wrapper for RedisCache for backward compatibility.
    
    Provides async methods that wrap synchronous Redis operations.
    """

    def __init__(self, cache: RedisCache):
        """Initialize with a RedisCache instance."""
        self._cache = cache

    async def get(self, key: str):
        """Async get method."""
        return self._cache.get(key)

    async def set(self, key: str, value, ttl_seconds: int = 3600):
        """Async set method."""
        return self._cache.set(key, value, ttl_seconds)


async def get_cache_async() -> AsyncRedisCache:
    """
    Get async cache wrapper (for backward compatibility).

    Returns:
        AsyncRedisCache instance wrapping the sync cache
    """
    return AsyncRedisCache(get_cache())
