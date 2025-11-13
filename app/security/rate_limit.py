#!/usr/bin/env python3
# app/security/rate_limit.py
# -*- coding: utf-8 -*-
"""
Rate limiting utilities (stub).
"""

from fastapi import HTTPException, status


async def enforce_rate_limit(client_id: str) -> None:
    """
    Enforce per-client rate limits.
    Implement using Redis or similar token bucket in production.
    Raise HTTPException when exceeded.
    """
    # Placeholder: always allow.
    # Wire in Redis counters, leaky bucket, etc.
    _ = client_id
    # Example:
    # if quota_exceeded(client_id):
    #     raise HTTPException(
    #         status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    #         detail="Rate limit exceeded.",
    #     )
    return
