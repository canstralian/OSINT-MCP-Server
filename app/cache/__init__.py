#!/usr/bin/env python3
# app/cache/__init__.py
# -*- coding: utf-8 -*-
"""
Cache module for OSINT MCP Server.
"""

from app.cache.redis_cache import RedisCache, get_cache

__all__ = ["RedisCache", "get_cache"]
