#!/usr/bin/env python3
# app/cache/redis_cache.py
# -*- coding: utf-8 -*-
"""
Redis cache implementation for async operations.

This module provides async-compatible cache operations used by the MCP server.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Async Redis cache wrapper.

    Provides async get/set operations with safe error handling.
    """

    def __init__(self, redis_url: str | None = None):
        """
        Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        self._available = False
        self._sync_client = None

    async def _ensure_client(self) -> None:
        """Ensure Redis client is initialized."""
        if self._client is not None:
            return

        try:
            # Try to use aioredis if available
            try:
                import redis.asyncio as aioredis

                self._client = await aioredis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_timeout=2,
                    socket_connect_timeout=2,
                )
                await self._client.ping()
                self._available = True
                logger.info("Async Redis cache initialized")
            except ImportError:
                # Fallback to sync redis
                import redis

                self._sync_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_timeout=2,
                    socket_connect_timeout=2,
                )
                self._sync_client.ping()
                self._available = True
                logger.info("Sync Redis cache initialized (async not available)")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Cache disabled.")
            self._available = False

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        await self._ensure_client()

        if not self._available:
            return None

        try:
            if self._client:
                value = await self._client.get(key)
            elif self._sync_client:
                value = self._sync_client.get(key)
            else:
                return None

            if value is None:
                return None

            return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds

        Returns:
            True if successful
        """
        await self._ensure_client()

        if not self._available:
            return False

        try:
            serialized = json.dumps(value, default=str)

            if self._client:
                if ttl_seconds:
                    await self._client.setex(key, ttl_seconds, serialized)
                else:
                    await self._client.set(key, serialized)
            elif self._sync_client:
                if ttl_seconds:
                    self._sync_client.setex(key, ttl_seconds, serialized)
                else:
                    self._sync_client.set(key, serialized)
            else:
                return False

            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False


# Global cache instance
_cache_instance: RedisCache | None = None


async def get_cache() -> RedisCache:
    """
    Get or create global cache instance.

    Returns:
        RedisCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance
