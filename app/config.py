#!/usr/bin/env python3
# app/config.py
# -*- coding: utf-8 -*-
"""
Application configuration and settings.
"""

from functools import lru_cache
from logging import Logger, getLogger
from typing import Optional

from pydantic import AnyHttpUrl, BaseSettings, Field


class Settings(BaseSettings):
    """Runtime settings for the OSINT MCP server."""

    app_name: str = Field(default="osint-mcp-server")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Redis cache
    redis_url: str = Field(default="redis://redis:6379/0")

    # Auth
    api_key_header_name: str = Field(default="x-api-key")
    # In production: never hard-code; use env/secret manager.
    demo_api_key: Optional[str] = Field(default=None)

    # Example of an external OSINT API endpoint placeholder
    example_osint_api_base: Optional[AnyHttpUrl] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def logger(self) -> Logger:
        """Return module logger."""
        return getLogger(self.app_name)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
