#!/usr/bin/env python3
# app/security/auth.py
# -*- coding: utf-8 -*-
"""
Simple API key auth for MCP clients.
"""

from dataclasses import dataclass
from typing import List

from fastapi import Depends, Header, HTTPException, status

from app.config import get_settings


@dataclass
class ClientIdentity:
    """Represents authenticated client identity."""

    client_id: str
    scopes: List[str]


async def get_current_client(
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> ClientIdentity:
    """
    Resolve and validate client identity from API key.
    Replace with real auth (OAuth2, JWT, etc) for production.
    """
    settings = get_settings()

    if settings.demo_api_key is None:
        # Auth disabled (e.g., local dev)
        return ClientIdentity(client_id="anonymous", scopes=["osint:read"])

    if x_api_key != settings.demo_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    # In production, look up scopes from DB or identity provider.
    return ClientIdentity(client_id="demo-client", scopes=["osint:read"])
