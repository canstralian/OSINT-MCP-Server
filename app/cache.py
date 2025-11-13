#!/usr/bin/env python3
# app/cache.py
# -*- coding: utf-8 -*-
"""
Redis caching wrapper for OSINT-MCP-Server.

Provides a simple Redis cache with decorator support.
Cache failures are non-fatal and logged.
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
    Redis cache wrapper with safe failure handling.

    If Redis is unavailable, operations fail gracefully without
    raising exceptions to the caller.
    """

    def __init__(self, redis_url: str | None = None):
        """
        Initialize Redis cache connection.

        Args:
            redis_url: Redis connection URL. Defaults to REDIS_URL env var
                      or redis://localhost:6379/0.
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client: redis.Redis | None = None
        self._connect()

    def _connect(self) -> None:
        """Establish Redis connection with error handling."""
        try:
            self._client = redis.Redis.from_url(
                self.redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
            )
            # Test connection
            self._client.ping()
            logger.info(f"Redis cache connected: {self.redis_url}")
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e}. Caching disabled.")
            self._client = None

    def get(self, key: str) -> Any | None:
        """
        Retrieve value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value (deserialized from JSON) or None.
        """
        if not self._client:
            return None

        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Store value in cache with optional TTL.

        Args:
            key: Cache key.
            value: Value to cache (will be JSON serialized).
            ttl: Time-to-live in seconds. None means no expiration.

        Returns:
            True if successful, False otherwise.
        """
        if not self._client:
            return False

        try:
            # Serialize with safe default for non-serializable objects
            serialized = json.dumps(value, default=str)
            if ttl:
                self._client.setex(key, ttl, serialized)
            else:
                self._client.set(key, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete.

        Returns:
            True if successful, False otherwise.
        """
        if not self._client:
            return False

        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key '{key}': {e}")
            return False

    def cache_result(self, key_prefix: str, ttl: int = 3600) -> Callable:
        """
        Decorator to cache function results.

        The cache key is constructed from key_prefix and function arguments.

        Args:
            key_prefix: Prefix for cache keys.
            ttl: Time-to-live in seconds (default 3600).

        Returns:
            Decorator function.

        Example:
            @cache.cache_result("shodan_search", ttl=900)
            def search_shodan(query):
                return api_call(query)
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Build cache key from function name and arguments
                cache_key = f"{key_prefix}:{func.__name__}:"
                cache_key += json.dumps(
                    {"args": args, "kwargs": kwargs}, sort_keys=True, default=str
                )

                # Try to get cached result
                cached = self.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached

                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl=ttl)
                return result

            return wrapper

        return decorator


# Global cache instance
_cache_instance: RedisCache | None = None


def get_cache() -> RedisCache:
    """
    Get or create global RedisCache instance.

    Returns:
        RedisCache instance.
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance
